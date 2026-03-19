"""
Toxicity PnL Analyzer
=====================

分析客户交易的毒性（Toxicity），通过计算不同时间窗口下的 PnL 曲线
来识别 Toxic/Good/Neutral 客户。

Toxic 客户: 交易后市场往其有利方向移动（客户赚钱，LP亏钱）
Good 客户: 交易后市场往其不利方向移动（客户亏钱，LP赚钱）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import warnings

warnings.filterwarnings('ignore')


class ToxicityAnalyzer:
    """
    客户毒性分析器
    
    通过计算交易后不同时间窗口的 PnL 来评估客户的信息优势
    
    Usage:
    ------
    analyzer = ToxicityAnalyzer(trades_df, market_df)
    pnl_dict = analyzer.compute_pnl_per_unit()
    client_pnl = analyzer.aggregate_by_client(pnl_dict)
    toxic, good, neutral = analyzer.classify_clients(client_pnl)
    analyzer.plot_toxicity_curve(client_pnl, top_n=5)
    plt.show()
    """
    
    # 默认时间窗口（秒）
    DEFAULT_HORIZONS = [1, 5, 10, 30, 60, 300, 900, 1800, 3600, 7200]
    HORIZON_LABELS = {
        1: '1s', 5: '5s', 10: '10s', 30: '30s', 
        60: '1min', 300: '5min', 900: '15min', 1800: '30min',
        3600: '1h', 7200: '2h'
    }
    
    def __init__(self, trades_df: pd.DataFrame, market_df: pd.DataFrame):
        """
        初始化分析器
        
        Args:
            trades_df: 交易日志 DataFrame
                - timestamp (datetime): 成交时间
                - client_id (str): 客户标识
                - side (int): +1 表示买，-1 表示卖
                - notional (float): 名义金额
                - price (float): 成交价格
            
            market_df: 市场行情 DataFrame
                - market_time (datetime): 行情时间点
                - mid_price (float): 标的中间价
        """
        self.trades_df = trades_df.copy()
        self.market_df = market_df.copy()
        
        # 确保时间列是 datetime 类型
        if 'timestamp' in self.trades_df.columns:
            self.trades_df['timestamp'] = pd.to_datetime(self.trades_df['timestamp'])
        if 'market_time' in self.market_df.columns:
            self.market_df['market_time'] = pd.to_datetime(self.market_df['market_time'])
        
        # 对市场数据按时间排序并设置索引
        self.market_df = self.market_df.sort_values('market_time').set_index('market_time')
        
        # 预计算插值函数，用于快速查找任意时间的市场价格
        self._prepare_price_interpolator()
        
        print(f"[ToxicityAnalyzer] Loaded {len(self.trades_df)} trades, {len(self.market_df)} market quotes")
        print(f"[ToxicityAnalyzer] Trades time range: {self.trades_df['timestamp'].min()} ~ {self.trades_df['timestamp'].max()}")
        print(f"[ToxicityAnalyzer] Market time range: {self.market_df.index.min()} ~ {self.market_df.index.max()}")
        print(f"[ToxicityAnalyzer] Unique clients: {self.trades_df['client_id'].nunique()}")
    
    def _prepare_price_interpolator(self):
        """准备价格插值器，用于快速查找任意时间点的市场价格"""
        # 将时间转换为数值（秒级时间戳）
        self._market_times = self.market_df.index.astype(np.int64) // 10**9
        self._market_prices = self.market_df['mid_price'].values
        
        # 记录市场数据的时间范围
        self._market_start = self._market_times[0]
        self._market_end = self._market_times[-1]
    
    def _get_price_at_time(self, timestamp: datetime) -> Optional[float]:
        """
        获取指定时间点的市场价格（使用最近的前一个价格）
        
        Args:
            timestamp: 查询时间点
        
        Returns:
            市场价格，如果超出范围则返回 None
        """
        ts = int(timestamp.timestamp())
        
        # 超出范围检查
        if ts < self._market_start or ts > self._market_end:
            return None
        
        # 使用 searchsorted 找到最近的前一个时间点
        idx = np.searchsorted(self._market_times, ts, side='right') - 1
        if idx < 0:
            idx = 0
        
        return self._market_prices[idx]
    
    def compute_pnl_per_unit(
        self, 
        horizons_seconds: List[int] = None
    ) -> Dict[int, Dict[int, float]]:
        """
        计算每笔交易在不同时间窗口的 per-unit PnL
        
        对于交易 i 在时间窗口 h 上：
            pnl_per_unit[i][h] = side[i] * (market_price[t+h] - trade_price[i])
        
        Args:
            horizons_seconds: 时间窗口列表（秒），默认使用 DEFAULT_HORIZONS
        
        Returns:
            dict: {trade_idx: {horizon: pnl_per_unit}}
        """
        if horizons_seconds is None:
            horizons_seconds = self.DEFAULT_HORIZONS
        
        pnl_dict = {}
        
        print(f"[ToxicityAnalyzer] Computing PnL for {len(self.trades_df)} trades across {len(horizons_seconds)} horizons...")
        
        for idx, row in self.trades_df.iterrows():
            trade_time = row['timestamp']
            trade_price = row['price']
            side = row['side']
            
            pnl_dict[idx] = {}
            
            for h in horizons_seconds:
                # 计算 t+h 时间点
                future_time = trade_time + timedelta(seconds=h)
                
                # 获取该时间点的市场价格
                future_price = self._get_price_at_time(future_time)
                
                if future_price is not None:
                    # per-unit PnL = side * (future_price - trade_price)
                    # 买入后价格上涨 = 正 PnL（客户赚钱）
                    # 卖出后价格下跌 = 正 PnL（客户赚钱）
                    pnl = side * (future_price - trade_price)
                    pnl_dict[idx][h] = pnl
                else:
                    pnl_dict[idx][h] = np.nan
        
        # 统计有效计算的比例
        total_calcs = len(self.trades_df) * len(horizons_seconds)
        valid_calcs = sum(
            1 for trade_pnl in pnl_dict.values() 
            for pnl in trade_pnl.values() 
            if not np.isnan(pnl)
        )
        print(f"[ToxicityAnalyzer] Valid PnL calculations: {valid_calcs}/{total_calcs} ({100*valid_calcs/total_calcs:.1f}%)")
        
        return pnl_dict
    
    def aggregate_by_client(
        self, 
        pnl_dict: Dict[int, Dict[int, float]],
        weight_by_notional: bool = False
    ) -> Dict[str, Dict[int, float]]:
        """
        聚合到 client 级别，计算平均 per-unit PnL
        
        Args:
            pnl_dict: 每笔交易的 PnL 字典 {trade_idx: {horizon: pnl}}
            weight_by_notional: 是否按 notional 加权
        
        Returns:
            dict: {client_id: {horizon: avg_pnl}}
        """
        client_pnl = {}
        
        # 获取所有时间窗口
        horizons = set()
        for trade_pnl in pnl_dict.values():
            horizons.update(trade_pnl.keys())
        horizons = sorted(horizons)
        
        # 按 client 分组
        for client_id in self.trades_df['client_id'].unique():
            client_trades = self.trades_df[self.trades_df['client_id'] == client_id]
            
            client_pnl[client_id] = {}
            
            for h in horizons:
                pnl_values = []
                weights = []
                
                for idx in client_trades.index:
                    if idx in pnl_dict and h in pnl_dict[idx]:
                        pnl = pnl_dict[idx][h]
                        if not np.isnan(pnl):
                            pnl_values.append(pnl)
                            if weight_by_notional:
                                weights.append(client_trades.loc[idx, 'notional'])
                            else:
                                weights.append(1)
                
                if pnl_values:
                    if weight_by_notional:
                        avg_pnl = np.average(pnl_values, weights=weights)
                    else:
                        avg_pnl = np.mean(pnl_values)
                    client_pnl[client_id][h] = avg_pnl
                else:
                    client_pnl[client_id][h] = np.nan
        
        print(f"[ToxicityAnalyzer] Aggregated PnL for {len(client_pnl)} clients")
        
        return client_pnl
    
    def classify_clients(
        self, 
        client_pnl_dict: Dict[str, Dict[int, float]], 
        threshold: float = 0.0001,
        horizon_for_classification: int = 7200
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        根据长期 PnL 将 client 分为 toxic / good / neutral
        
        Toxic: PnL > +threshold（客户赚钱，对 LP 不利）
        Good: PnL < -threshold（客户亏钱，对 LP 有利）
        Neutral: 在中间
        
        Args:
            client_pnl_dict: 客户 PnL 字典
            threshold: 分类阈值
            horizon_for_classification: 用于分类的时间窗口（秒），默认 2h
        
        Returns:
            tuple: (toxic_clients, good_clients, neutral_clients)
        """
        toxic_clients = []
        good_clients = []
        neutral_clients = []
        
        for client_id, pnl_by_horizon in client_pnl_dict.items():
            # 使用指定的时间窗口进行分类
            if horizon_for_classification in pnl_by_horizon:
                pnl = pnl_by_horizon[horizon_for_classification]
            else:
                # 如果没有指定窗口，使用最长的可用窗口
                available_horizons = [h for h in pnl_by_horizon.keys() if not np.isnan(pnl_by_horizon[h])]
                if available_horizons:
                    pnl = pnl_by_horizon[max(available_horizons)]
                else:
                    continue
            
            if np.isnan(pnl):
                continue
            
            if pnl > threshold:
                toxic_clients.append((client_id, pnl))
            elif pnl < -threshold:
                good_clients.append((client_id, pnl))
            else:
                neutral_clients.append((client_id, pnl))
        
        # 按 PnL 排序
        toxic_clients = sorted(toxic_clients, key=lambda x: x[1], reverse=True)
        good_clients = sorted(good_clients, key=lambda x: x[1])  # 越负越好
        neutral_clients = sorted(neutral_clients, key=lambda x: abs(x[1]))  # 越接近0越中性
        
        print(f"[ToxicityAnalyzer] Classification (threshold={threshold}):")
        print(f"  - Toxic: {len(toxic_clients)} clients")
        print(f"  - Good: {len(good_clients)} clients")
        print(f"  - Neutral: {len(neutral_clients)} clients")
        
        return (
            [c[0] for c in toxic_clients],
            [c[0] for c in good_clients],
            [c[0] for c in neutral_clients]
        )
    
    def plot_toxicity_curve(
        self, 
        client_pnl_dict: Dict[str, Dict[int, float]], 
        top_n: int = 5,
        toxic_clients: List[str] = None,
        good_clients: List[str] = None,
        neutral_clients: List[str] = None,
        figsize: Tuple[int, int] = (12, 7),
        title: str = "Client Toxicity PnL Curve",
        use_log_scale: bool = True,
        show_average: bool = True
    ):
        """
        绘制 toxicity PnL 曲线
        
        Args:
            client_pnl_dict: 客户 PnL 字典
            top_n: 展示 top N toxic/good clients
            toxic_clients: toxic 客户列表（可选，如果不提供会自动分类）
            good_clients: good 客户列表
            neutral_clients: neutral 客户列表
            figsize: 图表大小
            title: 标题
            use_log_scale: X 轴是否使用 log scale
            show_average: 是否显示各分类的平均线
        """
        # 如果没有提供分类，自动分类
        if toxic_clients is None or good_clients is None or neutral_clients is None:
            toxic_clients, good_clients, neutral_clients = self.classify_clients(client_pnl_dict)
        
        # 获取所有时间窗口
        all_horizons = set()
        for pnl_by_horizon in client_pnl_dict.values():
            all_horizons.update(pnl_by_horizon.keys())
        horizons = sorted(all_horizons)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # 绘制 y=0 参考线
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
        
        # 颜色设置
        toxic_colors = plt.cm.Reds(np.linspace(0.4, 0.9, min(top_n, len(toxic_clients))))
        good_colors = plt.cm.Greens(np.linspace(0.4, 0.9, min(top_n, len(good_clients))))
        neutral_color = 'gray'
        
        # 绘制 Toxic 客户（top N）
        for i, client_id in enumerate(toxic_clients[:top_n]):
            pnl_values = [client_pnl_dict[client_id].get(h, np.nan) for h in horizons]
            ax.plot(horizons, pnl_values, 
                   color=toxic_colors[i], 
                   linewidth=2, 
                   alpha=0.8,
                   marker='o',
                   markersize=4,
                   label=f'Toxic: {client_id}')
        
        # 绘制 Good 客户（top N）
        for i, client_id in enumerate(good_clients[:top_n]):
            pnl_values = [client_pnl_dict[client_id].get(h, np.nan) for h in horizons]
            ax.plot(horizons, pnl_values, 
                   color=good_colors[i], 
                   linewidth=2, 
                   alpha=0.8,
                   marker='s',
                   markersize=4,
                   label=f'Good: {client_id}')
        
        # 绘制 Neutral 客户（1个代表）
        if neutral_clients:
            client_id = neutral_clients[0]
            pnl_values = [client_pnl_dict[client_id].get(h, np.nan) for h in horizons]
            ax.plot(horizons, pnl_values, 
                   color=neutral_color, 
                   linewidth=2, 
                   alpha=0.7,
                   marker='^',
                   markersize=4,
                   linestyle='--',
                   label=f'Neutral: {client_id}')
        
        # 绘制平均线
        if show_average:
            # Toxic 平均
            if toxic_clients:
                avg_toxic = []
                for h in horizons:
                    vals = [client_pnl_dict[c].get(h, np.nan) for c in toxic_clients if c in client_pnl_dict]
                    avg_toxic.append(np.nanmean(vals) if vals else np.nan)
                ax.plot(horizons, avg_toxic, 
                       color='darkred', linewidth=3, linestyle=':', alpha=0.9,
                       label=f'Toxic Avg (n={len(toxic_clients)})')
            
            # Good 平均
            if good_clients:
                avg_good = []
                for h in horizons:
                    vals = [client_pnl_dict[c].get(h, np.nan) for c in good_clients if c in client_pnl_dict]
                    avg_good.append(np.nanmean(vals) if vals else np.nan)
                ax.plot(horizons, avg_good, 
                       color='darkgreen', linewidth=3, linestyle=':', alpha=0.9,
                       label=f'Good Avg (n={len(good_clients)})')
        
        # X 轴设置
        if use_log_scale:
            ax.set_xscale('log')
        
        # X 轴刻度标签
        ax.set_xticks(horizons)
        ax.set_xticklabels([self.HORIZON_LABELS.get(h, f'{h}s') for h in horizons])
        ax.xaxis.set_major_formatter(ScalarFormatter())
        
        # 标签和标题
        ax.set_xlabel('Time Horizon', fontsize=12)
        ax.set_ylabel('Average Per-Unit PnL (Client Perspective)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # 添加说明
        ax.text(0.02, 0.98, 
               'Positive PnL = Client profits (toxic to LP)\nNegative PnL = Client loses (good for LP)',
               transform=ax.transAxes,
               fontsize=9,
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 图例
        ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=9)
        
        # 网格
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        return fig, ax
    
    def get_client_summary(
        self, 
        client_pnl_dict: Dict[str, Dict[int, float]]
    ) -> pd.DataFrame:
        """
        生成客户汇总表
        
        Returns:
            DataFrame: 包含每个客户在各时间窗口的 PnL
        """
        data = []
        
        for client_id, pnl_by_horizon in client_pnl_dict.items():
            row = {'client_id': client_id}
            
            # 添加各时间窗口的 PnL
            for h, pnl in pnl_by_horizon.items():
                label = self.HORIZON_LABELS.get(h, f'{h}s')
                row[f'pnl_{label}'] = pnl
            
            # 添加交易统计
            client_trades = self.trades_df[self.trades_df['client_id'] == client_id]
            row['trade_count'] = len(client_trades)
            row['total_notional'] = client_trades['notional'].sum()
            row['buy_count'] = (client_trades['side'] == 1).sum()
            row['sell_count'] = (client_trades['side'] == -1).sum()
            
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # 按最长时间窗口的 PnL 排序
        pnl_cols = [c for c in df.columns if c.startswith('pnl_')]
        if pnl_cols:
            df = df.sort_values(pnl_cols[-1], ascending=False)
        
        return df


def generate_sample_data(
    n_trades: int = 500,
    n_clients: int = 20,
    hours: int = 8
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    生成示例数据用于测试
    
    Args:
        n_trades: 交易数量
        n_clients: 客户数量
        hours: 数据时间跨度（小时）
    
    Returns:
        tuple: (trades_df, market_df)
    """
    np.random.seed(42)
    
    # 生成市场数据（每秒一个点）
    start_time = datetime(2026, 1, 16, 9, 0, 0)
    n_seconds = hours * 3600
    
    market_times = [start_time + timedelta(seconds=i) for i in range(n_seconds)]
    
    # 模拟价格走势（随机游走 + 趋势）
    returns = np.random.normal(0, 0.00001, n_seconds)
    prices = 7.25 * np.exp(np.cumsum(returns))
    
    market_df = pd.DataFrame({
        'market_time': market_times,
        'mid_price': prices
    })
    
    # 生成客户列表，设置不同的"毒性"特征
    clients = [f'Client_{i:03d}' for i in range(n_clients)]
    
    # 分配客户类型：20% toxic, 20% good, 60% neutral
    n_toxic = int(n_clients * 0.2)
    n_good = int(n_clients * 0.2)
    
    client_types = {}
    for i, c in enumerate(clients):
        if i < n_toxic:
            client_types[c] = 'toxic'
        elif i < n_toxic + n_good:
            client_types[c] = 'good'
        else:
            client_types[c] = 'neutral'
    
    # 生成交易
    trades = []
    for _ in range(n_trades):
        client_id = np.random.choice(clients)
        client_type = client_types[client_id]
        
        # 随机选择交易时间
        trade_idx = np.random.randint(0, n_seconds - 7200)  # 确保有足够的后续数据
        trade_time = market_times[trade_idx]
        base_price = prices[trade_idx]
        
        # 根据客户类型决定交易方向
        # Toxic 客户：倾向于在价格即将上涨时买入，即将下跌时卖出
        # Good 客户：相反
        # Neutral 客户：随机
        
        future_return = (prices[min(trade_idx + 300, n_seconds-1)] - base_price) / base_price
        
        if client_type == 'toxic':
            # 70% 概率预测正确方向
            if np.random.random() < 0.7:
                side = 1 if future_return > 0 else -1
            else:
                side = np.random.choice([1, -1])
        elif client_type == 'good':
            # 70% 概率预测错误方向
            if np.random.random() < 0.7:
                side = -1 if future_return > 0 else 1
            else:
                side = np.random.choice([1, -1])
        else:
            side = np.random.choice([1, -1])
        
        # 添加一些随机滑点
        slippage = np.random.normal(0, 0.0001)
        trade_price = base_price * (1 + slippage)
        
        notional = np.random.uniform(100000, 1000000)
        
        trades.append({
            'timestamp': trade_time,
            'client_id': client_id,
            'side': side,
            'notional': notional,
            'price': trade_price
        })
    
    trades_df = pd.DataFrame(trades)
    
    print(f"[Sample Data] Generated {len(trades_df)} trades, {len(market_df)} market quotes")
    print(f"[Sample Data] Client distribution: {n_toxic} toxic, {n_good} good, {n_clients - n_toxic - n_good} neutral")
    
    return trades_df, market_df


# ===== 主程序示例 =====
if __name__ == '__main__':
    print("=" * 60)
    print("Toxicity PnL Analyzer - Demo")
    print("=" * 60)
    
    # 1. 生成示例数据
    print("\n[1] Generating sample data...")
    trades_df, market_df = generate_sample_data(n_trades=500, n_clients=20, hours=8)
    
    # 2. 创建分析器
    print("\n[2] Creating analyzer...")
    analyzer = ToxicityAnalyzer(trades_df, market_df)
    
    # 3. 计算 PnL
    print("\n[3] Computing per-trade PnL...")
    pnl_dict = analyzer.compute_pnl_per_unit()
    
    # 4. 聚合到客户级别
    print("\n[4] Aggregating to client level...")
    client_pnl = analyzer.aggregate_by_client(pnl_dict)
    
    # 5. 分类客户
    print("\n[5] Classifying clients...")
    toxic, good, neutral = analyzer.classify_clients(client_pnl, threshold=0.00005)
    
    # 6. 生成汇总表
    print("\n[6] Client Summary:")
    summary_df = analyzer.get_client_summary(client_pnl)
    print(summary_df.to_string(index=False))
    
    # 7. 绘制图表
    print("\n[7] Plotting toxicity curve...")
    fig, ax = analyzer.plot_toxicity_curve(
        client_pnl, 
        top_n=3,
        toxic_clients=toxic,
        good_clients=good,
        neutral_clients=neutral,
        title="Client Toxicity PnL Curve (Demo Data)"
    )
    
    plt.savefig('toxicity_curve.png', dpi=150, bbox_inches='tight')
    print("\n[Done] Chart saved to toxicity_curve.png")
    plt.show()
