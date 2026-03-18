# -*- coding: utf-8 -*-
"""
FX Markup Pricing Engine V4
============================
纯计算工具 — 基于真实客单数据的加价收入测算。
Markup 完全由用户输入，初始值 = 0。

核心公式:
  Revenue = Volume × Markup(BPS) × 1e-4
  交易量 = Excel 真实数据，不做任何调整
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json


# ──────────────────── Data Models ────────────────────

@dataclass
class Cell:
    """单个 (业务, 币种) 单元格"""
    business: str
    ccy: str
    volume: float          # 月交易量 — 真实数据
    markup_bps: float      # 当前设定的加价 (BPS) — 用户输入


# ──────────────────── Engine ────────────────────

class MarkupEngine:
    """加价计算引擎 V4 — markup 由用户输入"""

    def __init__(self, name: str = 'summary'):
        self.name = name
        self.cells: Dict[Tuple[str, str], Cell] = {}
        self.businesses: List[str] = []
        self.ccys: List[str] = []
        self.month_total: float = 0

    def load_from_data(self, flat_records: List[Dict], default_markup: float = 0.0):
        """从平铺数据加载，markup 默认全部为 0"""
        self.cells.clear()
        biz_set = set()
        ccy_set = set()

        for rec in flat_records:
            biz = rec['business']
            ccy = rec['ccy']
            vol = rec['volume']

            self.cells[(biz, ccy)] = Cell(
                business=biz, ccy=ccy,
                volume=vol, markup_bps=default_markup,
            )
            biz_set.add(biz)
            ccy_set.add(ccy)

        # 按交易量排序
        biz_totals = {}
        for (b, c), cell in self.cells.items():
            biz_totals[b] = biz_totals.get(b, 0) + cell.volume
        self.businesses = sorted(biz_set, key=lambda b: -biz_totals.get(b, 0))

        ccy_totals = {}
        for (b, c), cell in self.cells.items():
            ccy_totals[c] = ccy_totals.get(c, 0) + cell.volume
        self.ccys = sorted(ccy_set, key=lambda c: -ccy_totals.get(c, 0))

        self.month_total = sum(c.volume for c in self.cells.values())

    # ── 单元格计算（纯公式） ──

    @staticmethod
    def _calc_revenue(volume: float, markup_bps: float) -> float:
        """Revenue = Volume × Markup × 1e-4"""
        return volume * markup_bps * 1e-4

    # ── 全量计算 ──

    def calc_all(self) -> Dict:
        """用当前 markup 配置计算所有单元格的加价收入"""
        cells_out = []
        total_vol = 0.0
        total_rev = 0.0

        biz_summary = {}
        ccy_summary = {}

        for (biz, ccy), cell in self.cells.items():
            if cell.volume <= 0:
                continue

            rev = self._calc_revenue(cell.volume, cell.markup_bps)

            cells_out.append({
                'business': biz,
                'ccy': ccy,
                'volume': round(cell.volume, 0),
                'markup_bps': round(cell.markup_bps, 2),
                'revenue': round(rev, 2),
            })

            total_vol += cell.volume
            total_rev += rev

            if biz not in biz_summary:
                biz_summary[biz] = {'volume': 0.0, 'revenue': 0.0}
            biz_summary[biz]['volume'] += cell.volume
            biz_summary[biz]['revenue'] += rev

            if ccy not in ccy_summary:
                ccy_summary[ccy] = {'volume': 0.0, 'revenue': 0.0}
            ccy_summary[ccy]['volume'] += cell.volume
            ccy_summary[ccy]['revenue'] += rev

        for s in biz_summary.values():
            s['avg_markup_bps'] = round(s['revenue'] / (s['volume'] * 1e-4), 2) if s['volume'] > 0 else 0
            s['volume'] = round(s['volume'], 0)
            s['revenue'] = round(s['revenue'], 2)
            s['annual_revenue'] = round(s['revenue'] * 12, 2)

        for s in ccy_summary.values():
            s['avg_markup_bps'] = round(s['revenue'] / (s['volume'] * 1e-4), 2) if s['volume'] > 0 else 0
            s['volume'] = round(s['volume'], 0)
            s['revenue'] = round(s['revenue'], 2)
            s['annual_revenue'] = round(s['revenue'] * 12, 2)

        avg_markup = round(total_rev / (total_vol * 1e-4), 2) if total_vol > 0 else 0

        return {
            'cells': cells_out,
            'biz_summary': biz_summary,
            'ccy_summary': ccy_summary,
            'totals': {
                'volume': round(total_vol, 0),
                'revenue': round(total_rev, 2),
                'annual_revenue': round(total_rev * 12, 2),
                'avg_markup_bps': avg_markup,
            },
        }

    # ── 矩阵接口 ──

    def get_markup_matrix(self) -> Dict:
        matrix = []
        for biz in self.businesses:
            row = []
            for ccy in self.ccys:
                cell = self.cells.get((biz, ccy))
                row.append(cell.markup_bps if cell and cell.volume > 0 else None)
            matrix.append(row)
        return {'businesses': self.businesses, 'ccys': self.ccys, 'matrix': matrix}

    def get_volume_matrix(self) -> Dict:
        matrix = []
        for biz in self.businesses:
            row = []
            for ccy in self.ccys:
                cell = self.cells.get((biz, ccy))
                row.append(cell.volume if cell else 0)
            matrix.append(row)
        return {'businesses': self.businesses, 'ccys': self.ccys, 'matrix': matrix}

    def get_revenue_matrix(self) -> Dict:
        matrix = []
        for biz in self.businesses:
            row = []
            for ccy in self.ccys:
                cell = self.cells.get((biz, ccy))
                if cell and cell.volume > 0:
                    row.append(round(self._calc_revenue(cell.volume, cell.markup_bps), 2))
                else:
                    row.append(None)
            matrix.append(row)
        return {'businesses': self.businesses, 'ccys': self.ccys, 'matrix': matrix}

    # ── 更新 markup ──

    def update_markup(self, business: str, ccy: str, markup_bps: float):
        key = (business, ccy)
        if key in self.cells:
            self.cells[key].markup_bps = markup_bps

    def batch_update_markups(self, updates: Dict[str, Dict[str, float]]):
        """批量更新: {business: {ccy: markup_bps}}"""
        for biz, ccy_map in updates.items():
            for ccy, markup in ccy_map.items():
                self.update_markup(biz, ccy, markup)

    def set_uniform_markup(self, markup_bps: float):
        """所有单元格设为统一 markup"""
        for cell in self.cells.values():
            cell.markup_bps = markup_bps

    def set_biz_markup(self, business: str, markup_bps: float):
        """设置某业务线所有币种"""
        for (b, c), cell in self.cells.items():
            if b == business:
                cell.markup_bps = markup_bps

    def set_ccy_markup(self, ccy: str, markup_bps: float):
        """设置某币种所有业务线"""
        for (b, c), cell in self.cells.items():
            if c == ccy:
                cell.markup_bps = markup_bps

    # ── Uniform 扫描 ──

    def scan_uniform(self, min_bps=0, max_bps=20, step=0.5) -> List[Dict]:
        """统一 markup 下的 revenue 曲线"""
        markups = np.arange(min_bps, max_bps + step / 2, step)
        results = []
        for m in markups:
            total_rev = 0.0
            for cell in self.cells.values():
                if cell.volume > 0:
                    total_rev += self._calc_revenue(cell.volume, m)
            results.append({
                'markup_bps': round(float(m), 2),
                'revenue': round(total_rev, 2),
                'annual_revenue': round(total_rev * 12, 2),
            })
        return results

    # ── 获取当前配置 ──

    def get_config(self) -> Dict:
        cells = []
        for (biz, ccy), cell in self.cells.items():
            if cell.volume > 0:
                cells.append({
                    'business': biz, 'ccy': ccy,
                    'volume': cell.volume,
                    'markup_bps': cell.markup_bps,
                })
        return {
            'name': self.name,
            'businesses': self.businesses,
            'ccys': self.ccys,
            'month_total': self.month_total,
            'cells': cells,
        }

    # ── 获取币种维度汇总（用于按币种设置 markup）──

    def get_ccy_volumes(self) -> List[Dict]:
        """返回各币种的交易量和当前 markup"""
        ccy_data = {}
        for (biz, ccy), cell in self.cells.items():
            if cell.volume <= 0:
                continue
            if ccy not in ccy_data:
                ccy_data[ccy] = {'ccy': ccy, 'volume': 0.0, 'markups': []}
            ccy_data[ccy]['volume'] += cell.volume
            ccy_data[ccy]['markups'].append(cell.markup_bps)

        result = []
        for ccy in self.ccys:
            if ccy in ccy_data:
                d = ccy_data[ccy]
                avg_m = sum(d['markups']) / len(d['markups']) if d['markups'] else 0
                result.append({
                    'ccy': ccy,
                    'volume': round(d['volume'], 0),
                    'current_markup_bps': round(avg_m, 2),
                })
        return result
