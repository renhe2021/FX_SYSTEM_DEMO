# -*- coding: utf-8 -*-
"""Reverse engineer: 找出截图报表的分类逻辑"""
import sys, os, io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pnl-analysis'))

import pandas as pd
from data_loader import load_csv, calc_derived_fields

data_dir = os.path.join(os.path.dirname(__file__), 'ddd', '20260310151934', 'data')
df1 = calc_derived_fields(load_csv(os.path.join(data_dir, 'PROFIT_LOSS_DETAIL_20260131.csv')))
df2 = calc_derived_fields(load_csv(os.path.join(data_dir, 'PROFIT_LOSS_DETAIL_20260228.csv')))

# 截图中的值 (千元)
# 26年1月 | 26年2月
screenshot = {
    '跨境收单':       (1173, 703),
    '汇款互联':       (532, 534),
    '港股汇款':       (0, 0),
    '留学缴费':       (503, 169),   # 641 in screenshot but let me check
    '企业外汇-境内购汇': (3738, 4063),
    '企业外汇-境外账户': (443, 226),
    '企业外汇-基础通道': (423, 192),
    '企业外汇小计':    (4603, 4481),
    '业务侧小计':     (5777, 5184),
    '平台侧汇兑损益':  (-1300, 10824),
    '税后汇兑损益':    (4477, 16008),
    '跨境收单损益':    (17744, -24274),
    'WXG侧损益':      (22250, -33462),
    'FIT侧损益':      (-1521, 9188),
    '平台(不含跨境FIT)': (1723, 1636),
}

print("=" * 80)
print("截图数据 (千元)")
print("=" * 80)
for k, (v1, v2) in screenshot.items():
    print(f"  {k:25s}  1月: {v1:>8,}  2月: {v2:>8,}")

print()
print("=" * 80)
print("原始CSV: 按 渠道 × 业务 × 商户类型 × 产品类型 详细拆分 (千元)")
print("=" * 80)

for label, df in [("1月", df1), ("2月", df2)]:
    print(f"\n--- {label} ---")
    detail = df.groupby(['损益实际归属主体', '所属业务', '商户类型', '产品类型']).agg(
        损益=('损益金额', 'sum'),
        WX=('其中WX', 'sum'),
        FIT=('FIT', 'sum'),
        行数=('损益金额', 'count'),
    ).reset_index()
    detail['损益(千元)'] = (detail['损益'] / 1000).round(0).astype(int)
    detail['WX(千元)'] = (detail['WX'] / 1000).round(0).astype(int)
    detail['FIT(千元)'] = (detail['FIT'] / 1000).round(0).astype(int)
    detail = detail.sort_values('损益(千元)', ascending=False)
    for _, r in detail.iterrows():
        if abs(r['损益(千元)']) >= 1:
            print(f"  {r['损益实际归属主体']:10s} | {r['所属业务']:15s} | {r['商户类型']:8s} | {r['产品类型']:15s} | 损益:{r['损益(千元)']:>8,}  WX:{r['WX(千元)']:>8,}  FIT:{r['FIT(千元)']:>8,}  ({r['行数']}行)")

print()
print("=" * 80)
print("尝试按截图逻辑重分类")
print("=" * 80)

# 假设截图的分类逻辑:
# "业务侧" = 损益户 (商户类型=损益户)
# "平台侧" = 非损益户? 或者按产品类型?
# "跨境收单损益" 可能是 渠道=CFT-WPHK 的全部?

for label, df in [("1月", df1), ("2月", df2)]:
    print(f"\n--- {label} ---")
    
    # 按商户类型分
    by_type = df.groupby('商户类型')[['损益金额','其中WX','FIT']].sum()
    print(f"\n  按商户类型:")
    for idx, row in by_type.iterrows():
        print(f"    {idx:15s}  损益:{row['损益金额']/1000:>10,.0f}  WX:{row['其中WX']/1000:>8,.0f}  FIT:{row['FIT']/1000:>8,.0f}")
    
    # 按产品类型分
    by_prod = df.groupby('产品类型')[['损益金额','其中WX','FIT']].sum()
    print(f"\n  按产品类型:")
    for idx, row in by_prod.iterrows():
        print(f"    {idx:20s}  损益:{row['损益金额']/1000:>10,.0f}  WX:{row['其中WX']/1000:>8,.0f}  FIT:{row['FIT']/1000:>8,.0f}")
    
    # 按渠道分
    by_entity = df.groupby('损益实际归属主体')[['损益金额','其中WX','FIT']].sum()
    print(f"\n  按渠道:")
    for idx, row in by_entity.iterrows():
        print(f"    {idx:12s}  损益:{row['损益金额']/1000:>10,.0f}  WX:{row['其中WX']/1000:>8,.0f}  FIT:{row['FIT']/1000:>8,.0f}")

    # 损益户 按业务
    print(f"\n  损益户 按业务:")
    pnl_acct = df[df['商户类型'] == '损益户']
    by_biz = pnl_acct.groupby('所属业务')[['损益金额','其中WX','FIT']].sum().sort_values('损益金额', ascending=False)
    for idx, row in by_biz.iterrows():
        if abs(row['损益金额']) >= 100:
            print(f"    {idx:20s}  损益:{row['损益金额']/1000:>10,.0f}")
    print(f"    {'合计':20s}  损益:{pnl_acct['损益金额'].sum()/1000:>10,.0f}")

    # 非损益户 按业务
    print(f"\n  非损益户 按业务:")
    non_pnl = df[df['商户类型'] != '损益户']
    if len(non_pnl) > 0:
        by_biz2 = non_pnl.groupby('所属业务')[['损益金额','其中WX','FIT']].sum().sort_values('损益金额', ascending=False)
        for idx, row in by_biz2.iterrows():
            if abs(row['损益金额']) >= 100:
                print(f"    {idx:20s}  损益:{row['损益金额']/1000:>10,.0f}")
        print(f"    {'合计':20s}  损益:{non_pnl['损益金额'].sum()/1000:>10,.0f}")

print()
print("=" * 80)
print("关键验证: 截图里的数字能否拆出来")
print("=" * 80)

for label, df in [("1月", df1), ("2月", df2)]:
    print(f"\n--- {label} ---")
    
    # 尝试: 跨境收单 损益户 + 跨境收单产品类型
    ks_pnl = df[(df['所属业务'] == '跨境收单') & (df['商户类型'] == '损益户')]
    ks_all = df[df['所属业务'] == '跨境收单']
    
    # 企业外汇 = MSO平台 + 纯汇兑 ?
    qywh = df[df['所属业务'].isin(['MSO平台', '纯汇兑'])]
    mso_plat = df[df['所属业务'] == 'MSO平台']
    chun_dui = df[df['所属业务'] == '纯汇兑']
    
    # 试试按产品类型拆 MSO
    if len(df[df['所属业务'] == 'MSO平台']) > 0:
        mso_by_prod = df[df['所属业务'] == 'MSO平台'].groupby('产品类型')['损益金额'].sum()
        print(f"  MSO平台 按产品类型: {dict((k,round(v/1000)) for k,v in mso_by_prod.items())}")
    
    print(f"  跨境收单(损益户): {ks_pnl['损益金额'].sum()/1000:.0f} 千元")
    print(f"  跨境收单(全部):   {ks_all['损益金额'].sum()/1000:.0f} 千元")
    print(f"  互联汇款:         {df[df['所属业务']=='互联汇款']['损益金额'].sum()/1000:.0f} 千元")
    print(f"  留学缴费:         {df[df['所属业务']=='留学缴费']['损益金额'].sum()/1000:.0f} 千元")
    print(f"  留学锁价商户:     {df[df['所属业务']=='留学锁价商户']['损益金额'].sum()/1000:.0f} 千元")
    print(f"  留学(含锁价):     {df[df['所属业务'].str.contains('留学')]['损益金额'].sum()/1000:.0f} 千元")
    print(f"  出境机酒:         {df[df['所属业务']=='出境机酒']['损益金额'].sum()/1000:.0f} 千元")
    print(f"  机酒锁价商户:     {df[df['所属业务']=='机酒周末锁价商户']['损益金额'].sum()/1000:.0f} 千元")
    print(f"  MSO平台:          {mso_plat['损益金额'].sum()/1000:.0f} 千元")
    print(f"  纯汇兑:           {chun_dui['损益金额'].sum()/1000:.0f} 千元")
    print(f"  企业外汇(MSO+纯): {qywh['损益金额'].sum()/1000:.0f} 千元")
    
    # SVF
    svf = df[df['所属业务'] == 'SVF平台']
    print(f"  SVF平台:          {svf['损益金额'].sum()/1000:.0f} 千元")
    
    # 融合
    rh1 = df[df['所属业务'] == '融合一期']
    rh3 = df[df['所属业务'] == '融合三期']
    print(f"  融合一期:         {rh1['损益金额'].sum()/1000:.0f} 千元")
    print(f"  融合三期:         {rh3['损益金额'].sum()/1000:.0f} 千元")
    
    # CFT-WPHK
    wphk = df[df['损益实际归属主体'] == 'CFT-WPHK']
    print(f"  CFT-WPHK(全部):   {wphk['损益金额'].sum()/1000:.0f} 千元")
    print(f"  CFT-WPHK WX:      {wphk['其中WX'].sum()/1000:.0f} 千元")
    print(f"  CFT-WPHK FIT:     {wphk['FIT'].sum()/1000:.0f} 千元")
    
    # CFT
    cft = df[df['损益实际归属主体'] == 'CFT']
    print(f"  CFT(全部):        {cft['损益金额'].sum()/1000:.0f} 千元")
    
    # 全量
    total = df['损益金额'].sum()
    total_wx = df['其中WX'].sum()
    total_fit = df['FIT'].sum()
    print(f"  总计:             损益:{total/1000:.0f}  WX:{total_wx/1000:.0f}  FIT:{total_fit/1000:.0f}")
