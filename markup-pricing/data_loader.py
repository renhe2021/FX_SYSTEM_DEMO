# -*- coding: utf-8 -*-
"""
Data Loader - 解析月度交易量 Excel
===================================
从 "2026年1月.xlsx" 格式的 Excel 中提取：
  - 汇总表 (row 11~24): 全部主体合并的 业务×币种 交易量
  - MSO 分拆表 (row 26~34): MSO 主体的 业务×币种
  - SVF 分拆表 (row 36~39): SVF 主体的 业务×币种 (含更多小币种)
  - 主体汇总 (row 3~6): MSO / SVF / SVF-AUTOFX 的 业务线总量
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, List, Tuple, Optional


class FXDataLoader:
    """加载并解析 FX 交易量 Excel 数据"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.raw_df = None
        self.summary_matrix = None       # 全量: 业务×币种
        self.mso_matrix = None           # MSO: 业务×币种
        self.svf_matrix = None           # SVF: 业务×币种
        self.entity_summary = None       # 主体×业务线
        self.month_label = os.path.basename(filepath).replace('.xlsx', '')

    def load(self) -> 'FXDataLoader':
        """加载 Excel 并解析所有表"""
        self.raw_df = pd.read_excel(self.filepath, header=None)
        self._parse_summary_matrix()
        self._parse_mso_matrix()
        self._parse_svf_matrix()
        self._parse_entity_summary()
        return self

    # ──────── 解析汇总表 (行 11~24) ────────

    def _parse_summary_matrix(self):
        """解析全量 业务×币种 矩阵 (行索引 11=header, 12~23=data, 24=总计)"""
        df = self.raw_df

        # 行 11 是 header: 行标签, AUD, CAD, CHF, EUR, ...
        header_row = 11
        ccys = []
        for c in range(2, 16):  # col 2~15
            val = df.iloc[header_row, c]
            if pd.notna(val):
                ccys.append(str(val).strip())

        rows = []
        for r in range(12, 24):  # row 12~23 (data rows, 24 is 总计)
            biz = df.iloc[r, 1]
            if pd.isna(biz):
                continue
            biz = str(biz).strip()
            volumes = {}
            for i, ccy in enumerate(ccys):
                val = df.iloc[r, 2 + i]
                volumes[ccy] = float(val) if pd.notna(val) else 0.0
            rows.append({'business': biz, **volumes})

        self.summary_matrix = pd.DataFrame(rows).set_index('business')
        # 去掉 "总计" 列（如果存在）
        if '总计' in self.summary_matrix.columns:
            self.summary_matrix = self.summary_matrix.drop(columns=['总计'])
        # 去掉 "总计" 行（如果存在）
        if '总计' in self.summary_matrix.index:
            self.summary_matrix = self.summary_matrix.drop(index=['总计'])

    # ──────── 解析 MSO 分拆表 (行 26~34) ────────

    def _parse_mso_matrix(self):
        """MSO 分币种分业务"""
        df = self.raw_df

        header_row = 26
        ccys = []
        for c in range(2, 16):
            val = df.iloc[header_row, c]
            if pd.notna(val):
                ccys.append(str(val).strip())

        rows = []
        for r in range(27, 34):
            biz = df.iloc[r, 1]
            if pd.isna(biz):
                continue
            biz = str(biz).strip()
            if biz == '总计':
                continue
            volumes = {}
            for i, ccy in enumerate(ccys):
                val = df.iloc[r, 2 + i]
                volumes[ccy] = float(val) if pd.notna(val) and val != 0 else 0.0
            rows.append({'business': biz, **volumes})

        self.mso_matrix = pd.DataFrame(rows).set_index('business')
        if '总计' in self.mso_matrix.columns:
            self.mso_matrix = self.mso_matrix.drop(columns=['总计'])

    # ──────── 解析 SVF 分拆表 (行 36~39) ────────

    def _parse_svf_matrix(self):
        """SVF 分币种分业务 (更多币种 AED~USD)"""
        df = self.raw_df

        header_row = 36
        ccys = []
        for c in range(2, 28):  # SVF 表有更多列
            val = df.iloc[header_row, c]
            if pd.notna(val):
                ccys.append(str(val).strip())

        rows = []
        for r in range(37, 40):
            biz = df.iloc[r, 1]
            if pd.isna(biz):
                continue
            biz = str(biz).strip()
            if biz == '总计':
                continue
            volumes = {}
            for i, ccy in enumerate(ccys):
                val = df.iloc[r, 2 + i]
                volumes[ccy] = float(val) if pd.notna(val) else 0.0
            rows.append({'business': biz, **volumes})

        self.svf_matrix = pd.DataFrame(rows).set_index('business')
        if '总计' in self.svf_matrix.columns:
            self.svf_matrix = self.svf_matrix.drop(columns=['总计'])

    # ──────── 解析主体汇总 (行 2~5) ────────

    def _parse_entity_summary(self):
        """主体级汇总: MSO / SVF / SVF-AUTOFX 各业务线总量"""
        df = self.raw_df

        # 行 2 是业务线 header
        biz_names = []
        for c in range(2, 10):
            val = df.iloc[2, c]
            if pd.notna(val):
                biz_names.append(str(val).strip().replace('\n', ' '))

        rows = []
        for r in range(3, 6):  # MSO, SVF, SVF-AUTOFX
            entity = df.iloc[r, 1]
            if pd.isna(entity):
                continue
            entity = str(entity).strip()
            volumes = {}
            for i, biz in enumerate(biz_names):
                val = df.iloc[r, 2 + i]
                volumes[biz] = float(val) if pd.notna(val) else 0.0
            rows.append({'entity': entity, **volumes})

        self.entity_summary = pd.DataFrame(rows).set_index('entity')

    # ──────── 输出接口 ────────

    def get_all_businesses(self) -> List[str]:
        """获取所有业务线"""
        if self.summary_matrix is not None:
            return self.summary_matrix.index.tolist()
        return []

    def get_all_ccys(self, source='summary') -> List[str]:
        """获取所有币种"""
        mat = self._get_matrix(source)
        if mat is not None:
            return mat.columns.tolist()
        return []

    def get_volume(self, business: str, ccy: str, source='summary') -> float:
        """获取某业务×某币种的交易量"""
        mat = self._get_matrix(source)
        if mat is not None and business in mat.index and ccy in mat.columns:
            return float(mat.loc[business, ccy])
        return 0.0

    def get_business_total(self, business: str, source='summary') -> float:
        """获取某业务线的总交易量"""
        mat = self._get_matrix(source)
        if mat is not None and business in mat.index:
            return float(mat.loc[business].sum())
        return 0.0

    def get_ccy_total(self, ccy: str, source='summary') -> float:
        """获取某币种的总交易量"""
        mat = self._get_matrix(source)
        if mat is not None and ccy in mat.columns:
            return float(mat[ccy].sum())
        return 0.0

    def get_grand_total(self, source='summary') -> float:
        """获取总交易量"""
        mat = self._get_matrix(source)
        if mat is not None:
            return float(mat.values.sum())
        return 0.0

    def to_flat_records(self, source='summary') -> List[Dict]:
        """转为平铺记录 [{business, ccy, volume}, ...]"""
        mat = self._get_matrix(source)
        if mat is None:
            return []
        records = []
        for biz in mat.index:
            for ccy in mat.columns:
                vol = float(mat.loc[biz, ccy])
                if vol > 0:
                    records.append({
                        'business': biz,
                        'ccy': ccy,
                        'volume': vol,
                    })
        return records

    def to_matrix_dict(self, source='summary') -> Dict:
        """转为 {businesses, ccys, matrix} 格式"""
        mat = self._get_matrix(source)
        if mat is None:
            return {'businesses': [], 'ccys': [], 'matrix': []}
        return {
            'businesses': mat.index.tolist(),
            'ccys': mat.columns.tolist(),
            'matrix': mat.fillna(0).values.tolist(),
        }

    def _get_matrix(self, source: str) -> Optional[pd.DataFrame]:
        if source == 'mso':
            return self.mso_matrix
        elif source == 'svf':
            return self.svf_matrix
        elif source == 'entity':
            return self.entity_summary
        return self.summary_matrix


# ──────── 便捷加载 ────────

def load_monthly_data(filepath: str) -> FXDataLoader:
    """快捷加载"""
    return FXDataLoader(filepath).load()


if __name__ == '__main__':
    import sys
    fp = sys.argv[1] if len(sys.argv) > 1 else r'data\2026年1月.xlsx'
    loader = load_monthly_data(fp)

    print(f"\n{'='*60}")
    print(f"月度数据: {loader.month_label}")
    print(f"{'='*60}")

    print(f"\n总交易量: ${loader.get_grand_total():,.0f}")

    print(f"\n业务线列表: {loader.get_all_businesses()}")
    print(f"币种列表: {loader.get_all_ccys()}")

    print(f"\n[汇总矩阵]")
    print(loader.summary_matrix.to_string())

    print(f"\n[主体汇总]")
    print(loader.entity_summary.to_string())
