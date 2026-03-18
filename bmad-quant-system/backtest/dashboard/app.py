# -*- coding: utf-8 -*-
"""
Weekend Pre-Lock Backtest Dashboard - Flask Backend (v2 Wizard Flow)
=====================================================================
Step-by-step workflow: Load Signals → Load Prices → Grid Search → Compare
"""

from flask import Flask, render_template, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import pandas as pd
import numpy as np
import yaml
import os
import sys
import glob
import json
import logging
import threading
import time as _time
from pathlib import Path

import requests as _requests

logger = logging.getLogger(__name__)

DASHBOARD_DIR = Path(__file__).parent
BASE_DIR = DASHBOARD_DIR.parent.parent  # bmad-quant-system/
BACKTEST_DIR = DASHBOARD_DIR.parent  # bmad-quant-system/backtest/

# Add project root to path so we can import weekend_price_fetcher
sys.path.insert(0, str(BACKTEST_DIR))
sys.path.insert(0, str(BASE_DIR))

# Try to import BBG fetcher
try:
    from weekend_price_fetcher import WeekendPriceDataFetcher, HAS_BBG
except ImportError:
    HAS_BBG = False
    WeekendPriceDataFetcher = None


def load_config():
    config_path = DASHBOARD_DIR / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class BacktestEngine:
    """Lazy-loading backtest engine supporting step-by-step workflow."""

    def __init__(self, config):
        self.config = config
        self.trade_size = config['trading']['trade_size_usd']

        # State - nothing loaded initially
        self.signals = None
        self.prices = None
        self.weekly_signals = None
        self.valid_weeks = []
        self.grid_results = None

        # Internal arrays (populated after both data loaded)
        self._weeks = None
        self._preds = None
        self._confs = None
        self._entry = None
        self._exit = None
        self._pnl_if_trade = None

        # Tranche execution data (populated after _prepare_weekly)
        # Per-week list of all signals within the execution window
        self._weekly_all_signals = None  # dict: year_week -> list of signal rows

        # Intraday price lookup index (populated by load_intraday)
        self._intraday_ts_index = None   # sorted int64 array of timestamps (ns)
        self._intraday_ask_arr = None    # corresponding ask prices
        self._intraday_bid_arr = None    # corresponding bid prices (for stop loss unwind)

    def update_trade_size(self, new_trade_size: int):
        """Update weekly trade size and recalculate PnL arrays."""
        if self.trade_size == new_trade_size:
            return
        self.trade_size = new_trade_size
        self.config['trading']['trade_size_usd'] = new_trade_size
        # Recalculate PnL per trade if arrays are ready
        if self._entry is not None and self._exit is not None:
            self._pnl_if_trade = (self._exit - self._entry) / self._entry * self.trade_size

    @property
    def signals_loaded(self):
        return self.signals is not None

    @property
    def prices_loaded(self):
        return self.prices is not None

    @property
    def intraday_loaded(self):
        return self._intraday_ts_index is not None

    @property
    def ready(self):
        return self.signals_loaded and self.prices_loaded and self._weeks is not None

    def ensure_intraday_loaded(self):
        """Auto-load intraday data if not already loaded.

        Searches for the best available intraday file in order:
        1. data/market/bbg_intraday_latest.csv
        2. Most recent bbg_intraday_*.csv in data/market/
        3. data/raw/usdcnh_intraday.csv

        Raises ValueError if no intraday file can be found.
        """
        if self.intraday_loaded:
            return  # already loaded

        candidates = [
            BASE_DIR / 'data' / 'market' / 'bbg_intraday_latest.csv',
        ]
        # Also scan for timestamped files in data/market/
        market_dir = BASE_DIR / 'data' / 'market'
        if market_dir.exists():
            timestamped = sorted(market_dir.glob('bbg_intraday_2*.csv'), reverse=True)
            candidates.extend(timestamped)
        candidates.append(BASE_DIR / 'data' / 'raw' / 'usdcnh_intraday.csv')

        for f in candidates:
            if f.exists() and f.stat().st_size > 1000:
                logger.info(f"Auto-loading intraday data from: {f}")
                self.load_intraday(str(f))
                return

        raise ValueError(
            "Stop Loss / Profit Taking requires intraday (minute-level) bid/ask data, "
            "but no intraday file was found. Expected one of:\n"
            "  - data/market/bbg_intraday_latest.csv\n"
            "  - data/market/bbg_intraday_YYYYMMDD_HHMMSS.csv\n"
            "  - data/raw/usdcnh_intraday.csv\n"
            "Please load intraday data first via the UI or place a file in the expected location."
        )

    def load_signals(self, file_path):
        """Step 1: Load signal file."""
        path = Path(file_path)
        if not path.is_absolute():
            path = (BASE_DIR / file_path).resolve()

        self.signals = pd.read_csv(path)
        self.signals['predict_time'] = pd.to_datetime(self.signals['predict_time'])
        if 'confidence' not in self.signals.columns:
            self.signals['confidence'] = np.where(
                self.signals['prediction'] >= 0.5,
                self.signals['confidence_1'],
                self.signals['confidence_0']
            )
        if 'direction' not in self.signals.columns:
            self.signals['direction'] = np.where(
                self.signals['prediction'] >= 0.5, 'BULLISH', 'BEARISH'
            )

        # If prices already loaded, prepare weekly
        if self.prices_loaded:
            self._prepare_weekly()

        return self._signal_summary()

    @staticmethod
    def _compute_year_week(predict_time_series):
        """Compute year_week from predict_time: signals on Sat belong to Friday's ISO week."""
        def _assign_yw(ts):
            wd = ts.weekday()
            if wd == 5:  # Saturday → use previous Friday
                friday = ts - pd.Timedelta(days=1)
            elif wd == 6:  # Sunday → use previous Friday
                friday = ts - pd.Timedelta(days=2)
            elif wd == 4:  # Friday
                friday = ts
            else:
                friday = ts - pd.Timedelta(days=(wd - 4) % 7)
            iso = friday.isocalendar()
            return f"{iso[0]}_{iso[1]:02d}"
        return predict_time_series.apply(_assign_yw)

    def process_raw_signals(self, file_path):
        """Process a raw signal CSV: add confidence, direction, year_week columns.
        Saves processed file to same directory and data/signals/."""
        path = Path(file_path)
        if not path.is_absolute():
            path = (BASE_DIR / file_path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        df = pd.read_csv(path)
        df['predict_time'] = pd.to_datetime(df['predict_time'])

        # Required raw columns check
        for col in ['predict_time', 'prediction', 'confidence_0', 'confidence_1']:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        original_cols = list(df.columns)
        added_cols = []

        # Compute confidence
        if 'confidence' not in df.columns:
            df['confidence'] = np.where(
                df['prediction'] >= 0.5,
                df['confidence_1'],
                df['confidence_0']
            )
            added_cols.append('confidence')
        # Compute direction
        if 'direction' not in df.columns:
            df['direction'] = np.where(
                df['prediction'] >= 0.5, 'BULLISH', 'BEARISH'
            )
            added_cols.append('direction')
        # Compute year_week
        if 'year_week' not in df.columns:
            df['year_week'] = self._compute_year_week(df['predict_time'])
            added_cols.append('year_week')

        # Determine output filename: append _processed before .csv
        stem = path.stem
        if stem.endswith('_processed'):
            out_name = path.name  # already processed name
        else:
            out_name = f"{stem}_processed.csv"

        # Save to same directory as source
        out_path_source = path.parent / out_name
        df.to_csv(out_path_source, index=False)
        saved_paths = [str(out_path_source)]

        # Also save to data/signals/ for easy access
        signals_dir = BASE_DIR / 'data' / 'signals'
        signals_dir.mkdir(parents=True, exist_ok=True)
        out_path_signals = signals_dir / out_name
        df.to_csv(out_path_signals, index=False)
        saved_paths.append(str(out_path_signals))

        # Build summary
        total = len(df)
        weeks = sorted(df['year_week'].unique().tolist())
        bullish_count = int((df['prediction'] >= 0.5).sum())

        return {
            'total_signals': total,
            'total_weeks': len(weeks),
            'weeks_range': f"{weeks[0]} ~ {weeks[-1]}" if weeks else '-',
            'bullish_count': bullish_count,
            'bearish_count': total - bullish_count,
            'bullish_pct': round(bullish_count / total * 100, 1) if total > 0 else 0,
            'added_columns': added_cols,
            'original_columns': original_cols,
            'output_columns': list(df.columns),
            'saved_paths': saved_paths,
            'output_filename': out_name,
            'date_range': [str(df['predict_time'].min()), str(df['predict_time'].max())],
        }

    def validate_signals(self):
        """Validate loaded signal data and return detailed verification report."""
        if self.signals is None:
            return {'valid': False, 'errors': ['No signals loaded']}

        sig = self.signals
        errors = []
        warnings = []
        info = []

        # 1. Required columns check
        required_cols = ['predict_time', 'prediction', 'year_week']
        important_cols = ['confidence', 'confidence_0', 'confidence_1', 'direction', 'target_current_pair']
        missing_required = [c for c in required_cols if c not in sig.columns]
        missing_important = [c for c in important_cols if c not in sig.columns]
        if missing_required:
            errors.append(f"Missing required columns: {missing_required}")
        if missing_important:
            warnings.append(f"Missing optional columns: {missing_important}")
        info.append(f"Found {len(sig.columns)} columns: {list(sig.columns)}")

        # 2. Null / NaN check
        null_counts = {}
        for col in required_cols + ['confidence']:
            if col in sig.columns:
                n = int(sig[col].isna().sum())
                if n > 0:
                    null_counts[col] = n
                    errors.append(f"Column '{col}' has {n} null values ({n/len(sig)*100:.1f}%)")
        if not null_counts:
            info.append("No null values in key columns")

        # 3. Value range check
        if 'prediction' in sig.columns:
            pred_min, pred_max = float(sig['prediction'].min()), float(sig['prediction'].max())
            if pred_min < 0 or pred_max > 1:
                warnings.append(f"Prediction values out of [0,1] range: [{pred_min:.4f}, {pred_max:.4f}]")
            else:
                info.append(f"Prediction range: [{pred_min:.4f}, {pred_max:.4f}] (OK)")

        if 'confidence' in sig.columns:
            conf_min, conf_max = float(sig['confidence'].min()), float(sig['confidence'].max())
            if conf_min < 0 or conf_max > 1:
                warnings.append(f"Confidence values out of [0,1] range: [{conf_min:.4f}, {conf_max:.4f}]")
            else:
                info.append(f"Confidence range: [{conf_min:.4f}, {conf_max:.4f}] (OK)")

        # 4. Time window check (should be Fri 22:30+ ~ Sat 01:30 Beijing)
        sig_copy = sig.copy()
        sig_copy['hour'] = sig_copy['predict_time'].dt.hour
        sig_copy['minute'] = sig_copy['predict_time'].dt.minute
        sig_copy['td'] = sig_copy['hour'] + sig_copy['minute'] / 60
        sig_copy['weekday'] = sig_copy['predict_time'].dt.weekday
        friday_late = sig_copy[(sig_copy['weekday'] == 4) & (sig_copy['td'] >= 22.5)]
        saturday_early = sig_copy[(sig_copy['weekday'] == 5) & (sig_copy['td'] <= 1.5)]
        in_window = len(friday_late) + len(saturday_early)
        out_window = len(sig) - in_window
        if out_window > 0:
            warnings.append(f"{out_window} signals ({out_window/len(sig)*100:.1f}%) outside Fri 22:30 ~ Sat 01:30 window")
        info.append(f"{in_window} signals in trading window ({in_window/len(sig)*100:.1f}%)")

        # 5. Duplicate week check
        week_counts = sig.groupby('year_week').size()
        dup_weeks = week_counts[week_counts > 1]
        info.append(f"{len(week_counts)} unique weeks, avg {week_counts.mean():.1f} signals/week")
        if len(dup_weeks) > 0:
            info.append(f"{len(dup_weeks)} weeks have multiple signals (expected - will use last per week)")

        # 6. Ticker/pair info
        if 'target_current_pair' in sig.columns:
            pairs = sig['target_current_pair'].unique().tolist()
            info.append(f"Currency pair(s): {pairs}")
        else:
            warnings.append("No 'target_current_pair' column - cannot verify instrument")

        # 7. Distribution data for charts
        pred_hist = np.histogram(sig['prediction'].dropna().values, bins=50, range=(0, 1))
        conf_hist = np.histogram(sig['confidence'].dropna().values, bins=50, range=(0, 1)) if 'confidence' in sig.columns else None

        # Weekly signal count
        weekly_counts = sig.groupby('year_week').size().reset_index(name='count')

        # Prediction over time
        weekly_pred = sig.groupby('year_week').agg(
            mean_pred=('prediction', 'mean'),
            mean_conf=('confidence', 'mean') if 'confidence' in sig.columns else ('prediction', 'mean'),
            bullish_pct=('prediction', lambda x: float((x >= 0.5).mean())),
        ).reset_index()

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'info': info,
            'distributions': {
                'prediction_histogram': {
                    'bins': [round(float(b), 3) for b in pred_hist[1][:-1]],
                    'counts': [int(c) for c in pred_hist[0]],
                },
                'confidence_histogram': {
                    'bins': [round(float(b), 3) for b in conf_hist[1][:-1]],
                    'counts': [int(c) for c in conf_hist[0]],
                } if conf_hist is not None else None,
                'weekly_counts': {
                    'weeks': weekly_counts['year_week'].tolist(),
                    'counts': [int(c) for c in weekly_counts['count'].tolist()],
                },
                'weekly_prediction': {
                    'weeks': weekly_pred['year_week'].tolist(),
                    'mean_pred': [round(float(v), 4) for v in weekly_pred['mean_pred'].tolist()],
                    'mean_conf': [round(float(v), 4) for v in weekly_pred['mean_conf'].tolist()],
                    'bullish_pct': [round(float(v), 4) for v in weekly_pred['bullish_pct'].tolist()],
                },
            },
            'market_data_config': self._derive_market_config(),
        }

    def _derive_market_config(self):
        """Derive market data download config from loaded signals."""
        if self.signals is None:
            return None
        sig = self.signals
        # Ticker
        ticker = 'USDCNH Curncy'
        if 'target_current_pair' in sig.columns:
            pair = sig['target_current_pair'].iloc[0]
            ticker = f"{pair} Curncy"

        # Date range from signals
        min_date = sig['predict_time'].min()
        max_date = sig['predict_time'].max()
        # Extend: start from the Friday before min_date, end at Saturday after max_date
        start_date = (min_date - pd.Timedelta(days=min_date.weekday())).strftime('%Y-%m-%d')  # Monday of that week
        end_date = (max_date + pd.Timedelta(days=2)).strftime('%Y-%m-%d')

        weeks = sorted(sig['year_week'].unique().tolist())

        return {
            'ticker': ticker,
            'pair': sig['target_current_pair'].iloc[0] if 'target_current_pair' in sig.columns else 'USDCNH',
            'start_date': start_date,
            'end_date': end_date,
            'weeks': weeks,
            'total_weeks': len(weeks),
            'frequency': '1m',
        }

    # ---------- LLM Analysis ----------
    def llm_analyze_signals(self, config, validation_report=None):
        """Build prompt from signal data + validation report, call LLM, return analysis text.

        Yields chunks for streaming response.
        """
        llm_cfg = config.get('llm', {})
        if not llm_cfg.get('enabled'):
            yield "LLM analysis is disabled. Enable it in config.yaml under `llm.enabled`."
            return
        api_key = llm_cfg.get('api_key', '')
        if not api_key or api_key == 'YOUR_API_KEY_HERE':
            yield "Please set your LLM API key in config.yaml under `llm.api_key`."
            return

        base_url = llm_cfg.get('base_url', 'https://api.openai.com/v1').rstrip('/')
        model = llm_cfg.get('model', 'claude-opus-4-6')
        temperature = float(llm_cfg.get('temperature', 0.1))
        top_p = float(llm_cfg.get('top_p', 0.8))
        max_tokens = int(llm_cfg.get('max_tokens', 4096))
        timeout = int(llm_cfg.get('timeout', 120))

        # --- Build context from signal data ---
        sig = self.signals
        context_parts = []
        context_parts.append("=== Signal Dataset Overview ===")
        context_parts.append(f"Total signals: {len(sig)}")
        context_parts.append(f"Date range: {sig['predict_time'].min()} to {sig['predict_time'].max()}")

        if 'target_current_pair' in sig.columns:
            context_parts.append(f"Currency pair(s): {sig['target_current_pair'].unique().tolist()}")

        unique_weeks = sig['year_week'].nunique()
        context_parts.append(f"Unique weeks: {unique_weeks}")
        context_parts.append(f"Avg signals per week: {len(sig)/unique_weeks:.1f}")

        # Prediction stats
        pred = sig['prediction']
        context_parts.append(f"\n=== Prediction Statistics ===")
        context_parts.append(f"Mean: {pred.mean():.4f}, Median: {pred.median():.4f}")
        context_parts.append(f"Std: {pred.std():.4f}, Min: {pred.min():.4f}, Max: {pred.max():.4f}")
        context_parts.append(f"Bullish signals (>=0.5): {(pred >= 0.5).sum()} ({(pred >= 0.5).mean()*100:.1f}%)")
        context_parts.append(f"Bearish signals (<0.5): {(pred < 0.5).sum()} ({(pred < 0.5).mean()*100:.1f}%)")

        # Confidence stats
        if 'confidence' in sig.columns:
            conf = sig['confidence']
            context_parts.append(f"\n=== Confidence Statistics ===")
            context_parts.append(f"Mean: {conf.mean():.4f}, Median: {conf.median():.4f}")
            context_parts.append(f"Std: {conf.std():.4f}, Min: {conf.min():.4f}, Max: {conf.max():.4f}")

        # Time window analysis
        sig_copy = sig.copy()
        sig_copy['hour'] = sig_copy['predict_time'].dt.hour
        sig_copy['weekday'] = sig_copy['predict_time'].dt.weekday
        sig_copy['td'] = sig_copy['hour'] + sig_copy['predict_time'].dt.minute / 60
        friday_late = sig_copy[(sig_copy['weekday'] == 4) & (sig_copy['td'] >= 22.5)]
        saturday_early = sig_copy[(sig_copy['weekday'] == 5) & (sig_copy['td'] <= 1.5)]
        in_window = len(friday_late) + len(saturday_early)
        context_parts.append(f"\n=== Time Window Analysis ===")
        context_parts.append(f"In trading window (Fri 22:30~Sat 01:30): {in_window}/{len(sig)} ({in_window/len(sig)*100:.1f}%)")
        context_parts.append(f"Outside trading window: {len(sig)-in_window}")

        # Weekly trend (last 10 weeks)
        weekly_agg = sig.groupby('year_week').agg(
            n_signals=('prediction', 'size'),
            mean_pred=('prediction', 'mean'),
            bullish_pct=('prediction', lambda x: float((x >= 0.5).mean())),
        ).reset_index().sort_values('year_week')
        recent = weekly_agg.tail(10)
        context_parts.append(f"\n=== Recent 10 Weeks Trend ===")
        for _, row in recent.iterrows():
            context_parts.append(f"  {row['year_week']}: signals={int(row['n_signals'])}, "
                                 f"mean_pred={row['mean_pred']:.4f}, bullish={row['bullish_pct']*100:.0f}%")

        # Validation report summary
        if validation_report:
            context_parts.append(f"\n=== Validation Results ===")
            context_parts.append(f"Valid: {validation_report.get('valid', 'N/A')}")
            for e in validation_report.get('errors', []):
                context_parts.append(f"  ERROR: {e}")
            for w in validation_report.get('warnings', []):
                context_parts.append(f"  WARNING: {w}")
            for i in validation_report.get('info', []):
                context_parts.append(f"  INFO: {i}")

        data_context = "\n".join(context_parts)

        system_prompt = """You are a senior quantitative analyst specializing in FX (foreign exchange) trading.
You are reviewing signal data from a Weekend Pre-Lock strategy that trades USDCNH.

The strategy works as follows:
- Signals are generated on Friday evening (Beijing time ~22:30) through Saturday early morning (~01:30)
- Each signal has a `prediction` (0~1, >=0.5 = bullish) and `confidence` score
- Trades are executed based on prediction & confidence thresholds
- Position is unwound at a fixed Saturday exit time (e.g., 02:00 Beijing)

Your task: Provide a concise, professional analysis covering:
1. **Data Quality Assessment** — completeness, anomalies, null values, time window compliance
2. **Signal Distribution Analysis** — prediction/confidence distributions, skewness, any clustering
3. **Trend Analysis** — recent weeks bullish/bearish trend, any regime changes
4. **Risk Flags** — potential issues: low confidence periods, prediction drift, data gaps
5. **Recommendations** — suggested threshold ranges for grid search, any data cleaning needed

Use bullet points, be specific with numbers. Keep the analysis actionable and under 800 words.
Respond in the same language as the data context (English if data is in English)."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please analyze the following signal data:\n\n{data_context}"},
        ]

        # Call LLM with streaming
        # Append /chat/completions (works for both OpenAI /v1 and fit-ai proxy)
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            resp = _requests.post(url, headers=headers, json=payload,
                                  stream=True, timeout=timeout)
            resp.raise_for_status()

            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith('data:'):
                    continue
                data_str = line[5:].strip()
                if data_str == '[DONE]':
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get('choices', [{}])[0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        yield content
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

        except _requests.exceptions.Timeout:
            yield "\n\n[Error: LLM request timed out. Check your network or increase `llm.timeout` in config.yaml]"
        except _requests.exceptions.ConnectionError:
            yield f"\n\n[Error: Cannot connect to {base_url}. Check `llm.base_url` in config.yaml]"
        except _requests.exceptions.HTTPError as e:
            yield f"\n\n[Error: LLM API returned HTTP {e.response.status_code}. Check your API key and model name]"
        except Exception as e:
            yield f"\n\n[Error: {str(e)}]"

    def _signal_summary(self):
        sig = self.signals
        # Convert sample rows safely (Timestamp -> str)
        sample = sig.head(5).copy()
        for col in sample.columns:
            if pd.api.types.is_datetime64_any_dtype(sample[col]):
                sample[col] = sample[col].astype(str)
        return {
            'total_signals': int(len(sig)),
            'total_weeks': int(sig['year_week'].nunique()),
            'weeks': sorted(sig['year_week'].unique().tolist()),
            'date_range': [str(sig['predict_time'].min()), str(sig['predict_time'].max())],
            'prediction_stats': {
                'mean': round(float(sig['prediction'].mean()), 4),
                'std': round(float(sig['prediction'].std()), 4),
                'min': round(float(sig['prediction'].min()), 4),
                'max': round(float(sig['prediction'].max()), 4),
            },
            'confidence_stats': {
                'mean': round(float(sig['confidence'].mean()), 4),
                'std': round(float(sig['confidence'].std()), 4),
                'min': round(float(sig['confidence'].min()), 4),
                'max': round(float(sig['confidence'].max()), 4),
            },
            'bullish_pct': round(float((sig['prediction'] >= 0.5).mean()), 4),
            'columns': list(sig.columns),
            'sample_rows': sample.to_dict('records'),
        }

    def load_prices(self, file_path):
        """Step 2: Load market price file (CSV with entry_price/exit_price columns)."""
        path = Path(file_path)
        if not path.is_absolute():
            path = (BASE_DIR / file_path).resolve()

        self.prices = pd.read_csv(path).dropna(subset=['entry_price', 'exit_price'])
        self.entry_map = dict(zip(self.prices['year_week'], self.prices['entry_price']))
        self.exit_map = dict(zip(self.prices['year_week'], self.prices['exit_price']))
        self._price_source = 'csv'

        # If signals already loaded, prepare weekly
        if self.signals_loaded:
            self._prepare_weekly()

        return self._price_summary()

    def load_bbg_ticks(self, file_path, entry_offset_minutes=0, exit_hour=2, exit_minute=0):
        """Step 2 (alt): Load BBG second-level bid/ask data and extract entry/exit prices.

        Long-only strategy — all prices use ASK (buy side).
        Logic:
        - Entry Price: For each signal_time, find nearest tick → ask
        - Exit Price: For each week, find tick nearest to Saturday 02:00 Beijing → ask
        - entry_offset_minutes: offset from signal_time in minutes (0 = exact match)
        - exit_hour/exit_minute: exit reference time on Saturday (Beijing time)
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = (BASE_DIR / file_path).resolve()

        # Load Excel (BBG tick data)
        ext = path.suffix.lower()
        if ext in ('.xlsx', '.xls'):
            ticks = pd.read_excel(path)
        else:
            ticks = pd.read_csv(path)

        ticks['timestamp'] = pd.to_datetime(ticks['timestamp'])
        ticks = ticks.sort_values('timestamp').reset_index(drop=True)

        # Compute mid if not present
        if 'mid' not in ticks.columns:
            ticks['mid'] = (ticks['bid'] + ticks['ask']) / 2

        # Determine year_week for each tick (ISO week-based, matching signal convention)
        # The signal year_week is based on the Friday of that week
        # BBG tick timestamps are in Beijing time
        ticks['date'] = ticks['timestamp'].dt.date
        ticks['weekday'] = ticks['timestamp'].dt.weekday  # 0=Mon

        # Assign year_week: ticks on Sat (wd=5) belong to the previous week's Friday
        # Ticks on Fri (wd=4) belong to that Friday's week
        def assign_year_week(row):
            ts = row['timestamp']
            wd = ts.weekday()
            if wd == 5:  # Saturday → use Friday
                friday = ts - pd.Timedelta(days=1)
            elif wd == 6:  # Sunday → use Friday
                friday = ts - pd.Timedelta(days=2)
            elif wd == 4:  # Friday
                friday = ts
            else:
                friday = ts - pd.Timedelta(days=(wd - 4) % 7)
            iso = friday.isocalendar()
            return f"{iso[0]}_{iso[1]:02d}"

        ticks['year_week'] = ticks.apply(assign_year_week, axis=1)

        # Store tick data for preview
        self._bbg_ticks = ticks
        self._bbg_tick_file = path.name

        # Build price table from ticks
        # We need signal times from the loaded signals to match entry prices
        price_rows = []
        weeks = sorted(ticks['year_week'].unique())

        for yw in weeks:
            wk_ticks = ticks[ticks['year_week'] == yw].copy()
            if len(wk_ticks) == 0:
                continue

            # Find Friday date
            first_ts = wk_ticks['timestamp'].iloc[0]
            wd = first_ts.weekday()
            if wd == 5:
                friday_date = (first_ts - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                saturday_date = first_ts.strftime('%Y-%m-%d')
            elif wd == 4:
                friday_date = first_ts.strftime('%Y-%m-%d')
                saturday_date = (first_ts + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                friday_date = first_ts.strftime('%Y-%m-%d')
                saturday_date = first_ts.strftime('%Y-%m-%d')

            # Entry: if signals loaded, use signal_time; otherwise use first available tick
            entry_price = None
            signal_time_str = None

            if self.signals_loaded and self.signals is not None:
                sig_week = self.signals[self.signals['year_week'] == yw]
                if len(sig_week) > 0:
                    sig_time = sig_week['predict_time'].max()
                    target_time = sig_time + pd.Timedelta(minutes=entry_offset_minutes)
                    # Find nearest tick
                    time_diffs = (wk_ticks['timestamp'] - target_time).abs()
                    nearest_idx = time_diffs.idxmin()
                    entry_price = float(wk_ticks.loc[nearest_idx, 'ask'])
                    signal_time_str = str(sig_time)

            if entry_price is None:
                # Fallback: use first tick's ask
                entry_price = float(wk_ticks['ask'].iloc[0])
                signal_time_str = str(wk_ticks['timestamp'].iloc[0])

            # Exit: Saturday at exit_hour:exit_minute
            sat_ticks = wk_ticks[wk_ticks['weekday'] == 5]  # Saturday ticks
            if len(sat_ticks) > 0:
                sat_date = sat_ticks['timestamp'].iloc[0].normalize()
                exit_target = sat_date + pd.Timedelta(hours=exit_hour, minutes=exit_minute)
                time_diffs = (sat_ticks['timestamp'] - exit_target).abs()
                nearest_idx = time_diffs.idxmin()
                exit_price = float(sat_ticks.loc[nearest_idx, 'ask'])
            else:
                # No Saturday ticks, use last tick's ask
                exit_price = float(wk_ticks['ask'].iloc[-1])

            price_rows.append({
                'year_week': yw,
                'friday_date': friday_date,
                'saturday_date': saturday_date,
                'signal_time': signal_time_str,
                'entry_price': round(entry_price, 5),
                'exit_price': round(exit_price, 5),
            })

        self.prices = pd.DataFrame(price_rows)
        if len(self.prices) == 0:
            raise ValueError("No valid price data extracted from BBG tick file")

        self.entry_map = dict(zip(self.prices['year_week'], self.prices['entry_price']))
        self.exit_map = dict(zip(self.prices['year_week'], self.prices['exit_price']))
        self._price_source = 'bbg_ticks'

        if self.signals_loaded:
            self._prepare_weekly()

        return self._price_summary_bbg(ticks)

    def load_intraday(self, file_path, entry_window_minutes=30, exit_hour=2, exit_minute=0):
        """Step 2 (alt): Load intraday data and extract entry/exit prices.

        Long-only strategy — all prices use ASK (buy side).
        Supports two formats:
        - OHLCV (columns: timestamp, open, high, low, close, volume) → uses close
        - BBG bid/ask bars (columns: timestamp, bid, ask, mid, spread) → uses ask for both entry and exit
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = (BASE_DIR / file_path).resolve()

        ext = path.suffix.lower()
        if ext in ('.xlsx', '.xls'):
            bars = pd.read_excel(path)
        else:
            bars = pd.read_csv(path)

        bars['timestamp'] = pd.to_datetime(bars['timestamp'])
        bars = bars.sort_values('timestamp').reset_index(drop=True)

        # Detect format: BBG bid/ask or OHLCV
        is_bidask = 'bid' in bars.columns and 'ask' in bars.columns
        entry_col = 'ask' if is_bidask else 'close'
        exit_col = 'ask' if is_bidask else 'close'

        # If mid column missing but bid/ask present, compute it (for reference only)
        if is_bidask and 'mid' not in bars.columns:
            bars['mid'] = (bars['bid'] + bars['ask']) / 2

        # Assign year_week (use existing column if present from BBG download)
        bars['weekday'] = bars['timestamp'].dt.weekday

        if 'year_week' not in bars.columns:
            def assign_year_week_bar(ts):
                wd = ts.weekday()
                if wd == 5:
                    friday = ts - pd.Timedelta(days=1)
                elif wd == 6:
                    friday = ts - pd.Timedelta(days=2)
                elif wd == 4:
                    friday = ts
                else:
                    friday = ts - pd.Timedelta(days=(wd - 4) % 7)
                iso = friday.isocalendar()
                return f"{iso[0]}_{iso[1]:02d}"

            bars['year_week'] = bars['timestamp'].apply(assign_year_week_bar)

        self._intraday_bars = bars
        self._intraday_file = path.name

        # Pre-build sorted timestamp index + ask price array for O(log N) entry price lookup
        bars_sorted = bars.sort_values('timestamp').reset_index(drop=True)
        self._intraday_ts_index = bars_sorted['timestamp'].values.astype('int64')  # ns since epoch
        ask_col = 'ask' if 'ask' in bars_sorted.columns else ('mid' if 'mid' in bars_sorted.columns else 'close')
        self._intraday_ask_arr = bars_sorted[ask_col].values.astype(float)
        # Bid prices for stop loss unwind (sell side)
        bid_col = 'bid' if 'bid' in bars_sorted.columns else ask_col
        self._intraday_bid_arr = bars_sorted[bid_col].values.astype(float)

        # Build price table
        price_rows = []
        weeks = sorted(bars['year_week'].unique())

        for yw in weeks:
            wk_bars = bars[bars['year_week'] == yw].copy()
            if len(wk_bars) == 0:
                continue

            first_ts = wk_bars['timestamp'].iloc[0]
            wd = first_ts.weekday()
            if wd == 5:
                friday_date = (first_ts - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                saturday_date = first_ts.strftime('%Y-%m-%d')
            elif wd == 4:
                friday_date = first_ts.strftime('%Y-%m-%d')
                saturday_date = (first_ts + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                friday_date = first_ts.strftime('%Y-%m-%d')
                saturday_date = first_ts.strftime('%Y-%m-%d')

            # Use friday_date/saturday_date from data if available
            if 'friday_date' in wk_bars.columns:
                friday_date = str(wk_bars['friday_date'].iloc[0])
            if 'saturday_date' in wk_bars.columns:
                saturday_date = str(wk_bars['saturday_date'].iloc[0])

            # Entry price
            entry_price = None
            signal_time_str = None

            if self.signals_loaded and self.signals is not None:
                sig_week = self.signals[self.signals['year_week'] == yw]
                if len(sig_week) > 0:
                    sig_time = sig_week['predict_time'].max()
                    # Find nearest bar
                    time_diffs = (wk_bars['timestamp'] - sig_time).abs()
                    nearest_idx = time_diffs.idxmin()
                    entry_price = float(wk_bars.loc[nearest_idx, entry_col])
                    signal_time_str = str(sig_time)

            if entry_price is None:
                entry_price = float(wk_bars[entry_col].iloc[0])
                signal_time_str = str(wk_bars['timestamp'].iloc[0])

            # Exit price: Saturday at exit_hour:exit_minute
            sat_bars = wk_bars[wk_bars['weekday'] == 5]
            if len(sat_bars) > 0:
                sat_date = sat_bars['timestamp'].iloc[0].normalize()
                exit_target = sat_date + pd.Timedelta(hours=exit_hour, minutes=exit_minute)
                time_diffs = (sat_bars['timestamp'] - exit_target).abs()
                nearest_idx = time_diffs.idxmin()
                exit_price = float(sat_bars.loc[nearest_idx, exit_col])
            else:
                exit_price = float(wk_bars[exit_col].iloc[-1])

            price_rows.append({
                'year_week': yw,
                'friday_date': friday_date,
                'saturday_date': saturday_date,
                'signal_time': signal_time_str,
                'entry_price': round(entry_price, 5),
                'exit_price': round(exit_price, 5),
            })

        self.prices = pd.DataFrame(price_rows)
        if len(self.prices) == 0:
            raise ValueError("No valid price data extracted from intraday file")

        self.entry_map = dict(zip(self.prices['year_week'], self.prices['entry_price']))
        self.exit_map = dict(zip(self.prices['year_week'], self.prices['exit_price']))
        self._price_source = 'intraday'

        if self.signals_loaded:
            self._prepare_weekly()

        return self._price_summary_intraday(bars)

    def _price_summary_intraday(self, bars):
        """Summary for intraday data loading."""
        p = self.prices
        sample = p.head(5).copy()
        for col in sample.columns:
            if pd.api.types.is_datetime64_any_dtype(sample[col]):
                sample[col] = sample[col].astype(str)

        date_range = [str(bars['timestamp'].min()), str(bars['timestamp'].max())]
        interval_sec = bars['timestamp'].diff().median().total_seconds() if len(bars) > 1 else 0

        return {
            'total_rows': int(len(p)),
            'weeks': sorted(p['year_week'].unique().tolist()),
            'columns': list(p.columns),
            'valid_weeks': len(self.valid_weeks) if self.valid_weeks else 0,
            'sample_rows': sample.to_dict('records'),
            'source': 'intraday',
            'intraday_info': {
                'total_bars': int(len(bars)),
                'date_range': date_range,
                'interval_seconds': round(float(interval_sec), 1),
                'file_name': getattr(self, '_intraday_file', ''),
                'price_range': self._intraday_price_range(bars),
            },
        }

    @staticmethod
    def _intraday_price_range(bars):
        """Get price range from intraday bars, supporting both OHLCV and bid/ask formats."""
        if 'low' in bars.columns and 'high' in bars.columns:
            return [round(float(bars['low'].min()), 5), round(float(bars['high'].max()), 5)]
        elif 'bid' in bars.columns and 'ask' in bars.columns:
            return [round(float(bars['bid'].min()), 5), round(float(bars['ask'].max()), 5)]
        elif 'mid' in bars.columns:
            return [round(float(bars['mid'].min()), 5), round(float(bars['mid'].max()), 5)]
        elif 'close' in bars.columns:
            return [round(float(bars['close'].min()), 5), round(float(bars['close'].max()), 5)]
        return [0, 0]

    def get_price_chart_data(self):
        """Return loaded price data for visualisation in Step 2."""
        if self.prices is None:
            return None

        p = self.prices.copy()
        result = {
            'weeks': p['year_week'].tolist(),
            'entry_prices': [round(float(v), 5) for v in p['entry_price'].tolist()],
            'exit_prices': [round(float(v), 5) for v in p['exit_price'].tolist()],
            'pnl_pips': [round(float((e - n) * 10000), 1) for n, e in zip(p['entry_price'], p['exit_price'])],
            'spreads': [round(float(abs(e - n)), 5) for n, e in zip(p['entry_price'], p['exit_price'])],
            'friday_dates': p['friday_date'].tolist() if 'friday_date' in p.columns else [],
            'saturday_dates': p['saturday_date'].tolist() if 'saturday_date' in p.columns else [],
            'signal_times': p['signal_time'].astype(str).tolist() if 'signal_time' in p.columns else [],
            'source': getattr(self, '_price_source', 'csv'),
        }

        # If intraday bars available, add OHLC for richer chart
        if hasattr(self, '_intraday_bars') and self._intraday_bars is not None:
            bars = self._intraday_bars
            # Resample to hourly for chart
            hourly = bars.set_index('timestamp').resample('1h').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
            }).dropna().reset_index()
            result['ohlc'] = {
                'timestamps': [str(t) for t in hourly['timestamp'].tolist()],
                'open': [round(float(v), 5) for v in hourly['open'].tolist()],
                'high': [round(float(v), 5) for v in hourly['high'].tolist()],
                'low': [round(float(v), 5) for v in hourly['low'].tolist()],
                'close': [round(float(v), 5) for v in hourly['close'].tolist()],
            }

        return result

    def _price_summary(self):
        p = self.prices
        sample = p.head(5).copy()
        for col in sample.columns:
            if pd.api.types.is_datetime64_any_dtype(sample[col]):
                sample[col] = sample[col].astype(str)
        return {
            'total_rows': int(len(p)),
            'weeks': sorted(p['year_week'].unique().tolist()),
            'columns': list(p.columns),
            'valid_weeks': len(self.valid_weeks) if self.valid_weeks else 0,
            'sample_rows': sample.to_dict('records'),
            'source': getattr(self, '_price_source', 'csv'),
        }

    def _price_summary_bbg(self, ticks):
        """Summary for BBG tick-based price loading."""
        p = self.prices
        sample = p.head(5).copy()
        for col in sample.columns:
            if pd.api.types.is_datetime64_any_dtype(sample[col]):
                sample[col] = sample[col].astype(str)

        tick_date_range = [str(ticks['timestamp'].min()), str(ticks['timestamp'].max())]
        interval_sec = ticks['timestamp'].diff().median().total_seconds() if len(ticks) > 1 else 0

        return {
            'total_rows': int(len(p)),
            'weeks': sorted(p['year_week'].unique().tolist()),
            'columns': list(p.columns),
            'valid_weeks': len(self.valid_weeks) if self.valid_weeks else 0,
            'sample_rows': sample.to_dict('records'),
            'source': 'bbg_ticks',
            'tick_info': {
                'total_ticks': int(len(ticks)),
                'date_range': tick_date_range,
                'interval_seconds': round(float(interval_sec), 1),
                'file_name': getattr(self, '_bbg_tick_file', ''),
                'bid_range': [round(float(ticks['bid'].min()), 5), round(float(ticks['bid'].max()), 5)],
                'ask_range': [round(float(ticks['ask'].min()), 5), round(float(ticks['ask'].max()), 5)],
                'avg_spread': round(float(ticks['spread'].mean()) if 'spread' in ticks.columns else float((ticks['ask'] - ticks['bid']).mean()), 5),
            }
        }

    def _prepare_weekly(self):
        """Called automatically when both signals and prices are loaded.
        
        Builds:
        - _weekly_all_signals: ALL signals per week (sorted by time) for tranche execution
        - weekly_signals: last signal per week (for single-shot mode, filtered to trading window)
        """
        sig = self.signals.copy()

        sig_weeks = set(sig['year_week'].unique())
        price_weeks = set(self.prices['year_week'])
        self.valid_weeks = sorted(sig_weeks & price_weeks)

        sig_valid = sig[sig['year_week'].isin(self.valid_weeks)]

        # Store signals per week for tranche execution — FILTERED to trading window (22:30~01:30)
        sig_sorted = sig_valid.sort_values('predict_time').copy()
        sig_sorted['_hour'] = sig_sorted['predict_time'].dt.hour
        sig_sorted['_minute'] = sig_sorted['predict_time'].dt.minute
        sig_sorted['_td'] = sig_sorted['_hour'] + sig_sorted['_minute'] / 60
        sig_sorted['_wd'] = sig_sorted['predict_time'].dt.weekday
        fri_mask = (sig_sorted['_wd'] == 4) & (sig_sorted['_td'] >= 22.5)
        sat_mask = (sig_sorted['_wd'] == 5) & (sig_sorted['_td'] <= 1.5)
        sig_in_window = sig_sorted[fri_mask | sat_mask].copy()
        sig_in_window = sig_in_window.drop(columns=['_hour', '_minute', '_td', '_wd'])

        self._weekly_all_signals = {}
        for yw, grp in sig_in_window.groupby('year_week'):
            self._weekly_all_signals[yw] = grp.reset_index(drop=True)

        # For single-shot mode: filter to trading window (Fri 22:30+ and Sat <=01:30)
        sig_filtered = sig_valid.copy()
        sig_filtered['hour'] = sig_filtered['predict_time'].dt.hour
        sig_filtered['minute'] = sig_filtered['predict_time'].dt.minute
        sig_filtered['td'] = sig_filtered['hour'] + sig_filtered['minute'] / 60
        sig_filtered['wd'] = sig_filtered['predict_time'].dt.weekday

        friday = (sig_filtered['wd'] == 4) & (sig_filtered['td'] >= 22.5)
        saturday = (sig_filtered['wd'] == 5) & (sig_filtered['td'] <= 1.5)
        sig_filtered = sig_filtered[friday | saturday]

        # Legacy: last signal per week (for single-shot mode)
        self.weekly_signals = (
            sig_filtered.sort_values('predict_time').groupby('year_week').last().reset_index()
        )

        # Ensure all valid weeks are represented (some weeks may have no signals in window)
        # Fill missing weeks from all_signals (use last signal)
        for yw in self.valid_weeks:
            if yw not in self.weekly_signals['year_week'].values:
                week_sigs = self._weekly_all_signals.get(yw)
                if week_sigs is not None and len(week_sigs) > 0:
                    last_sig = week_sigs.iloc[[-1]].copy()
                    self.weekly_signals = pd.concat([self.weekly_signals, last_sig], ignore_index=True)

        self.weekly_signals = self.weekly_signals.sort_values('year_week').reset_index(drop=True)

        self._weeks = self.weekly_signals['year_week'].values
        self._preds = self.weekly_signals['prediction'].values
        self._confs = self.weekly_signals['confidence'].values
        self._entry = np.array([self.entry_map.get(w, np.nan) for w in self._weeks])
        self._exit = np.array([self.exit_map.get(w, np.nan) for w in self._weeks])
        self._pnl_if_trade = (self._exit - self._entry) / self._entry * self.trade_size

    def run_single(self, pred_th=0.5, conf_th=0.0):
        if not self.ready:
            return None

        mask = (self._preds >= pred_th) & (self._confs > conf_th)
        pnl_arr = np.where(mask, self._pnl_if_trade, 0.0)
        cum_pnl = np.cumsum(pnl_arr)
        running_max = np.maximum.accumulate(cum_pnl)
        drawdown = cum_pnl - running_max

        trades = []
        for i, w in enumerate(self._weeks):
            row = self.weekly_signals.iloc[i]
            bought = bool(mask[i])
            return_pct = round(float(pnl_arr[i] / self.trade_size * 100), 4) if bought and self.trade_size > 0 else 0.0
            trades.append({
                'year_week': w,
                'predict_time': str(row['predict_time']),
                'prediction': round(float(self._preds[i]), 4),
                'confidence': round(float(self._confs[i]), 4),
                'confidence_0': round(float(row['confidence_0']), 4),
                'confidence_1': round(float(row['confidence_1']), 4),
                'direction': 'BULLISH' if self._preds[i] >= 0.5 else 'BEARISH',
                'should_buy': bought,
                'entry_price': round(float(self._entry[i]), 5) if bought else None,
                'exit_price': round(float(self._exit[i]), 5) if bought else None,
                'pips': round(float((self._exit[i] - self._entry[i]) * 10000), 1),
                'pnl': round(float(pnl_arr[i]), 2),
                'return_pct': return_pct,
                'cum_pnl': round(float(cum_pnl[i]), 2),
                'drawdown': round(float(drawdown[i]), 2),
            })

        trade_mask = mask
        trade_pnls = pnl_arr[trade_mask]
        n_trades = int(trade_mask.sum())
        total_pnl = float(pnl_arr.sum())
        wins = trade_pnls[trade_pnls > 0]
        losses = trade_pnls[trade_pnls < 0]
        std = pnl_arr.std()

        metrics = {
            'total_pnl': round(total_pnl, 2),
            'num_trades': n_trades,
            'num_weeks': len(self._weeks),
            'trade_freq': round(n_trades / len(self._weeks), 4) if len(self._weeks) > 0 else 0,
            'win_rate': round(float(len(wins) / n_trades), 4) if n_trades > 0 else 0,
            'avg_pnl_trade': round(total_pnl / n_trades, 2) if n_trades > 0 else 0,
            'avg_pnl_week': round(total_pnl / len(self._weeks), 2),
            'sharpe': round(float((pnl_arr.mean() / std) * np.sqrt(52)), 4) if std > 0 else 0,
            'max_drawdown': round(float(drawdown.min()), 2),
            'profit_factor': round(float(wins.sum() / abs(losses.sum())), 4) if len(losses) > 0 and losses.sum() != 0 else 9999.0,
            'avg_win': round(float(wins.mean()), 2) if len(wins) > 0 else 0,
            'avg_loss': round(float(losses.mean()), 2) if len(losses) > 0 else 0,
            'max_win': round(float(wins.max()), 2) if len(wins) > 0 else 0,
            'max_loss': round(float(losses.min()), 2) if len(losses) > 0 else 0,
        }

        return {'trades': trades, 'metrics': metrics, 'params': {'pred_threshold': pred_th, 'conf_threshold': conf_th}}

    # ---------- Tranche Execution ----------
    # Trading window: Fri 22:30 ~ Sat 01:30 (7 signal slots every 30 min)
    # Reference/exit: Sat 02:00
    # Each slot gets 1/N of total notional. If signal < threshold → SKIP,
    # that slot's amount carries over to next slot. Multiple executions per week.

    def _get_entry_price_at_time(self, sig_time, year_week):
        """Get entry price (ask) at a specific signal time from intraday data.
        
        Long-only strategy: we BUY at ASK price.
        
        Uses the pre-built intraday timestamp index for O(log N) lookup.
        Matches by absolute timestamp (no year_week dependency), tolerating
        up to 5 minutes of difference. This is robust against year_week
        assignment mismatches between signal and price files.
        
        Falls back to the week's single entry_price if intraday data
        is unavailable or no bar is found within tolerance.
        """
        if hasattr(self, '_intraday_ts_index') and self._intraday_ts_index is not None:
            sig_ts = pd.to_datetime(sig_time)
            ts_arr = self._intraday_ts_index  # sorted numpy array of int64 (ns)
            sig_ns = sig_ts.value  # nanoseconds since epoch

            # Binary search for nearest timestamp
            idx = np.searchsorted(ts_arr, sig_ns)
            candidates = []
            if idx > 0:
                candidates.append(idx - 1)
            if idx < len(ts_arr):
                candidates.append(idx)

            best_idx = min(candidates, key=lambda i: abs(ts_arr[i] - sig_ns))
            diff_seconds = abs(ts_arr[best_idx] - sig_ns) / 1e9

            # Only use if within 5 minutes (300 seconds)
            if diff_seconds <= 300:
                return float(self._intraday_ask_arr[best_idx])

        # Fall back to week-level entry price
        return self.entry_map.get(year_week, np.nan)

    def _get_bid_price_at_time(self, sig_time):
        """Get bid price at a specific time (for stop loss unwind — sell side).
        
        Returns np.nan if no intraday data or no bar within 5-minute tolerance.
        """
        if hasattr(self, '_intraday_ts_index') and self._intraday_ts_index is not None:
            sig_ts = pd.to_datetime(sig_time)
            ts_arr = self._intraday_ts_index
            sig_ns = sig_ts.value

            idx = np.searchsorted(ts_arr, sig_ns)
            candidates = []
            if idx > 0:
                candidates.append(idx - 1)
            if idx < len(ts_arr):
                candidates.append(idx)

            best_idx = min(candidates, key=lambda i: abs(ts_arr[i] - sig_ns))
            diff_seconds = abs(ts_arr[best_idx] - sig_ns) / 1e9

            if diff_seconds <= 300:
                return float(self._intraday_bid_arr[best_idx])

        return np.nan

    def _check_stop_loss(self, avg_entry_price, start_time, end_time, stop_loss_bps):
        """Check if stop loss is triggered between start_time and end_time.
        
        Monitors minute-level BID prices after entry. If bid price drops enough
        that (avg_entry - bid) / avg_entry >= stop_loss_bps / 10000, we unwind.
        
        Long-only position: we bought at ASK, so loss = (entry_ask - current_bid) / entry_ask.
        If the market moves DOWN (bid falls below entry), that's a loss for a long position.
        
        Args:
            avg_entry_price: weighted average entry ASK price of executed tranches
            start_time: start monitoring from this timestamp
            end_time: stop monitoring at this timestamp (e.g. next signal time or exit time)
            stop_loss_bps: stop loss threshold in basis points (e.g. 10 = 10bps = 0.10%)
        
        Returns:
            (triggered: bool, unwind_time: Timestamp or None, unwind_bid: float or None)
        """
        if stop_loss_bps is None or stop_loss_bps <= 0:
            return False, None, None
        if self._intraday_ts_index is None:
            raise ValueError("Stop Loss requested but intraday data is not loaded. Call ensure_intraday_loaded() first.")

        threshold = stop_loss_bps / 10000.0  # convert bps to decimal
        start_ns = pd.to_datetime(start_time).value
        end_ns = pd.to_datetime(end_time).value

        ts_arr = self._intraday_ts_index
        bid_arr = self._intraday_bid_arr

        # Find the range of bars between start_time and end_time
        start_idx = np.searchsorted(ts_arr, start_ns, side='left')
        end_idx = np.searchsorted(ts_arr, end_ns, side='right')

        for i in range(start_idx, min(end_idx, len(ts_arr))):
            bid = bid_arr[i]
            if np.isnan(bid) or bid == 0:
                continue
            # Loss for long position: (entry - bid) / entry
            loss_pct = (avg_entry_price - bid) / avg_entry_price
            if loss_pct >= threshold:
                unwind_time = pd.Timestamp(ts_arr[i], unit='ns')
                return True, unwind_time, float(bid)

        return False, None, None

    def _check_profit_taking(self, avg_entry_price, start_time, end_time, profit_taking_bps):
        """Check if profit taking is triggered between start_time and end_time.
        
        Monitors minute-level BID prices after entry. If bid price rises enough
        that (bid - avg_entry) / avg_entry >= profit_taking_bps / 10000, we unwind
        to lock in profit.
        
        Long-only position: we bought at ASK, profit = (current_bid - entry_ask) / entry_ask.
        If the market moves UP (bid rises above entry), that's a profit for a long position.
        
        Args:
            avg_entry_price: weighted average entry ASK price of executed tranches
            start_time: start monitoring from this timestamp
            end_time: stop monitoring at this timestamp
            profit_taking_bps: profit taking threshold in basis points (e.g. 15 = 15bps = 0.15%)
        
        Returns:
            (triggered: bool, unwind_time: Timestamp or None, unwind_bid: float or None)
        """
        if profit_taking_bps is None or profit_taking_bps <= 0:
            return False, None, None
        if self._intraday_ts_index is None:
            raise ValueError("Profit Taking requested but intraday data is not loaded. Call ensure_intraday_loaded() first.")

        threshold = profit_taking_bps / 10000.0
        start_ns = pd.to_datetime(start_time).value
        end_ns = pd.to_datetime(end_time).value

        ts_arr = self._intraday_ts_index
        bid_arr = self._intraday_bid_arr

        start_idx = np.searchsorted(ts_arr, start_ns, side='left')
        end_idx = np.searchsorted(ts_arr, end_ns, side='right')

        for i in range(start_idx, min(end_idx, len(ts_arr))):
            bid = bid_arr[i]
            if np.isnan(bid) or bid == 0:
                continue
            # Profit for long position: (bid - entry) / entry
            gain_pct = (bid - avg_entry_price) / avg_entry_price
            if gain_pct >= threshold:
                unwind_time = pd.Timestamp(ts_arr[i], unit='ns')
                return True, unwind_time, float(bid)

        return False, None, None

    def _check_sl_pt(self, avg_entry_price, start_time, end_time, stop_loss_bps, profit_taking_bps):
        """Check both stop loss and profit taking in a single pass (minute-level).
        
        Scans BID prices chronologically. Returns whichever triggers FIRST.
        
        Returns:
            (event_type: str or None, unwind_time, unwind_bid)
            event_type is 'SL', 'PT', or None
        """
        has_sl = stop_loss_bps is not None and stop_loss_bps > 0
        has_pt = profit_taking_bps is not None and profit_taking_bps > 0
        if not has_sl and not has_pt:
            return None, None, None
        if self._intraday_ts_index is None:
            raise ValueError("SL/PT requested but intraday data is not loaded. Call ensure_intraday_loaded() first.")

        sl_threshold = stop_loss_bps / 10000.0 if has_sl else float('inf')
        pt_threshold = profit_taking_bps / 10000.0 if has_pt else float('inf')
        start_ns = pd.to_datetime(start_time).value
        end_ns = pd.to_datetime(end_time).value

        ts_arr = self._intraday_ts_index
        bid_arr = self._intraday_bid_arr

        start_idx = np.searchsorted(ts_arr, start_ns, side='left')
        end_idx = np.searchsorted(ts_arr, end_ns, side='right')

        for i in range(start_idx, min(end_idx, len(ts_arr))):
            bid = bid_arr[i]
            if np.isnan(bid) or bid == 0:
                continue
            diff_pct = (bid - avg_entry_price) / avg_entry_price
            # Profit taking: bid rose above entry
            if has_pt and diff_pct >= pt_threshold:
                return 'PT', pd.Timestamp(ts_arr[i], unit='ns'), float(bid)
            # Stop loss: bid dropped below entry (diff_pct is negative)
            if has_sl and (-diff_pct) >= sl_threshold:
                return 'SL', pd.Timestamp(ts_arr[i], unit='ns'), float(bid)

        return None, None, None

    def run_single_tranche(self, pred_th=0.5, conf_th=0.0, tranche_size=None, stop_loss_bps=None, profit_taking_bps=None):
        """Run backtest with tranche execution (long-only, ASK price) + optional stop loss / profit taking.
        
        Args:
            pred_th: prediction threshold
            conf_th: confidence threshold
            tranche_size: USD amount per tranche. If None, auto = trade_size / N per week.
            stop_loss_bps: stop loss in basis points. None = disabled.
            profit_taking_bps: profit taking in basis points. None = disabled.
        
        Stop Loss:  (avg_entry - bid) / avg_entry >= threshold → unwind at BID, stop tonight
        Profit Taking: (bid - avg_entry) / avg_entry >= threshold → unwind at BID, lock profit, stop tonight
        Both monitored minute-by-minute; whichever triggers first wins.
        """
        if not self.ready:
            return None
        if self._weekly_all_signals is None:
            return None

        # Auto-load intraday data if SL/PT is requested
        has_sl = stop_loss_bps is not None and stop_loss_bps > 0
        has_pt = profit_taking_bps is not None and profit_taking_bps > 0
        if has_sl or has_pt:
            self.ensure_intraday_loaded()

        trades = []
        all_tranche_details = []

        for i, w in enumerate(self._weeks):
            exit_price = self._exit[i]

            if np.isnan(exit_price):
                trades.append(self._make_no_trade_row(i, w, 'tranche'))
                continue

            week_sigs = self._weekly_all_signals.get(w)
            if week_sigs is None or len(week_sigs) == 0:
                trades.append(self._make_no_trade_row(i, w, 'tranche'))
                continue

            n_slots = len(week_sigs)
            use_fixed_size = tranche_size is not None and tranche_size > 0
            if use_fixed_size:
                # Fixed dollar amount per tranche
                base_amount = tranche_size
                weekly_notional = base_amount * n_slots  # theoretical max
                base_weight = base_amount / weekly_notional  # for weight tracking
            else:
                # Equal weight: each slot = trade_size / N
                base_weight = 1.0 / n_slots
                weekly_notional = self.trade_size

            total_executed = 0.0
            accumulated_weight = 0.0
            tranche_details = []
            week_pnl = 0.0
            total_exec_amount = 0.0
            weighted_entry_sum = 0.0
            stop_loss_triggered = False
            stop_loss_info = None
            profit_taking_triggered = False
            profit_taking_info = None
            early_exit_triggered = False  # True if SL or PT triggered

            # Collect executed tranches for recalculation
            executed_tranches = []  # list of (entry_price, exec_amount)

            # Get exit time for monitoring (Saturday 02:00 of this week)
            last_sig_time = week_sigs.iloc[-1]['predict_time']
            if last_sig_time.weekday() == 4:  # Friday
                exit_datetime = (last_sig_time + pd.Timedelta(days=1)).normalize() + pd.Timedelta(hours=2)
            else:  # Saturday
                exit_datetime = last_sig_time.normalize() + pd.Timedelta(hours=2)

            for s_idx, (_, sig_row) in enumerate(week_sigs.iterrows()):
                sig_pred = float(sig_row['prediction'])
                sig_conf = float(sig_row['confidence'])
                sig_time = sig_row['predict_time']
                sig_time_str = str(sig_time)
                available_weight = accumulated_weight + base_weight

                # If SL or PT was triggered, mark remaining slots as STOPPED
                if early_exit_triggered:
                    tranche_details.append({
                        'slot_idx': s_idx + 1,
                        'slot_total': n_slots,
                        'signal_time': sig_time_str,
                        'prediction': round(sig_pred, 4),
                        'confidence': round(sig_conf, 4),
                        'base_weight': round(base_weight, 4),
                        'available_weight': 0.0,
                        'executed_weight': 0.0,
                        'entry_price': None,
                        'amount_usd': 0.0,
                        'pnl': 0.0,
                        'action': 'STOPPED (SL)' if stop_loss_triggered else 'STOPPED (PT)',
                    })
                    continue

                should_exec = (sig_pred >= pred_th) and (sig_conf > conf_th)

                if should_exec:
                    # Get entry price at THIS signal's time
                    this_entry = self._get_entry_price_at_time(sig_time, w)
                    if np.isnan(this_entry):
                        accumulated_weight = available_weight
                        tranche_details.append({
                            'slot_idx': s_idx + 1,
                            'slot_total': n_slots,
                            'signal_time': sig_time_str,
                            'prediction': round(sig_pred, 4),
                            'confidence': round(sig_conf, 4),
                            'base_weight': round(base_weight, 4),
                            'available_weight': round(available_weight, 4),
                            'executed_weight': 0.0,
                            'entry_price': None,
                            'amount_usd': 0.0,
                            'pnl': 0.0,
                            'action': 'SKIP (no price)',
                        })
                        continue

                    exec_amount = available_weight * weekly_notional
                    executed_tranches.append((this_entry, exec_amount))
                    total_executed += available_weight
                    total_exec_amount += exec_amount
                    weighted_entry_sum += this_entry * exec_amount

                    # Tentative PnL (will be overridden if stop loss triggers)
                    tranche_pnl = (exit_price - this_entry) / this_entry * exec_amount
                    week_pnl += tranche_pnl

                    tranche_details.append({
                        'slot_idx': s_idx + 1,
                        'slot_total': n_slots,
                        'signal_time': sig_time_str,
                        'prediction': round(sig_pred, 4),
                        'confidence': round(sig_conf, 4),
                        'base_weight': round(base_weight, 4),
                        'available_weight': round(available_weight, 4),
                        'executed_weight': round(available_weight, 4),
                        'entry_price': round(this_entry, 5),
                        'amount_usd': round(exec_amount, 0),
                        'pnl': round(tranche_pnl, 2),
                        'action': 'EXECUTE',
                    })
                    accumulated_weight = 0.0

                    # --- SL / PT Check (combined, minute-by-minute) ---
                    if total_exec_amount > 0 and (
                        (stop_loss_bps is not None and stop_loss_bps > 0) or
                        (profit_taking_bps is not None and profit_taking_bps > 0)
                    ):
                        avg_entry = weighted_entry_sum / total_exec_amount
                        if s_idx + 1 < n_slots:
                            next_sig_time = week_sigs.iloc[s_idx + 1]['predict_time']
                        else:
                            next_sig_time = exit_datetime

                        evt, evt_time, evt_bid = self._check_sl_pt(
                            avg_entry, sig_time, next_sig_time, stop_loss_bps, profit_taking_bps
                        )

                        if evt is not None:
                            early_exit_triggered = True
                            # Recalculate ALL executed tranches' PnL using unwind bid price
                            week_pnl = 0.0
                            for (t_entry, t_amount) in executed_tranches:
                                t_pnl = (evt_bid - t_entry) / t_entry * t_amount
                                week_pnl += t_pnl
                            exec_detail_idx = 0
                            unwind_label = 'SL UNWIND' if evt == 'SL' else 'PT UNWIND'
                            for td in tranche_details:
                                if td['action'] == 'EXECUTE':
                                    t_entry_price = executed_tranches[exec_detail_idx][0]
                                    t_amount = executed_tranches[exec_detail_idx][1]
                                    td['pnl'] = round((evt_bid - t_entry_price) / t_entry_price * t_amount, 2)
                                    td['action'] = f'EXECUTE → {unwind_label}'
                                    exec_detail_idx += 1
                            if evt == 'SL':
                                stop_loss_triggered = True
                                stop_loss_info = {
                                    'triggered': True,
                                    'unwind_time': str(evt_time),
                                    'unwind_bid': round(evt_bid, 5),
                                    'avg_entry': round(avg_entry, 5),
                                    'loss_bps': round((avg_entry - evt_bid) / avg_entry * 10000, 2),
                                    'threshold_bps': stop_loss_bps,
                                }
                            else:
                                profit_taking_triggered = True
                                profit_taking_info = {
                                    'triggered': True,
                                    'unwind_time': str(evt_time),
                                    'unwind_bid': round(evt_bid, 5),
                                    'avg_entry': round(avg_entry, 5),
                                    'gain_bps': round((evt_bid - avg_entry) / avg_entry * 10000, 2),
                                    'threshold_bps': profit_taking_bps,
                                }
                else:
                    accumulated_weight = available_weight
                    tranche_details.append({
                        'slot_idx': s_idx + 1,
                        'slot_total': n_slots,
                        'signal_time': sig_time_str,
                        'prediction': round(sig_pred, 4),
                        'confidence': round(sig_conf, 4),
                        'base_weight': round(base_weight, 4),
                        'available_weight': round(available_weight, 4),
                        'executed_weight': 0.0,
                        'entry_price': None,
                        'amount_usd': 0.0,
                        'pnl': 0.0,
                        'action': 'SKIP',
                    })

                    # --- SL / PT Check for SKIP slots too (position may still breach) ---
                    if total_exec_amount > 0 and (
                        (stop_loss_bps is not None and stop_loss_bps > 0) or
                        (profit_taking_bps is not None and profit_taking_bps > 0)
                    ):
                        avg_entry = weighted_entry_sum / total_exec_amount
                        if s_idx + 1 < n_slots:
                            next_sig_time = week_sigs.iloc[s_idx + 1]['predict_time']
                        else:
                            next_sig_time = exit_datetime

                        evt, evt_time, evt_bid = self._check_sl_pt(
                            avg_entry, sig_time, next_sig_time, stop_loss_bps, profit_taking_bps
                        )

                        if evt is not None:
                            early_exit_triggered = True
                            week_pnl = 0.0
                            for (t_entry, t_amount) in executed_tranches:
                                t_pnl = (evt_bid - t_entry) / t_entry * t_amount
                                week_pnl += t_pnl
                            exec_detail_idx = 0
                            unwind_label = 'SL UNWIND' if evt == 'SL' else 'PT UNWIND'
                            for td in tranche_details:
                                if td['action'] == 'EXECUTE':
                                    t_entry_price = executed_tranches[exec_detail_idx][0]
                                    t_amount = executed_tranches[exec_detail_idx][1]
                                    td['pnl'] = round((evt_bid - t_entry_price) / t_entry_price * t_amount, 2)
                                    td['action'] = f'EXECUTE → {unwind_label}'
                                    exec_detail_idx += 1
                            if evt == 'SL':
                                stop_loss_triggered = True
                                stop_loss_info = {
                                    'triggered': True,
                                    'unwind_time': str(evt_time),
                                    'unwind_bid': round(evt_bid, 5),
                                    'avg_entry': round(avg_entry, 5),
                                    'loss_bps': round((avg_entry - evt_bid) / avg_entry * 10000, 2),
                                    'threshold_bps': stop_loss_bps,
                                }
                            else:
                                profit_taking_triggered = True
                                profit_taking_info = {
                                    'triggered': True,
                                    'unwind_time': str(evt_time),
                                    'unwind_bid': round(evt_bid, 5),
                                    'avg_entry': round(avg_entry, 5),
                                    'gain_bps': round((evt_bid - avg_entry) / avg_entry * 10000, 2),
                                    'threshold_bps': profit_taking_bps,
                                }

            # Unexecuted remainder is forfeited — no hindsight reallocation
            unexecuted_weight = accumulated_weight
            # Weighted average entry price across all executed tranches
            avg_entry = weighted_entry_sum / total_exec_amount if total_exec_amount > 0 else self._entry[i]

            detail_entry = {
                'year_week': w,
                'n_signals': n_slots,
                'tranches': tranche_details,
                'total_executed_weight': round(total_executed, 4),
                'unexecuted_weight': round(unexecuted_weight, 4),
                'unexecuted_amount': round(unexecuted_weight * weekly_notional, 0),
            }
            if stop_loss_info:
                detail_entry['stop_loss'] = stop_loss_info
            if profit_taking_info:
                detail_entry['profit_taking'] = profit_taking_info
            all_tranche_details.append(detail_entry)

            row = self.weekly_signals.iloc[i]
            n_executed = sum(1 for td in tranche_details if 'EXECUTE' in td['action'])
            # Determine actual exit price: SL or PT unwind bid, or normal exit
            if stop_loss_info:
                actual_exit = stop_loss_info['unwind_bid']
            elif profit_taking_info:
                actual_exit = profit_taking_info['unwind_bid']
            else:
                actual_exit = exit_price
            return_pct = round(float(week_pnl / total_exec_amount * 100), 4) if total_exec_amount > 0 else 0.0
            trade_row = {
                'year_week': w,
                'predict_time': str(row['predict_time']),
                'prediction': round(float(self._preds[i]), 4),
                'confidence': round(float(self._confs[i]), 4),
                'direction': 'BULLISH' if self._preds[i] >= 0.5 else 'BEARISH',
                'should_buy': total_executed > 0,
                'entry_price': round(float(avg_entry), 5) if not np.isnan(avg_entry) else 0,
                'exit_price': round(float(actual_exit), 5),
                'pips': round(float((actual_exit - avg_entry) * 10000), 1) if not np.isnan(avg_entry) else 0,
                'pnl': round(float(week_pnl), 2),
                'return_pct': return_pct,
                'executed_pct': round(total_executed * 100, 1),
                'executed_amount': round(total_exec_amount, 0),
                'n_executed': n_executed,
                'n_signals': n_slots,
                'stop_loss_triggered': stop_loss_triggered,
                'profit_taking_triggered': profit_taking_triggered,
            }
            if stop_loss_info:
                trade_row['stop_loss'] = stop_loss_info
            if profit_taking_info:
                trade_row['profit_taking'] = profit_taking_info
            trades.append(trade_row)

        # Cumulative metrics
        pnl_arr = np.array([t['pnl'] for t in trades])
        cum_pnl = np.cumsum(pnl_arr)
        running_max = np.maximum.accumulate(cum_pnl)
        drawdown = cum_pnl - running_max

        for idx, t in enumerate(trades):
            t['cum_pnl'] = round(float(cum_pnl[idx]), 2)
            t['drawdown'] = round(float(drawdown[idx]), 2)

        # Use should_buy flag instead of pnl!=0 to count traded weeks
        # (a week with executions but PnL=0 should still count as traded)
        n_traded_weeks = sum(1 for t in trades if t['should_buy'])
        total_pnl = float(pnl_arr.sum())
        traded_pnls = np.array([t['pnl'] for t in trades if t['should_buy']])
        wins = traded_pnls[traded_pnls > 0] if len(traded_pnls) > 0 else np.array([])
        losses = traded_pnls[traded_pnls < 0] if len(traded_pnls) > 0 else np.array([])
        std = pnl_arr.std()

        avg_exec_pct = np.mean([t['executed_pct'] for t in trades if t['should_buy']]) if n_traded_weeks > 0 else 0
        avg_n_exec = np.mean([t['n_executed'] for t in trades if t['should_buy']]) if n_traded_weeks > 0 else 0
        n_stop_losses = sum(1 for t in trades if t.get('stop_loss_triggered', False))
        n_profit_takings = sum(1 for t in trades if t.get('profit_taking_triggered', False))

        metrics = {
            'total_pnl': round(total_pnl, 2),
            'num_trades': n_traded_weeks,
            'num_weeks': len(self._weeks),
            'trade_freq': round(n_traded_weeks / len(self._weeks), 4) if len(self._weeks) > 0 else 0,
            'win_rate': round(float(len(wins) / n_traded_weeks), 4) if n_traded_weeks > 0 else 0,
            'avg_pnl_trade': round(total_pnl / n_traded_weeks, 2) if n_traded_weeks > 0 else 0,
            'avg_pnl_week': round(total_pnl / len(self._weeks), 2),
            'sharpe': round(float((pnl_arr.mean() / std) * np.sqrt(52)), 4) if std > 0 else 0,
            'max_drawdown': round(float(drawdown.min()), 2),
            'profit_factor': round(float(wins.sum() / abs(losses.sum())), 4) if len(losses) > 0 and losses.sum() != 0 else 9999.0,
            'avg_win': round(float(wins.mean()), 2) if len(wins) > 0 else 0,
            'avg_loss': round(float(losses.mean()), 2) if len(losses) > 0 else 0,
            'max_win': round(float(wins.max()), 2) if len(wins) > 0 else 0,
            'max_loss': round(float(losses.min()), 2) if len(losses) > 0 else 0,
            'avg_executed_pct': round(float(avg_exec_pct), 1),
            'avg_signals_executed_per_week': round(float(avg_n_exec), 1),
            'execution_mode': 'tranche',
            'stop_loss_bps': stop_loss_bps,
            'n_stop_losses': n_stop_losses,
            'stop_loss_rate': round(n_stop_losses / n_traded_weeks, 4) if n_traded_weeks > 0 else 0,
            'profit_taking_bps': profit_taking_bps,
            'n_profit_takings': n_profit_takings,
            'profit_taking_rate': round(n_profit_takings / n_traded_weeks, 4) if n_traded_weeks > 0 else 0,
        }

        return {
            'trades': trades,
            'tranche_details': all_tranche_details,
            'metrics': metrics,
            'params': {
                'pred_threshold': pred_th,
                'conf_threshold': conf_th,
                'execution_mode': 'tranche',
                'weighting': 'fixed_size' if (tranche_size is not None and tranche_size > 0) else 'equal',
                'tranche_size': tranche_size,
                'trade_size': self.trade_size,
                'stop_loss_bps': stop_loss_bps,
                'profit_taking_bps': profit_taking_bps,
            },
        }

    def _make_no_trade_row(self, i, w, mode='single'):
        """Helper to create a no-trade row."""
        row = self.weekly_signals.iloc[i]
        base = {
            'year_week': w,
            'predict_time': str(row['predict_time']),
            'prediction': round(float(self._preds[i]), 4),
            'confidence': round(float(self._confs[i]), 4),
            'direction': 'BULLISH' if self._preds[i] >= 0.5 else 'BEARISH',
            'should_buy': False,
            'entry_price': None,
            'exit_price': None,
            'pips': 0,
            'pnl': 0.0,
            'return_pct': 0.0,
            'cum_pnl': 0.0,
            'drawdown': 0.0,
        }
        if mode == 'tranche':
            base.update({
                'executed_pct': 0.0,
                'executed_amount': 0.0,
                'n_executed': 0,
                'n_signals': 0,
            })
        return base

    def compute_oracle(self):
        """Compute 'God's eye view' oracle: optimal entry per week.
        
        For each week, look at ALL signal slots and pick the one that would
        yield the highest PnL if we invested the full trade_size at that
        slot's ASK entry price.
        
        Also computes a 'never trade' baseline (PnL=0 every week) and
        a 'worst slot' floor for context.
        
        Returns dict with per-week oracle data and cumulative metrics.
        """
        if not self.ready or self._weekly_all_signals is None:
            return None

        oracle_pnls = []       # best-slot PnL per week
        worst_pnls = []        # worst-slot PnL per week
        oracle_details = []    # per-week detail: best slot info

        for i, w in enumerate(self._weeks):
            exit_price = self._exit[i]
            if np.isnan(exit_price):
                oracle_pnls.append(0.0)
                worst_pnls.append(0.0)
                oracle_details.append({'year_week': w, 'best_slot': None, 'best_pnl': 0, 'worst_pnl': 0, 'n_slots': 0})
                continue

            week_sigs = self._weekly_all_signals.get(w)
            if week_sigs is None or len(week_sigs) == 0:
                oracle_pnls.append(0.0)
                worst_pnls.append(0.0)
                oracle_details.append({'year_week': w, 'best_slot': None, 'best_pnl': 0, 'worst_pnl': 0, 'n_slots': 0})
                continue

            n_sigs = len(week_sigs)
            slot_pnls = []
            slot_entries = []

            for si in range(n_sigs):
                sig_time = week_sigs.iloc[si]['predict_time']
                slot_entry = self._get_entry_price_at_time(sig_time, w)
                if np.isnan(slot_entry) or slot_entry == 0:
                    slot_pnls.append(np.nan)
                    slot_entries.append(np.nan)
                else:
                    pnl = (exit_price - slot_entry) / slot_entry * self.trade_size
                    slot_pnls.append(pnl)
                    slot_entries.append(slot_entry)

            valid_pnls = [p for p in slot_pnls if not np.isnan(p)]
            if valid_pnls:
                best_pnl = max(valid_pnls)
                worst_pnl = min(valid_pnls)
                best_idx = slot_pnls.index(best_pnl)

                # God's eye view: if all slots lose money, oracle chooses NOT to trade (PnL=0)
                if best_pnl <= 0:
                    oracle_pnls.append(0.0)
                    worst_pnls.append(worst_pnl)
                    oracle_details.append({
                        'year_week': w,
                        'best_slot': None,
                        'best_pnl': 0,
                        'worst_pnl': round(worst_pnl, 2),
                        'n_slots': n_sigs,
                        'exit_price': round(exit_price, 5),
                        'oracle_action': 'NO_TRADE (all slots negative)',
                    })
                else:
                    oracle_pnls.append(best_pnl)
                    worst_pnls.append(worst_pnl)
                    oracle_details.append({
                        'year_week': w,
                        'best_slot': best_idx + 1,
                        'best_time': str(week_sigs.iloc[best_idx]['predict_time']),
                        'best_entry': round(slot_entries[best_idx], 5),
                        'best_pnl': round(best_pnl, 2),
                        'worst_pnl': round(worst_pnl, 2),
                        'n_slots': n_sigs,
                        'exit_price': round(exit_price, 5),
                    })
            else:
                oracle_pnls.append(0.0)
                worst_pnls.append(0.0)
                oracle_details.append({'year_week': w, 'best_slot': None, 'best_pnl': 0, 'worst_pnl': 0, 'n_slots': n_sigs})

        oracle_arr = np.array(oracle_pnls)
        worst_arr = np.array(worst_pnls)
        oracle_cum = np.cumsum(oracle_arr).tolist()
        worst_cum = np.cumsum(worst_arr).tolist()

        # Oracle metrics
        oracle_total = float(oracle_arr.sum())
        oracle_std = oracle_arr.std()
        oracle_wins = oracle_arr[oracle_arr > 0]
        oracle_losses = oracle_arr[oracle_arr < 0]
        n_traded = int((oracle_arr != 0).sum())

        return {
            'weeks': self._weeks.tolist(),
            'oracle_pnl': [round(p, 2) for p in oracle_pnls],
            'oracle_cum_pnl': [round(c, 2) for c in oracle_cum],
            'worst_pnl': [round(p, 2) for p in worst_pnls],
            'worst_cum_pnl': [round(c, 2) for c in worst_cum],
            'details': oracle_details,
            'metrics': {
                'total_pnl': round(oracle_total, 2),
                'sharpe': round(float((oracle_arr.mean() / oracle_std) * np.sqrt(52)), 4) if oracle_std > 0 else 0,
                'num_trades': n_traded,
                'win_rate': round(float(len(oracle_wins) / n_traded), 4) if n_traded > 0 else 0,
                'max_drawdown': round(float((np.cumsum(oracle_arr) - np.maximum.accumulate(np.cumsum(oracle_arr))).min()), 2),
            },
        }

    def run_grid_tranche(self, pred_min=0.40, pred_max=0.85, pred_step=0.01,
                         conf_min=0.0, conf_max=1.0, conf_step=0.01,
                         min_trades=0, tranche_size=None, stop_loss_bps=None, profit_taking_bps=None):
        """Grid search for tranche execution mode (long-only, ASK price) + optional SL/PT.
        
        Each signal slot uses its OWN ASK entry price (looked up from intraday data).
        If tranche_size is set, each slot executes that fixed amount.
        Unexecuted remainder is forfeited (no hindsight reallocation).
        
        Stop loss: if avg weighted entry vs market bid breaches stop_loss_bps,
        unwind all executed tranches at that bid price and stop trading for the week.
        """
        if not self.ready or self._weekly_all_signals is None:
            return pd.DataFrame()

        pred_ths = np.round(np.arange(pred_min, pred_max + 0.001, pred_step), 2)
        conf_ths = np.round(np.arange(conf_min, conf_max + 0.001, conf_step), 2)

        # Pre-compute per-week data: per-slot entry prices and pnl_per_unit
        week_data = []
        for wi, w in enumerate(self._weeks):
            exit_price = self._exit[wi]
            if np.isnan(exit_price):
                week_data.append(None)
                continue

            week_sigs = self._weekly_all_signals.get(w)
            if week_sigs is None or len(week_sigs) == 0:
                week_data.append(None)
                continue

            n_sigs = len(week_sigs)
            use_fixed = tranche_size is not None and tranche_size > 0
            if use_fixed:
                base_w = 1.0 / n_sigs
                weekly_notional = tranche_size * n_sigs
            else:
                base_w = 1.0 / n_sigs
                weekly_notional = self.trade_size
            preds = week_sigs['prediction'].values.astype(float)
            confs = week_sigs['confidence'].values.astype(float)

            # Per-slot entry prices and pnl_per_unit (using ASK entry price)
            slot_entry_prices = np.zeros(n_sigs)
            slot_pnl_per_unit = np.zeros(n_sigs)
            slot_times = []
            for si in range(n_sigs):
                sig_time = week_sigs.iloc[si]['predict_time']
                slot_times.append(sig_time)
                slot_entry = self._get_entry_price_at_time(sig_time, w)
                slot_entry_prices[si] = slot_entry
                if np.isnan(slot_entry) or slot_entry == 0:
                    slot_pnl_per_unit[si] = np.nan  # mark as invalid
                else:
                    slot_pnl_per_unit[si] = (exit_price - slot_entry) / slot_entry

            # Compute exit datetime for stop loss monitoring
            last_sig_time = week_sigs.iloc[-1]['predict_time']
            if last_sig_time.weekday() == 4:
                exit_dt = (last_sig_time + pd.Timedelta(days=1)).normalize() + pd.Timedelta(hours=2)
            else:
                exit_dt = last_sig_time.normalize() + pd.Timedelta(hours=2)

            week_data.append({
                'preds': preds,
                'confs': confs,
                'base_w': base_w,
                'n_sigs': n_sigs,
                'slot_entry_prices': slot_entry_prices,
                'slot_pnl_per_unit': slot_pnl_per_unit,
                'weekly_notional': weekly_notional,
                'slot_times': slot_times,
                'exit_price': exit_price,
                'exit_datetime': exit_dt,
            })

        n_weeks = len(self._weeks)
        use_sl = stop_loss_bps is not None and stop_loss_bps > 0
        use_pt = profit_taking_bps is not None and profit_taking_bps > 0
        use_slpt = use_sl or use_pt

        if use_slpt:
            self.ensure_intraday_loaded()

        results = []
        for pt in pred_ths:
            for ct in conf_ths:
                pnl_arr = np.zeros(n_weeks)
                total_exec_pcts = []
                had_exec = np.zeros(n_weeks, dtype=bool)
                n_sl = 0
                n_pt = 0

                for wi in range(n_weeks):
                    wd = week_data[wi]
                    if wd is None:
                        continue

                    accumulated = 0.0
                    week_pnl = 0.0
                    total_exec = 0.0
                    base_w = wd['base_w']
                    wk_notional = wd['weekly_notional']
                    preds = wd['preds']
                    confs = wd['confs']
                    slot_ppu = wd['slot_pnl_per_unit']
                    early_stopped = False

                    exec_entries = []
                    weighted_entry_sum = 0.0
                    total_exec_amount = 0.0

                    for si in range(wd['n_sigs']):
                        if early_stopped:
                            break

                        available = accumulated + base_w

                        if preds[si] >= pt and confs[si] > ct and not np.isnan(slot_ppu[si]):
                            exec_amount = available * wk_notional
                            entry_price = wd['slot_entry_prices'][si]
                            exec_entries.append((entry_price, exec_amount))
                            total_exec += available
                            total_exec_amount += exec_amount
                            weighted_entry_sum += entry_price * exec_amount
                            week_pnl += slot_ppu[si] * exec_amount
                            accumulated = 0.0

                            if use_slpt and total_exec_amount > 0:
                                avg_entry = weighted_entry_sum / total_exec_amount
                                monitor_start = wd['slot_times'][si]
                                monitor_end = wd['slot_times'][si + 1] if si + 1 < wd['n_sigs'] else wd['exit_datetime']
                                evt, _, evt_bid = self._check_sl_pt(
                                    avg_entry, monitor_start, monitor_end, stop_loss_bps, profit_taking_bps
                                )
                                if evt is not None:
                                    early_stopped = True
                                    if evt == 'SL':
                                        n_sl += 1
                                    else:
                                        n_pt += 1
                                    week_pnl = sum(
                                        (evt_bid - ep) / ep * ea for ep, ea in exec_entries
                                    )
                        else:
                            accumulated = available
                            if use_slpt and total_exec_amount > 0:
                                avg_entry = weighted_entry_sum / total_exec_amount
                                monitor_start = wd['slot_times'][si]
                                monitor_end = wd['slot_times'][si + 1] if si + 1 < wd['n_sigs'] else wd['exit_datetime']
                                evt, _, evt_bid = self._check_sl_pt(
                                    avg_entry, monitor_start, monitor_end, stop_loss_bps, profit_taking_bps
                                )
                                if evt is not None:
                                    early_stopped = True
                                    if evt == 'SL':
                                        n_sl += 1
                                    else:
                                        n_pt += 1
                                    week_pnl = sum(
                                        (evt_bid - ep) / ep * ea for ep, ea in exec_entries
                                    )

                    pnl_arr[wi] = week_pnl
                    if total_exec > 0:
                        had_exec[wi] = True
                        total_exec_pcts.append(round(total_exec * 100, 1))

                n_trades = int(had_exec.sum())
                total_pnl = float(pnl_arr.sum())
                avg_exec_pct = float(np.mean(total_exec_pcts)) if total_exec_pcts else 0.0

                if n_trades == 0:
                    results.append([float(pt), float(ct), 0, 0, 0, 0, 0, 0, 0, 0, 0])
                    continue

                trade_pnls = pnl_arr[had_exec]
                w_arr = trade_pnls[trade_pnls > 0]
                l_arr = trade_pnls[trade_pnls < 0]
                std_val = pnl_arr.std()
                sharpe = float((pnl_arr.mean() / std_val) * np.sqrt(52)) if std_val > 0 else 0
                cum = np.cumsum(pnl_arr)
                max_dd = float((cum - np.maximum.accumulate(cum)).min())
                wr = float(len(w_arr) / n_trades) if n_trades > 0 else 0
                pf = float(w_arr.sum() / abs(l_arr.sum())) if len(l_arr) > 0 and l_arr.sum() != 0 else 9999.0

                results.append([
                    float(pt), float(ct), round(total_pnl, 2),
                    n_trades, round(sharpe, 4), round(max_dd, 2),
                    round(wr, 4), round(pf, 4), round(avg_exec_pct, 1),
                    n_sl, n_pt
                ])

        cols = ['pred_threshold', 'conf_threshold', 'total_pnl',
                'num_trades', 'sharpe', 'max_drawdown', 'win_rate',
                'profit_factor', 'avg_exec_pct', 'n_stop_losses', 'n_profit_takings']
        df = pd.DataFrame(results, columns=cols)
        self.grid_results = df
        return df

    def run_grid(self, pred_min=0.40, pred_max=0.85, pred_step=0.01,
                 conf_min=0.0, conf_max=1.0, conf_step=0.01, min_trades=0):
        if not self.ready:
            return pd.DataFrame()

        pred_ths = np.round(np.arange(pred_min, pred_max + 0.001, pred_step), 2)
        conf_ths = np.round(np.arange(conf_min, conf_max + 0.001, conf_step), 2)

        results = []
        for pt in pred_ths:
            for ct in conf_ths:
                mask = (self._preds >= pt) & (self._confs > ct)
                pnl_arr = np.where(mask, self._pnl_if_trade, 0.0)
                n_trades = int(mask.sum())
                total_pnl = float(pnl_arr.sum())

                if n_trades == 0:
                    results.append([float(pt), float(ct), 0, 0, 0, 0, 0, 0])
                    continue

                trade_pnls = pnl_arr[mask]
                wins = trade_pnls[trade_pnls > 0]
                losses = trade_pnls[trade_pnls < 0]
                std = pnl_arr.std()
                sharpe = float((pnl_arr.mean() / std) * np.sqrt(52)) if std > 0 else 0
                cum = np.cumsum(pnl_arr)
                max_dd = float((cum - np.maximum.accumulate(cum)).min())
                wr = float(len(wins) / n_trades) if n_trades > 0 else 0
                pf = float(wins.sum() / abs(losses.sum())) if len(losses) > 0 and losses.sum() != 0 else 9999.0

                results.append([float(pt), float(ct), round(total_pnl, 2),
                                n_trades, round(sharpe, 4), round(max_dd, 2),
                                round(wr, 4), round(pf, 4)])

        cols = ['pred_threshold', 'conf_threshold', 'total_pnl',
                'num_trades', 'sharpe', 'max_drawdown', 'win_rate', 'profit_factor']
        df = pd.DataFrame(results, columns=cols)
        self.grid_results = df
        return df

    def get_heatmap_data(self, metric='total_pnl'):
        if self.grid_results is None:
            return None

        df = self.grid_results.copy()
        df['pred_threshold'] = df['pred_threshold'].round(2)
        df['conf_threshold'] = df['conf_threshold'].round(2)

        if len(df) == 0:
            return None

        pivot = df.pivot_table(
            index='pred_threshold', columns='conf_threshold',
            values=metric, aggfunc='first'
        )

        return {
            'x': [round(float(c), 2) for c in pivot.columns.tolist()],
            'y': [round(float(r), 2) for r in pivot.index.tolist()],
            'z': [[None if pd.isna(v) else round(float(v), 2) for v in row]
                  for row in pivot.values.tolist()],
            'metric': metric,
        }


def list_data_files(directories, pattern='*.csv'):
    """List available data files from one or more directories."""
    if isinstance(directories, str):
        directories = [directories]
    files = []
    for directory in directories:
        search_dir = BASE_DIR / directory
        if not search_dir.exists():
            continue
        for f in sorted(search_dir.glob(pattern)):
            size = f.stat().st_size
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024*1024):.1f} MB"
            files.append({
                'name': f.name,
                'path': str(f.relative_to(BASE_DIR)).replace('\\', '/'),
                'folder': directory,
                'size': size_str,
                'full_path': str(f),
            })
    return files


def create_app():
    config = load_config()
    app = Flask(__name__,
                template_folder=str(DASHBOARD_DIR),
                static_folder=str(DASHBOARD_DIR / 'static'))
    CORS(app)

    engine = BacktestEngine(config)

    # ============ Page ============
    @app.route('/')
    def index():
        return render_template('index.html')

    # ============ Config ============
    @app.route('/api/config')
    def get_config():
        return jsonify({'success': True, 'data': config})

    @app.route('/api/config', methods=['POST'])
    def update_config():
        new_conf = request.json
        for key in ['signal', 'trading', 'grid_search']:
            if key in new_conf:
                config[key] = new_conf[key]
        config_path = DASHBOARD_DIR / 'config.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        return jsonify({'success': True})

    # ============ Status ============
    @app.route('/api/status')
    def status():
        return jsonify({
            'success': True,
            'data': {
                'signals_loaded': engine.signals_loaded,
                'prices_loaded': engine.prices_loaded,
                'intraday_loaded': engine.intraday_loaded,
                'ready': engine.ready,
                'valid_weeks': len(engine.valid_weeks),
                'grid_computed': engine.grid_results is not None,
                'grid_rows': len(engine.grid_results) if engine.grid_results is not None else 0,
            }
        })

    # ============ Step 1: List & Load Signals ============
    @app.route('/api/files/signals')
    def list_signal_files():
        files = list_data_files(['data/signals', 'data/raw'], '*.csv')
        return jsonify({'success': True, 'data': files})

    @app.route('/api/load/signals', methods=['POST'])
    def load_signals():
        params = request.json or {}
        file_path = params.get('file_path')
        if not file_path:
            return jsonify({'success': False, 'error': 'file_path required'}), 400
        try:
            summary = engine.load_signals(file_path)
            return jsonify({'success': True, 'data': summary})
        except Exception as e:
            import traceback
            return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 400

    @app.route('/api/process/signals', methods=['POST'])
    def process_signals():
        """Process a raw signal CSV: add confidence, direction, year_week columns."""
        params = request.json or {}
        file_path = params.get('file_path')
        if not file_path:
            return jsonify({'success': False, 'error': 'file_path required'}), 400
        try:
            result = engine.process_raw_signals(file_path)
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            import traceback
            return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 400

    @app.route('/api/validate/signals')
    def validate_signals():
        """Validate loaded signal data."""
        try:
            report = engine.validate_signals()
            return jsonify({'success': True, 'data': report})
        except Exception as e:
            import traceback
            return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 400

    @app.route('/api/llm/analyze', methods=['POST'])
    def llm_analyze():
        """Stream LLM analysis of signal data (SSE)."""
        if not engine.signals_loaded:
            return jsonify({'success': False, 'error': 'Load signals first'}), 400

        # Optionally include validation report
        validation_report = None
        try:
            validation_report = engine.validate_signals()
        except Exception:
            pass

        def generate():
            for chunk in engine.llm_analyze_signals(config, validation_report):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"

        return Response(generate(), mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    @app.route('/api/llm/config')
    def get_llm_config():
        """Return LLM config (without API key for security)."""
        llm_cfg = config.get('llm', {})
        return jsonify({'success': True, 'data': {
            'enabled': llm_cfg.get('enabled', False),
            'base_url': llm_cfg.get('base_url', ''),
            'model': llm_cfg.get('model', ''),
            'has_api_key': bool(llm_cfg.get('api_key', '')) and llm_cfg.get('api_key') != 'YOUR_API_KEY_HERE',
        }})

    @app.route('/api/llm/config', methods=['POST'])
    def update_llm_config():
        """Update LLM config and save to yaml."""
        new_llm = request.json or {}
        if 'llm' not in config:
            config['llm'] = {}
        for key in ['enabled', 'api_key', 'base_url', 'model', 'temperature', 'top_p', 'max_tokens', 'timeout']:
            if key in new_llm:
                config['llm'][key] = new_llm[key]
        config_path = DASHBOARD_DIR / 'config.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        return jsonify({'success': True})

    # ============ Step 2: List & Load Prices ============
    @app.route('/api/files/prices')
    def list_price_files():
        files = list_data_files(['data/market', 'data/raw'], '*.csv')
        return jsonify({'success': True, 'data': files})

    @app.route('/api/files/bbg_ticks')
    def list_bbg_tick_files():
        """List BBG second-level bid/ask Excel files."""
        files = list_data_files(['data/market/bbg_ticks'], '*.xlsx')
        # Also scan data/raw but only include files with 'bidask' in name
        raw_files = list_data_files(['data/raw'], '*.xlsx')
        files.extend([f for f in raw_files if 'bidask' in f['name'].lower()])
        return jsonify({'success': True, 'data': files})

    @app.route('/api/load/prices', methods=['POST'])
    def load_prices():
        params = request.json or {}
        file_path = params.get('file_path')
        if not file_path:
            return jsonify({'success': False, 'error': 'file_path required'}), 400
        try:
            summary = engine.load_prices(file_path)
            return jsonify({'success': True, 'data': summary})
        except Exception as e:
            import traceback
            return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 400

    @app.route('/api/load/bbg_ticks', methods=['POST'])
    def load_bbg_ticks():
        """Load BBG second-level tick data and extract entry/exit prices."""
        params = request.json or {}
        file_path = params.get('file_path')
        if not file_path:
            return jsonify({'success': False, 'error': 'file_path required'}), 400
        try:
            entry_offset = int(params.get('entry_offset_minutes', 0))
            exit_hour = int(params.get('exit_hour', 2))
            exit_minute = int(params.get('exit_minute', 0))
            summary = engine.load_bbg_ticks(
                file_path,
                entry_offset_minutes=entry_offset,
                exit_hour=exit_hour,
                exit_minute=exit_minute,
            )
            return jsonify({'success': True, 'data': summary})
        except Exception as e:
            import traceback
            return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 400

    @app.route('/api/files/intraday')
    def list_intraday_files():
        """List intraday OHLCV CSV/Excel files."""
        csv_files = list_data_files(['data/market', 'data/market/bbg_intraday', 'data/raw'], '*.csv')
        xlsx_files = list_data_files(['data/market'], '*.xlsx')
        all_files = csv_files + xlsx_files
        return jsonify({'success': True, 'data': all_files})

    @app.route('/api/load/intraday', methods=['POST'])
    def load_intraday():
        """Load minute-level intraday data and extract entry/exit prices."""
        params = request.json or {}
        file_path = params.get('file_path')
        if not file_path:
            return jsonify({'success': False, 'error': 'file_path required'}), 400
        try:
            exit_hour = int(params.get('exit_hour', 2))
            exit_minute = int(params.get('exit_minute', 0))
            summary = engine.load_intraday(
                file_path,
                exit_hour=exit_hour,
                exit_minute=exit_minute,
            )
            return jsonify({'success': True, 'data': summary})
        except Exception as e:
            import traceback
            return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 400

    @app.route('/api/price_chart')
    def price_chart():
        """Get loaded price data for visualisation."""
        data = engine.get_price_chart_data()
        if data is None:
            return jsonify({'success': False, 'error': 'No price data loaded'}), 400
        return jsonify({'success': True, 'data': data})

    # ============ Step 2b: BBG Download (Raw Intraday Data) ============
    # Downloads full intraday bid/ask bars per week — NO signal-based filtering.
    # Preprocessing (entry/exit extraction) happens later in the engine.
    # Shared state for async download progress
    bbg_download_state = {
        'status': 'idle',  # idle | connecting | downloading | done | error
        'progress': 0,
        'total': 0,
        'current_week': '',
        'message': '',
        'error': None,
        'output_file': None,
        'latest_file': None,
        'timestamp': None,
        'total_bars': 0,
    }

    @app.route('/api/bbg/status')
    def bbg_status():
        """Check if Bloomberg is available and Terminal is connected."""
        bbg_connected = False
        bbg_message = ''
        
        if not HAS_BBG:
            bbg_message = 'blpapi module not installed'
        else:
            # 真正尝试连接Bloomberg Terminal
            try:
                from quant_system.tools.bbg_wrapper import BloombergWrapper
                _test = BloombergWrapper()
                if _test.connect():
                    bbg_connected = True
                    bbg_message = 'Bloomberg Terminal connected'
                    _test.disconnect()
                else:
                    bbg_message = 'Bloomberg Terminal not running or not logged in'
            except Exception as e:
                bbg_message = f'Connection check failed: {str(e)}'
        
        return jsonify({
            'success': True,
            'data': {
                'has_bbg': HAS_BBG,
                'bbg_connected': bbg_connected,
                'bbg_message': bbg_message,
                'download_state': bbg_download_state,
            }
        })

    @app.route('/api/bbg/download', methods=['POST'])
    def bbg_download():
        """Start BBG raw intraday data download in background thread.

        Downloads FULL bid/ask bar data for each signal week's trading window
        (Fri 20:00 ~ Sat 05:00 Beijing time). No signal-based filtering —
        raw market data only. The engine will handle preprocessing later.
        """
        if not HAS_BBG:
            return jsonify({'success': False, 'error': 'Bloomberg (blpapi) not available. Please install blpapi and ensure Bloomberg Terminal is running.'}), 400
        
        # 前置检查: 尝试连接Bloomberg，验证Terminal是否在运行
        try:
            from quant_system.tools.bbg_wrapper import BloombergWrapper
            _test_bbg = BloombergWrapper()
            if not _test_bbg.connect():
                return jsonify({'success': False, 'error': 'Bloomberg Terminal未连接。请确认: 1) Bloomberg Terminal已启动 2) 已登录BBG账号 3) API服务(端口8194)正在运行'}), 400
            _test_bbg.disconnect()
        except Exception as e:
            return jsonify({'success': False, 'error': f'Bloomberg连接检查失败: {str(e)}'}), 400
        
        if not engine.signals_loaded:
            return jsonify({'success': False, 'error': 'Load signals first (Step 1)'}), 400
        if bbg_download_state['status'] in ('connecting', 'downloading'):
            return jsonify({'success': False, 'error': 'Download already in progress'}), 400

        params = request.json or {}
        ticker = params.get('ticker', 'USDCNH Curncy')
        frequency = params.get('frequency', '1m')
        force_refetch = params.get('force_refetch', False)

        # Output dir
        output_dir = BASE_DIR / 'data' / 'market' / 'bbg_intraday'
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = _time.strftime('%Y%m%d_%H%M%S')
        latest_file = str(BASE_DIR / 'data' / 'market' / 'bbg_intraday_latest.csv')

        def download_worker():
            try:
                bbg_download_state.update({
                    'status': 'connecting', 'progress': 0, 'total': 0,
                    'current_week': '', 'message': 'Connecting to Bloomberg...', 'error': None,
                    'output_file': None, 'latest_file': None, 'timestamp': None, 'total_bars': 0,
                })

                from quant_system.tools.bbg_wrapper import BloombergWrapper
                bbg = BloombergWrapper()
                bbg.connect()

                bbg_download_state['status'] = 'downloading'
                bbg_download_state['message'] = 'Identifying trading weeks from signals...'

                # Determine weeks from signals (only dates, no price extraction)
                signal_df = engine.signals.copy()
                fetcher = WeekendPriceDataFetcher()
                fetcher._connected = True  # skip connect, we use bbg directly
                fetcher.bbg = bbg
                weekends = fetcher._get_weekend_dates_from_signals(signal_df)
                total_weeks = len(weekends)
                bbg_download_state['total'] = total_weeks

                # Check which weeks are already cached
                cached_weeks = set()
                if not force_refetch:
                    for f in output_dir.glob('*.csv'):
                        # filenames like USDCNH_2025_20.csv
                        name = f.stem
                        parts = name.split('_', 1)
                        if len(parts) == 2:
                            cached_weeks.add(parts[1])
                    if cached_weeks:
                        bbg_download_state['message'] = f'Found {len(cached_weeks)} cached weeks on disk'

                all_bars = []
                total_bar_count = 0

                for i, weekend in enumerate(weekends):
                    year_week = weekend['year_week']
                    saturday_date = pd.to_datetime(weekend['saturday_date'])
                    friday_date = pd.to_datetime(weekend['friday_date'])

                    bbg_download_state['progress'] = i + 1
                    bbg_download_state['current_week'] = year_week
                    bbg_download_state['message'] = f'Downloading {year_week} ({i+1}/{total_weeks})'

                    week_file = output_dir / f'{ticker.replace(" ", "_")}_{year_week}.csv'
                    safe_yw = year_week  # e.g. "2025_20"

                    # Skip if cached
                    if safe_yw in cached_weeks and week_file.exists() and not force_refetch:
                        try:
                            cached_df = pd.read_csv(week_file)
                            cached_df['timestamp'] = pd.to_datetime(cached_df['timestamp'])
                            all_bars.append(cached_df)
                            total_bar_count += len(cached_df)
                            bbg_download_state['total_bars'] = total_bar_count
                            continue
                        except Exception:
                            pass  # re-download if cache is corrupt

                    # Download full window: Fri 20:00 → Sat 05:00 Beijing time
                    window_start = friday_date.replace(hour=20, minute=0, second=0)
                    window_end = saturday_date.replace(hour=5, minute=0, second=0)

                    try:
                        df = bbg.get_bid_ask_bars(
                            symbol=ticker,
                            start_date=window_start,
                            end_date=window_end,
                            resample=frequency,
                            is_beijing_time=True,
                        )

                        if df is not None and not df.empty:
                            # Convert UTC index → Beijing time column
                            df = df.reset_index()
                            df.rename(columns={'timestamp': 'timestamp_utc'}, inplace=True)
                            df['timestamp'] = df['timestamp_utc'] + pd.Timedelta(hours=8)
                            df['year_week'] = year_week
                            df['friday_date'] = weekend['friday_date']
                            df['saturday_date'] = weekend['saturday_date']

                            # Keep relevant columns
                            cols_to_keep = ['timestamp', 'bid', 'ask', 'mid', 'spread', 'year_week', 'friday_date', 'saturday_date']
                            cols_to_keep = [c for c in cols_to_keep if c in df.columns]
                            week_df = df[cols_to_keep].copy()

                            # Save per-week file
                            week_df.to_csv(week_file, index=False)

                            all_bars.append(week_df)
                            total_bar_count += len(week_df)
                            bbg_download_state['total_bars'] = total_bar_count
                        else:
                            print(f"  [BBG] No data for {year_week}")
                    except Exception as e:
                        print(f"  [BBG] Error fetching {year_week}: {e}")

                bbg.disconnect()

                if not all_bars:
                    raise ValueError("No intraday data downloaded from Bloomberg for any week")

                # Concatenate all weeks into one master file
                combined = pd.concat(all_bars, ignore_index=True)
                combined = combined.sort_values('timestamp').reset_index(drop=True)

                # Save timestamped + latest
                timestamped_file = str(BASE_DIR / 'data' / 'market' / f'bbg_intraday_{timestamp_str}.csv')
                combined.to_csv(timestamped_file, index=False)
                combined.to_csv(latest_file, index=False)

                bbg_download_state.update({
                    'status': 'done',
                    'message': f'Done! {total_bar_count} bars across {total_weeks} weeks downloaded',
                    'output_file': timestamped_file,
                    'latest_file': latest_file,
                    'timestamp': timestamp_str,
                    'total_bars': total_bar_count,
                })

            except Exception as e:
                import traceback
                bbg_download_state.update({
                    'status': 'error',
                    'message': str(e),
                    'error': traceback.format_exc(),
                })

        thread = threading.Thread(target=download_worker, daemon=True)
        thread.start()

        return jsonify({'success': True, 'message': 'Download started'})

    @app.route('/api/bbg/download/status')
    def bbg_download_status():
        """Poll download progress."""
        result = dict(bbg_download_state)
        return jsonify({'success': True, 'data': result})

    @app.route('/api/export/config', methods=['POST'])
    def export_download_config():
        """Export market data download config as JSON file."""
        params = request.json or {}
        config_data = {
            'ticker': params.get('ticker', 'USDCNH Curncy'),
            'frequency': params.get('frequency', '1m'),
            'start_date': params.get('start_date', ''),
            'end_date': params.get('end_date', ''),
            'exit_hour': int(params.get('exit_hour', 2)),
            'exit_minute': int(params.get('exit_minute', 0)),
            'time_window': 'Fri 20:00 ~ Sat 05:00 (Beijing)',
            'weeks': [],
        }
        mc = engine._derive_market_config() if engine.signals_loaded else None
        if mc:
            config_data['weeks'] = mc.get('weeks', [])
            config_data['pair'] = mc.get('pair', '')
            config_data['total_weeks'] = mc.get('total_weeks', 0)

        json_str = json.dumps(config_data, indent=2, ensure_ascii=False)
        return Response(
            json_str,
            mimetype='application/json',
            headers={'Content-Disposition': 'attachment; filename=bbg_download_config.json'}
        )

    @app.route('/api/export/script', methods=['POST'])
    def export_download_script():
        """Generate a Python script for BBG data download."""
        params = request.json or {}
        ticker = params.get('ticker', 'USDCNH Curncy')
        freq = params.get('frequency', '1m')
        start_date = params.get('start_date', '')
        end_date = params.get('end_date', '')
        exit_hour = int(params.get('exit_hour', 2))
        exit_minute = int(params.get('exit_minute', 0))

        mc = engine._derive_market_config() if engine.signals_loaded else None
        weeks_str = str(mc.get('weeks', [])) if mc else '[]'

        script = f'''# -*- coding: utf-8 -*-
"""
BBG Weekend Price Download Script (Auto-generated)
====================================================
Generated from Dashboard config.
Run this script with Bloomberg Terminal running.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from weekend_price_fetcher import WeekendPriceDataFetcher
import pandas as pd

# ============ Configuration ============
TICKER = "{ticker}"
FREQUENCY = "{freq}"
START_DATE = "{start_date}"
END_DATE = "{end_date}"
EXIT_HOUR = {exit_hour}
EXIT_MINUTE = {exit_minute}
SIGNAL_WEEKS = {weeks_str}

# ============ Download ============
def main():
    # Load signal file (update path as needed)
    signal_df = pd.read_csv("data/signals/USD_SIGNAL_V3_processed.csv")
    signal_df["predict_time"] = pd.to_datetime(signal_df["predict_time"])

    fetcher = WeekendPriceDataFetcher()
    fetcher.connect()

    prices = fetcher.fetch_all_weekend_prices(
        symbol=TICKER,
        signal_df=signal_df,
    )

    output_path = "data/market/weekend_prices_bbg.csv"
    fetcher.save_prices(prices, output_path)
    print(f"Saved {{len(prices)}} weeks to {{output_path}}")

    fetcher.disconnect()

if __name__ == "__main__":
    main()
'''
        return Response(
            script,
            mimetype='text/x-python',
            headers={'Content-Disposition': 'attachment; filename=download_bbg_prices.py'}
        )

    @app.route('/api/market_config')
    def get_market_config():
        """Get current market data config derived from signals."""
        if not engine.signals_loaded:
            return jsonify({'success': False, 'error': 'Load signals first'}), 400
        mc = engine._derive_market_config()
        return jsonify({'success': True, 'data': mc})

    # ============ Step 3: Grid Search ============
    @app.route('/api/grid/run', methods=['POST'])
    def run_grid():
        if not engine.ready:
            return jsonify({'success': False, 'error': 'Load signals and prices first'}), 400
        params = request.json or {}
        gs = config.get('grid_search', {})
        pred_min = float(params.get('pred_min', gs.get('prediction_range', {}).get('min', 0.40)))
        pred_max = float(params.get('pred_max', gs.get('prediction_range', {}).get('max', 0.85)))
        pred_step = float(params.get('pred_step', gs.get('prediction_range', {}).get('step', 0.01)))
        conf_min = float(params.get('conf_min', gs.get('confidence_range', {}).get('min', 0.0)))
        conf_max = float(params.get('conf_max', gs.get('confidence_range', {}).get('max', 1.0)))
        conf_step = float(params.get('conf_step', gs.get('confidence_range', {}).get('step', 0.01)))
        min_trades = int(params.get('min_trades', gs.get('min_trades', 0)))

        # Allow user to override weekly trade size from the UI
        trade_size = params.get('trade_size')
        if trade_size is not None:
            trade_size = int(trade_size)
            engine.update_trade_size(trade_size)

        # Execution mode: 'single' (legacy) or 'tranche'
        exec_mode = params.get('execution_mode', 'single')

        # Tranche size: user-defined per-tranche amount (None = auto = trade_size / N)
        tranche_size_param = params.get('tranche_size')
        tranche_size = int(tranche_size_param) if tranche_size_param else None

        # Stop loss in basis points (None = disabled)
        sl_param = params.get('stop_loss_bps')
        stop_loss_bps = float(sl_param) if sl_param else None

        # Profit taking in basis points (None = disabled)
        pt_param = params.get('profit_taking_bps')
        profit_taking_bps = float(pt_param) if pt_param else None

        if exec_mode == 'tranche':
            try:
                df = engine.run_grid_tranche(
                    pred_min, pred_max, pred_step,
                    conf_min, conf_max, conf_step,
                    min_trades=min_trades,
                    tranche_size=tranche_size,
                    stop_loss_bps=stop_loss_bps,
                    profit_taking_bps=profit_taking_bps,
                )
            except ValueError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
        else:
            if stop_loss_bps is not None or profit_taking_bps is not None:
                return jsonify({
                    'success': False,
                    'error': 'Stop Loss / Profit Taking requires Tranche execution mode. '
                             'Please switch to Tranche mode to use SL/PT.'
                }), 400
            df = engine.run_grid(pred_min, pred_max, pred_step, conf_min, conf_max, conf_step, min_trades)

        # Summary
        valid = df[df['num_trades'] >= min_trades]
        top_sharpe = valid.nlargest(5, 'sharpe').to_dict('records') if len(valid) > 0 else []
        top_pnl = valid.nlargest(5, 'total_pnl').to_dict('records') if len(valid) > 0 else []

        result_data = {
            'total_combinations': len(df),
            'valid_combinations': len(valid),
            'top_sharpe': top_sharpe,
            'top_pnl': top_pnl,
            'execution_mode': exec_mode,
            'trade_size': engine.trade_size,
        }

        return jsonify({'success': True, 'data': result_data})

    @app.route('/api/grid/results')
    def grid_results():
        if engine.grid_results is None:
            return jsonify({'success': False, 'error': 'Run grid search first'}), 400

        sort_by = request.args.get('sort_by', 'sharpe')
        min_trades = int(request.args.get('min_trades', 0))
        top_n = int(request.args.get('top_n', 50))

        df = engine.grid_results.copy()
        df = df[df['num_trades'] >= min_trades]

        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=False)
        rows = df.head(top_n).to_dict('records')
        return jsonify({'success': True, 'data': rows, 'total': len(df)})

    # ============ Step 4: Compare Configurations ============
    @app.route('/api/backtest', methods=['POST'])
    def run_backtest():
        if not engine.ready:
            return jsonify({'success': False, 'error': 'Load signals and prices first'}), 400
        params = request.json or {}
        pred_th = float(params.get('pred_threshold', 0.5))
        conf_th = float(params.get('conf_threshold', 0.0))

        exec_mode = params.get('execution_mode', 'single')
        if exec_mode == 'tranche':
            ts_param = params.get('tranche_size')
            ts = int(ts_param) if ts_param else None
            sl_param = params.get('stop_loss_bps')
            sl = float(sl_param) if sl_param else None
            pt_param = params.get('profit_taking_bps')
            pt = float(pt_param) if pt_param else None
            try:
                result = engine.run_single_tranche(pred_th, conf_th, tranche_size=ts, stop_loss_bps=sl, profit_taking_bps=pt)
            except ValueError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
        else:
            result = engine.run_single(pred_th, conf_th)

        return jsonify({'success': True, 'data': result})

    @app.route('/api/compare', methods=['POST'])
    def compare_configs():
        """Compare multiple configurations side by side."""
        if not engine.ready:
            return jsonify({'success': False, 'error': 'Load signals and prices first'}), 400
        params = request.json or {}
        configs = params.get('configs', [])
        if not configs:
            return jsonify({'success': False, 'error': 'Provide configs array'}), 400

        results = []
        for cfg in configs:
            pred = float(cfg.get('pred_threshold', 0.5))
            conf = float(cfg.get('conf_threshold', 0.0))
            label = cfg.get('label', f"P={pred:.2f} C={conf:.2f}")

            exec_mode = cfg.get('execution_mode', 'single')
            if exec_mode == 'tranche':
                ts_param = cfg.get('tranche_size')
                ts = int(ts_param) if ts_param else None
                sl_param = cfg.get('stop_loss_bps')
                sl = float(sl_param) if sl_param else None
                pt_param = cfg.get('profit_taking_bps')
                pt_val = float(pt_param) if pt_param else None
                try:
                    r = engine.run_single_tranche(pred, conf, tranche_size=ts, stop_loss_bps=sl, profit_taking_bps=pt_val)
                except ValueError as e:
                    return jsonify({'success': False, 'error': str(e)}), 400
            else:
                r = engine.run_single(pred, conf)
            r['label'] = label
            results.append(r)

        # Attach oracle (God's eye view) data — computed once, shared across all configs
        oracle = engine.compute_oracle()

        return jsonify({'success': True, 'data': results, 'oracle': oracle})

    # ============ Heatmap ============
    @app.route('/api/heatmap')
    def heatmap():
        if engine.grid_results is None:
            return jsonify({'success': False, 'error': 'Run grid search first'}), 400
        metric = request.args.get('metric', 'total_pnl')
        data = engine.get_heatmap_data(metric=metric)
        if data is None:
            return jsonify({'success': False, 'error': 'No data for selected filters'}), 400
        return jsonify({'success': True, 'data': data})

    return app, config


def main():
    app, config = create_app()
    dash_conf = config.get('dashboard', {})
    host = dash_conf.get('host', '0.0.0.0')
    port = dash_conf.get('port', 8889)
    debug = dash_conf.get('debug', True)

    print(f"\n{'='*60}")
    print(f"Weekend Pre-Lock Backtest Dashboard (v2 Wizard)")
    print(f"{'='*60}")
    print(f"  http://localhost:{port}")
    print(f"{'='*60}\n")

    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
