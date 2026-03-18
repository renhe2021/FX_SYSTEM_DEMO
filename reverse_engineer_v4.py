# -*- coding: utf-8 -*-
"""Reverse engineer v4: 统一万元单位，精确匹配截图报表"""
import sys, os, io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pnl-analysis'))

import pandas as pd
import numpy as np
from data_loader import load_csv, calc_derived_fields

data_dir = os.path.join(os.path.dirname(__file__), 'ddd', '20260310151934', 'data')
df1 = calc_derived_fields(load_csv(os.path.join(data_dir, 'PROFIT_LOSS_DETAIL_20260131.csv')))
df2 = calc_derived_fields(load_csv(os.path.join(data_dir, 'PROFIT_LOSS_DETAIL_20260228.csv')))

def to_w(v):
    """元 → 万元(四舍五入)"""
    return round(v / 10000)

def to_w_precise(v):
    """元 → 万元(保留1位小数)"""
    return round(v / 10000, 1)

# ============================================================
# 截图中的值 (单位: 万元)
# ============================================================
S = {
    '跨境收单':           (1173, 703),
    '汇款互联':           (532, 534),
    '港股汇款':           (0, 0),
    '留学缴费':           (503, 169),
    '企业外汇-境内购汇':   (3738, 4063),
    '企业外汇-境外账户':   (443, 226),
    '企业外汇-基础通道':   (423, 192),
    '企业外汇小计':        (4603, 4481),
    '业务侧小计':         (5777, 5184),
    '平台侧汇兑损益':     (-1300, 10824),
    '税后汇兑损益':       (4477, 16008),
    '跨境收单损益':       (17744, -24274),
    'WXG侧损益':         (22250, -33462),
    'FIT侧损益':         (-1521, 9188),
    '平台(不含跨境FIT)':  (1723, 1636),
}

print("=" * 90)
print("单位统一：截图=万元, CSV数据从元转万元")
print("=" * 90)

print("\n截图数据 (万元):")
for k, (v1, v2) in S.items():
    print(f"  {k:25s}  1月: {v1:>8,}  2月: {v2:>8,}")

print("\n" + "=" * 90)
print("第一步: 验证截图内部数学关系 (万元)")
print("=" * 90)

for label, idx in [("1月", 0), ("2月", 1)]:
    ks = S['跨境收单'][idx]
    hk = S['汇款互联'][idx]
    gs = S['港股汇款'][idx]
    lx = S['留学缴费'][idx]
    qy = S['企业外汇小计'][idx]
    yw = S['业务侧小计'][idx]
    pt = S['平台侧汇兑损益'][idx]
    tax = S['税后汇兑损益'][idx]
    ks_pnl = S['跨境收单损益'][idx]
    wxg = S['WXG侧损益'][idx]
    fit = S['FIT侧损益'][idx]
    pt_no_fit = S['平台(不含跨境FIT)'][idx]
    
    print(f"\n--- {label} ---")
    
    # 企业外汇子项
    qy_items = S['企业外汇-境内购汇'][idx] + S['企业外汇-境外账户'][idx] + S['企业外汇-基础通道'][idx]
    print(f"  企业外汇: {S['企业外汇-境内购汇'][idx]}+{S['企业外汇-境外账户'][idx]}+{S['企业外汇-基础通道'][idx]} = {qy_items} (截图:{qy}) {'✓' if qy_items == qy else f'✗ 差{qy_items-qy}'}")
    
    # 业务侧 = 跨境收单+互联+港股+留学+企业
    biz_sum = ks + hk + gs + lx + qy
    print(f"  业务侧: {ks}+{hk}+{gs}+{lx}+{qy} = {biz_sum} (截图:{yw}) {'✓' if biz_sum == yw else f'✗ 差{biz_sum-yw}'}")
    
    # 也许有隐藏行(如"其他")? 差额 = 业务侧 - 各项之和
    hidden = yw - biz_sum
    if hidden != 0:
        print(f"    → 隐藏行/调整项 = {hidden}")
    
    # 税后 = 业务侧 + 平台侧
    print(f"  税后: {yw}+({pt}) = {yw+pt} (截图:{tax}) {'✓' if yw+pt == tax else '✗'}")
    
    # WXG 和各项关系
    print(f"  WXG: {wxg}")
    print(f"    税后+跨境收单损益: {tax}+({ks_pnl}) = {tax+ks_pnl} {'✓' if tax+ks_pnl == wxg else f'✗ 差{wxg-tax-ks_pnl}'}")
    
    # WXG + FIT = ?
    print(f"  WXG+FIT: {wxg}+({fit}) = {wxg+fit}")
    
    # 2月: WXG+FIT = -33462+9188 = -24274 = 跨境收单损益! 有意思
    # 1月: WXG+FIT = 22250+(-1521) = 20729 ≠ 17744
    
    # 平台(不含跨境FIT) 
    # 2月: 平台(不含跨境FIT)=1636, FIT侧=9188 → 1636+9188=10824=平台侧! 
    pt_fit_sum = pt_no_fit + fit
    print(f"  平台(不含跨境FIT)+FIT侧: {pt_no_fit}+({fit}) = {pt_fit_sum} (平台侧:{pt}) {'✓' if pt_fit_sum == pt else '✗'}")

print("\n" + "=" * 90)
print("第二步: CSV全量数据转万元，全面对比")
print("=" * 90)

for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n{'='*40} {label} {'='*40}")
    
    # 所有 (渠道×业务×商户×产品) 组合
    detail = df.groupby(['损益实际归属主体', '所属业务', '商户类型', '产品类型']).agg(
        损益=('损益金额', 'sum'),
        WX=('其中WX', 'sum'),
        FIT=('FIT', 'sum'),
        行数=('损益金额', 'count'),
    ).reset_index()
    detail['万元'] = detail['损益'].apply(to_w)
    detail['FIT万'] = detail['FIT'].apply(to_w)
    detail = detail.sort_values('万元', ascending=False)
    
    print(f"\n  全量明细 (|万元| >= 1):")
    for _, r in detail.iterrows():
        if abs(r['万元']) >= 1:
            print(f"    {r['损益实际归属主体']:10s} | {r['所属业务']:12s} | {r['商户类型']:6s} | {r['产品类型']:18s} | 损益:{r['万元']:>7,} FIT:{r['FIT万']:>7,} ({r['行数']}行)")
    
    # ============================================================
    # 对标截图的分类
    # ============================================================
    
    print(f"\n  --- 对标截图各行(万元) ---")
    
    # [跨境收单] 截图的"跨境收单"在业务侧，应该是某个子集
    # 不含 WPHK/CFT 渠道的跨境收单
    # 全部跨境收单(损益户) = MSO(1847千=185万) + WPHK(14156千=1416万) + CFT(-927千=-93万)
    # 截图 = 1173万
    # MSO跨境收单(损益户)
    mso_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'MSO') & (df['商户类型'] == '损益户')]
    wphk_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'CFT-WPHK') & (df['商户类型'] == '损益户')]
    cft_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'CFT') & (df['商户类型'] == '损益户')]
    
    print(f"\n  [跨境收单] 截图={S['跨境收单'][m_idx]}万")
    print(f"    MSO跨境收单(损益户): {to_w_precise(mso_ks['损益金额'].sum())}万")
    print(f"    WPHK跨境收单(损益户): {to_w_precise(wphk_ks['损益金额'].sum())}万")
    print(f"    CFT跨境收单(损益户): {to_w_precise(cft_ks['损益金额'].sum())}万")
    
    # 融合一期/三期
    rh1 = df[df['所属业务'] == '融合一期']
    rh3_all = df[df['所属业务'] == '融合三期']
    rh3_mso = df[(df['所属业务'] == '融合三期') & (df['损益实际归属主体'] == 'MSO')]
    rh3_wphk = df[(df['所属业务'] == '融合三期') & (df['损益实际归属主体'] == 'CFT-WPHK')]
    rh3_cft = df[(df['所属业务'] == '融合三期') & (df['损益实际归属主体'] == 'CFT')]
    
    print(f"    融合一期(WPHK): {to_w_precise(rh1['损益金额'].sum())}万")
    print(f"    融合三期-MSO: {to_w_precise(rh3_mso['损益金额'].sum())}万")
    print(f"    融合三期-WPHK: {to_w_precise(rh3_wphk['损益金额'].sum())}万")
    if len(rh3_cft) > 0:
        print(f"    融合三期-CFT: {to_w_precise(rh3_cft['损益金额'].sum())}万")
    
    # 各种组合尝试
    # MSO跨境收单 + CFT跨境收单 + MSO融合三期
    combo_a = mso_ks['损益金额'].sum() + cft_ks['损益金额'].sum() + rh3_mso['损益金额'].sum()
    # MSO跨境收单 + MSO融合三期
    combo_b = mso_ks['损益金额'].sum() + rh3_mso['损益金额'].sum()
    # WPHK跨境收单 + 融合一期 + 融合三期(WPHK)
    combo_c = wphk_ks['损益金额'].sum() + rh1['损益金额'].sum() + rh3_wphk['损益金额'].sum()
    
    print(f"    组合A(MSO+CFT跨境+MSO融合三): {to_w(combo_a)}万")
    print(f"    组合B(MSO跨境+MSO融合三): {to_w(combo_b)}万")
    print(f"    组合C(WPHK跨境+融合一+WPHK融合三): {to_w(combo_c)}万")
    
    # WPHK跨境收单(损益户) 1月=14156千=1416万 → 很接近1173 但不等
    # 1416 vs 1173 差 243万
    # 也许 WPHK跨境收单 - 某些部分?
    # 或者 WPHK跨境收单 + CFT跨境收单 = 14156-927=13229千=1323万 → 不是1173
    
    # 新思路: 也许截图的"跨境收单"是 FIT 列!
    print(f"    WPHK跨境收单 FIT: {to_w_precise(wphk_ks['FIT'].sum())}万")
    print(f"    MSO跨境收单 FIT: {to_w_precise(mso_ks['FIT'].sum())}万")
    print(f"    CFT跨境收单 FIT: {to_w_precise(cft_ks['FIT'].sum())}万")
    
    # [互联汇款]
    hl = df[df['所属业务'] == '互联汇款']
    print(f"\n  [汇款互联] 截图={S['汇款互联'][m_idx]}万")
    print(f"    互联汇款 损益: {to_w_precise(hl['损益金额'].sum())}万 FIT: {to_w_precise(hl['FIT'].sum())}万")
    # 532千元=53万 vs 截图532万 → 差10倍!
    # 等等... 互联汇款(损益) = 532千元 = 53万, 但截图=532万
    # 这意味着CSV中 互联汇款损益=532千元, 截图=532万元
    # 532万 = 5320千... CSV = 532千
    # 那如果截图单位不是万而是千呢? 532千=截图532千 → 完美匹配!
    # 但用户说截图单位是万...
    
    # 让我同时列出千元和万元
    print(f"    互联汇款 千元: {round(hl['损益金额'].sum()/1000)}")
    print(f"    (如果截图单位是千: 截图{S['汇款互联'][m_idx]}千 vs CSV{round(hl['损益金额'].sum()/1000)}千)")
    
    # [留学缴费]
    lx = df[df['所属业务'] == '留学缴费']
    lx_lock = df[df['所属业务'] == '留学锁价商户']
    print(f"\n  [留学缴费] 截图={S['留学缴费'][m_idx]}万")
    print(f"    留学缴费 千元: {round(lx['损益金额'].sum()/1000)}")
    print(f"    留学+锁价 千元: {round((lx['损益金额'].sum()+lx_lock['损益金额'].sum())/1000)}")
    
    # [纯汇兑]
    chun = df[df['所属业务'] == '纯汇兑']
    print(f"\n  [基础通道] 截图={S['企业外汇-基础通道'][m_idx]}万")
    print(f"    纯汇兑 千元: {round(chun['损益金额'].sum()/1000)}")
    
    # 全量
    total_k = round(df['损益金额'].sum() / 1000)
    total_w = to_w(df['损益金额'].sum())
    print(f"\n  总计: {total_k}千元 = {total_w}万元")

print("\n" + "=" * 90)
print("第三步: 关键验证 - 截图单位到底是千还是万?")
print("=" * 90)

print("""
用户说: "1,173 是1173万的意思"
用户说: "15076这里应该是15,076,000应该是1507万"

如果截图=万元:
  互联汇款截图=532万=5,320,000元, CSV=5,324,862元(千元=532) → CSV千元532 ≈ 截图万元532
  → 不可能! 532千元=53万 ≠ 532万

如果截图=千元:
  互联汇款截图=532千=532,000元, CSV=5,324,862元=5325千元 → 不match

等等... CSV中 损益金额 = 折算CNY损益金额/100
让我验证下原始值...
""")

# 重新检查原始数据
print("互联汇款原始数据:")
for label, df in [("1月", df1), ("2月", df2)]:
    hl = df[df['所属业务'] == '互联汇款']
    raw_sum = hl['折算CNY损益金额'].sum()
    pnl_sum = hl['损益金额'].sum()
    print(f"  {label}: 折算CNY损益金额={raw_sum:,.0f} 损益金额(元)={pnl_sum:,.2f} 千元={pnl_sum/1000:.1f} 万元={pnl_sum/10000:.1f}")

print("\n跨境收单(全部损益户)原始数据:")
for label, df in [("1月", df1), ("2月", df2)]:
    ks = df[(df['所属业务'] == '跨境收单') & (df['商户类型'] == '损益户')]
    raw_sum = ks['折算CNY损益金额'].sum()
    pnl_sum = ks['损益金额'].sum()
    print(f"  {label}: 折算CNY损益金额={raw_sum:,.0f} 损益金额(元)={pnl_sum:,.2f} 千元={pnl_sum/1000:.1f} 万元={pnl_sum/10000:.1f}")

print("\n纯汇兑原始数据:")
for label, df in [("1月", df1), ("2月", df2)]:
    ch = df[df['所属业务'] == '纯汇兑']
    pnl_sum = ch['损益金额'].sum()
    print(f"  {label}: 损益金额(元)={pnl_sum:,.2f} 千元={pnl_sum/1000:.1f} 万元={pnl_sum/10000:.1f}")

print("\n出境机酒原始数据:")
for label, df in [("1月", df1), ("2月", df2)]:
    cj = df[df['所属业务'] == '出境机酒']
    pnl_sum = cj['损益金额'].sum()
    print(f"  {label}: 损益金额(元)={pnl_sum:,.2f} 千元={pnl_sum/1000:.1f} 万元={pnl_sum/10000:.1f}")

print("\n" + "=" * 90)
print("第四步: 也许 折算CNY损益金额 的单位不是'分'而是别的?")
print("=" * 90)

# 检查: 如果 折算CNY损益金额 单位是 元(不是分), 那:
# 损益金额 = 折算CNY损益金额 (不需要/100)
# 互联汇款1月: 折算CNY = 53,248,616
# 如果直接用 → 53,248,616元 = 53249千元 = 5325万元 → 截图532万? 不match
# 如果/100 → 532,486元 = 532千元 → 截图532万? 不match
# 如果/1000 → 53,249元 = 5.3万 → 不match
# 如果截图单位是千元 → 532千 match!

# 让我最终确认: 如果截图单位=千元, 对比结果
print("\n=== 假设截图单位=千元 ===")
for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n--- {label} ---")
    
    def to_k(v): return round(v / 1000)
    
    hl = df[df['所属业务'] == '互联汇款']
    chun = df[df['所属业务'] == '纯汇兑']
    lx = df[df['所属业务'] == '留学缴费']
    lx_lock = df[df['所属业务'] == '留学锁价商户']
    
    csv_hl = to_k(hl['损益金额'].sum())
    csv_chun = to_k(chun['损益金额'].sum())
    csv_lx = to_k(lx['损益金额'].sum())
    csv_lx_lock = to_k(lx_lock['损益金额'].sum())
    
    print(f"  互联汇款: CSV={csv_hl}千 截图={S['汇款互联'][m_idx]} {'✓' if csv_hl == S['汇款互联'][m_idx] else f'✗ 差{csv_hl - S['汇款互联'][m_idx]}'}")
    print(f"  纯汇兑(基础通道): CSV={csv_chun}千 截图={S['企业外汇-基础通道'][m_idx]} {'✓' if csv_chun == S['企业外汇-基础通道'][m_idx] else f'✗ 差{csv_chun - S['企业外汇-基础通道'][m_idx]}'}")
    print(f"  留学缴费: CSV={csv_lx}千 截图={S['留学缴费'][m_idx]} 差{csv_lx - S['留学缴费'][m_idx]}")
    print(f"  留学+锁价: CSV={csv_lx + csv_lx_lock}千 截图={S['留学缴费'][m_idx]} 差{csv_lx + csv_lx_lock - S['留学缴费'][m_idx]}")

print("\n=== 假设截图单位=万元 ===")
for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n--- {label} ---")
    
    def to_w(v): return round(v / 10000)
    
    hl = df[df['所属业务'] == '互联汇款']
    chun = df[df['所属业务'] == '纯汇兑']
    lx = df[df['所属业务'] == '留学缴费']
    lx_lock = df[df['所属业务'] == '留学锁价商户']
    
    csv_hl = to_w(hl['损益金额'].sum())
    csv_chun = to_w(chun['损益金额'].sum())
    csv_lx = to_w(lx['损益金额'].sum())
    csv_lx_lock = to_w(lx_lock['损益金额'].sum())
    
    print(f"  互联汇款: CSV={csv_hl}万 截图={S['汇款互联'][m_idx]} {'✓' if csv_hl == S['汇款互联'][m_idx] else f'差{csv_hl - S['汇款互联'][m_idx]}'}")
    print(f"  纯汇兑(基础通道): CSV={csv_chun}万 截图={S['企业外汇-基础通道'][m_idx]} {'✓' if csv_chun == S['企业外汇-基础通道'][m_idx] else f'差{csv_chun - S['企业外汇-基础通道'][m_idx]}'}")
    print(f"  留学缴费: CSV={csv_lx}万 截图={S['留学缴费'][m_idx]} 差{csv_lx - S['留学缴费'][m_idx]}")
    print(f"  留学+锁价: CSV={csv_lx + csv_lx_lock}万 截图={S['留学缴费'][m_idx]} 差{csv_lx + csv_lx_lock - S['留学缴费'][m_idx]}")

print("\n" + "=" * 90)
print("第五步: 检查 折算CNY损益金额 原始值与截图的直接关系")
print("=" * 90)

# 也许 折算CNY损益金额 的单位根本不是分，而是 0.01元?
# 或者截图看的是另一个字段?

# 直接用各种除数试
print("\n互联汇款1月, 折算CNY损益金额合计:")
hl1_raw = df1[df1['所属业务'] == '互联汇款']['折算CNY损益金额'].sum()
print(f"  原始值: {hl1_raw:,.0f}")
print(f"  /1 = {hl1_raw:,.0f}")
print(f"  /100 = {hl1_raw/100:,.2f} (损益金额=元)")
print(f"  /1000 = {hl1_raw/1000:,.2f}")
print(f"  /10000 = {hl1_raw/10000:,.2f}")
print(f"  /100000 = {hl1_raw/100000:,.2f}")
print(f"  截图 = {S['汇款互联'][0]}")
print(f"  如果截图是千元: {S['汇款互联'][0]}千 = {S['汇款互联'][0]*1000:,}元, 原始/100 = {hl1_raw/100:,.0f}元")
# 532千=532,000, 原始/100=532,486 → 差486元 → 几乎完美！
print(f"  → 截图千元={S['汇款互联'][0]*1000:,} vs CSV元={hl1_raw/100:,.0f} → 差{S['汇款互联'][0]*1000 - hl1_raw/100:,.0f}元")

print("\n纯汇兑1月, 折算CNY损益金额合计:")
ch1_raw = df1[df1['所属业务'] == '纯汇兑']['折算CNY损益金额'].sum()
print(f"  原始值: {ch1_raw:,.0f}")
print(f"  /100 = {ch1_raw/100:,.2f}元 = {ch1_raw/100/1000:,.1f}千元")
print(f"  截图(千): {S['企业外汇-基础通道'][0]}")
print(f"  → 截图千元={S['企业外汇-基础通道'][0]*1000:,} vs CSV元={ch1_raw/100:,.0f} → 差{S['企业外汇-基础通道'][0]*1000 - ch1_raw/100:,.0f}元")

print("\n" + "=" * 90)
print("结论: 截图单位=千元, CSV/100=元, 四舍五入到千元后对比")
print("=" * 90)

# 现在用千元单位，全面对比
def to_k(v):
    return round(v / 1000)

for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n{'='*40} {label} {'='*40}")
    
    # ---------- 业务侧项目 ----------
    # 互联汇款
    hl = df[df['所属业务'] == '互联汇款']
    csv_hl = to_k(hl['损益金额'].sum())
    
    # 纯汇兑 = 企业外汇-基础通道
    chun = df[df['所属业务'] == '纯汇兑']
    csv_chun = to_k(chun['损益金额'].sum())
    
    # 留学
    lx = df[df['所属业务'] == '留学缴费']
    lx_lock = df[df['所属业务'] == '留学锁价商户']
    csv_lx = to_k(lx['损益金额'].sum())
    csv_lx_both = to_k(lx['损益金额'].sum() + lx_lock['损益金额'].sum())
    
    # 出境机酒
    cj = df[df['所属业务'] == '出境机酒']
    cj_lock = df[df['所属业务'] == '机酒周末锁价商户']
    csv_cj = to_k(cj['损益金额'].sum())
    
    # MSO平台
    mso_huanhui_pnl = df[(df['所属业务'] == 'MSO平台') & (df['产品类型'] == '换汇平台') & (df['商户类型'] == '损益户')]
    mso_shoukuan_pnl = df[(df['所属业务'] == 'MSO平台') & (df['产品类型'] == '收款业务') & (df['商户类型'] == '损益户')]
    csv_mso_hh = to_k(mso_huanhui_pnl['损益金额'].sum())
    csv_mso_sk = to_k(mso_shoukuan_pnl['损益金额'].sum())
    
    # 跨境收单(按渠道)
    mso_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'MSO')]
    wphk_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'CFT-WPHK')]
    cft_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'CFT')]
    
    # 融合
    rh1 = df[df['所属业务'] == '融合一期']  # 都在WPHK
    rh3_mso = df[(df['所属业务'] == '融合三期') & (df['损益实际归属主体'] == 'MSO')]
    rh3_wphk = df[(df['所属业务'] == '融合三期') & (df['损益实际归属主体'] == 'CFT-WPHK')]
    rh3_cft = df[(df['所属业务'] == '融合三期') & (df['损益实际归属主体'] == 'CFT')]
    
    # SVF
    svf = df[df['所属业务'] == 'SVF平台']
    
    # MPI
    mpi = df[df['损益实际归属主体'] == 'MPI']
    
    print(f"\n  === 已确认匹配项(千元) ===")
    print(f"  互联汇款: CSV={csv_hl} 截图={S['汇款互联'][m_idx]} {'✓' if csv_hl == S['汇款互联'][m_idx] else '✗'}")
    print(f"  纯汇兑→基础通道: CSV={csv_chun} 截图={S['企业外汇-基础通道'][m_idx]} {'✓' if csv_chun == S['企业外汇-基础通道'][m_idx] else '✗'}")
    
    print(f"\n  === 留学 ===")
    print(f"  留学缴费: CSV={csv_lx} 截图={S['留学缴费'][m_idx]} 差{csv_lx - S['留学缴费'][m_idx]}")
    print(f"  留学+锁价: CSV={csv_lx_both} 截图={S['留学缴费'][m_idx]} 差{csv_lx_both - S['留学缴费'][m_idx]}")
    # 1月: 留学661, 锁价-28, 合计633, 截图503 → 差130
    # 2月: 留学181, 锁价-8, 合计173, 截图169 → 差4
    # 2月几乎对上了! 差4千元可能是四舍五入
    # 1月差130... 也许留学缴费截图只看某一部分?
    
    # 按产品类型看留学缴费
    lx_by_entity = df[(df['产品类型'] == '留学缴费')].groupby('损益实际归属主体')['损益金额'].sum()
    for entity, v in lx_by_entity.items():
        print(f"    产品=留学缴费 {entity}: {to_k(v)}")
    
    print(f"\n  === 跨境收单深度分析 ===")
    print(f"  截图跨境收单={S['跨境收单'][m_idx]} (千元)")
    print(f"    MSO跨境收单: {to_k(mso_ks['损益金额'].sum())}")
    print(f"    WPHK跨境收单: {to_k(wphk_ks['损益金额'].sum())}")
    print(f"    CFT跨境收单: {to_k(cft_ks['损益金额'].sum())}")
    print(f"    融合一期(WPHK): {to_k(rh1['损益金额'].sum())}")
    print(f"    融合三期-MSO: {to_k(rh3_mso['损益金额'].sum())}")
    print(f"    融合三期-WPHK: {to_k(rh3_wphk['损益金额'].sum())}")
    if len(rh3_cft) > 0:
        print(f"    融合三期-CFT: {to_k(rh3_cft['损益金额'].sum())}")
    
    # 尝试: 跨境收单(截图) = MSO跨境收单 + CFT跨境收单 + MSO融合三期
    combo1 = to_k(mso_ks['损益金额'].sum() + cft_ks['损益金额'].sum() + rh3_mso['损益金额'].sum())
    print(f"    MSO跨境+CFT跨境+MSO融合三: {combo1}")
    
    # 尝试: 跨境收单(截图) = MSO跨境收单 + MSO融合三期
    combo2 = to_k(mso_ks['损益金额'].sum() + rh3_mso['损益金额'].sum())
    print(f"    MSO跨境+MSO融合三: {combo2}")
    
    # 尝试: WPHK跨境 - 某些部分?
    # 1月: WPHK跨境=14156, 截图=1173, 差12983
    # 也许截图只是 MSO+MPI 口径?
    mpi_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'MPI')]
    combo3 = to_k(mso_ks['损益金额'].sum() + cft_ks['损益金额'].sum())
    print(f"    MSO+CFT跨境: {combo3}")
    
    # 也许截图的跨境收单 = MSO跨境收单(不含融合)?
    # 1月MSO跨境=1847, 截图=1173, 差674
    # 674 ≈ CFT跨境(-927)? 不
    
    print(f"\n  === 企业外汇-境内购汇 分析 ===")
    print(f"  截图={S['企业外汇-境内购汇'][m_idx]} (千元)")
    print(f"    出境机酒: {csv_cj}")
    print(f"    MSO换汇(损益户): {csv_mso_hh}")
    print(f"    MSO收款(损益户): {csv_mso_sk}")
    print(f"    出境+换汇+收款: {csv_cj + csv_mso_hh + csv_mso_sk}")
    # 1月: 3039+2257+300=5596, 截图3738... 差1858
    # 也许不含MSO换汇? 出境+收款=3039+300=3339, 差399
    # 也许只是出境机酒+MSO收款? 3339 vs 3738 差399
    # 或者 出境机酒 = 企业外汇-出境, 而 境内购汇 = MSO换汇+MSO收款?
    # 2557 + 300 = 2857? 不match
    
    # 按产品类型直接看
    prod_cj = df[df['产品类型'] == '企业外汇-出境']
    prod_hh = df[df['产品类型'] == '换汇平台']
    prod_sk = df[df['产品类型'] == '收款业务']
    
    print(f"    产品=企业外汇-出境: {to_k(prod_cj['损益金额'].sum())}")
    print(f"    产品=换汇平台(全): {to_k(prod_hh['损益金额'].sum())}")
    print(f"    产品=收款业务(全): {to_k(prod_sk['损益金额'].sum())}")
    print(f"    产品=换汇+收款: {to_k(prod_hh['损益金额'].sum() + prod_sk['损益金额'].sum())}")
    print(f"    产品=出境+换汇+收款: {to_k(prod_cj['损益金额'].sum() + prod_hh['损益金额'].sum() + prod_sk['损益金额'].sum())}")
    
    # 只看损益户
    prod_cj_p = df[(df['产品类型'] == '企业外汇-出境') & (df['商户类型'] == '损益户')]
    prod_hh_p = df[(df['产品类型'] == '换汇平台') & (df['商户类型'] == '损益户')]
    prod_sk_p = df[(df['产品类型'] == '收款业务') & (df['商户类型'] == '损益户')]
    print(f"    产品=出境(损益户): {to_k(prod_cj_p['损益金额'].sum())}")
    print(f"    产品=换汇(损益户): {to_k(prod_hh_p['损益金额'].sum())}")
    print(f"    产品=收款(损益户): {to_k(prod_sk_p['损益金额'].sum())}")
    combo_gw = to_k(prod_cj_p['损益金额'].sum() + prod_hh_p['损益金额'].sum() + prod_sk_p['损益金额'].sum())
    print(f"    出境+换汇+收款(损益户): {combo_gw}")
    
    # 也许"境内购汇"对应的是 产品类型=换汇平台 + 收款业务, 不含出境?
    combo_no_cj = to_k(prod_hh_p['损益金额'].sum() + prod_sk_p['损益金额'].sum())
    print(f"    换汇+收款(损益户,不含出境): {combo_no_cj}")
    
    print(f"\n  === 企业外汇-境外账户 分析 ===")
    print(f"  截图={S['企业外汇-境外账户'][m_idx]} (千元)")
    svf_pnl_acct = df[(df['所属业务'] == 'SVF平台') & (df['商户类型'] == '损益户')]
    print(f"    SVF平台(损益户): {to_k(svf_pnl_acct['损益金额'].sum())}")
    # SVF1月=5407, 截图443... 太大了
    
    # MPI?
    mpi_total = to_k(mpi['损益金额'].sum())
    print(f"    MPI全部: {mpi_total}")
    
    # MSO平台的某个子集?
    # MSO收款=300, 截图=443?
    # 也许境外账户=MSO收款+某些其他?
    # 300+143=443? 143来自哪?
    
    print(f"\n  === 大汇总 ===")
    # 全量
    total = to_k(df['损益金额'].sum())
    total_wx = to_k(df['其中WX'].sum())
    total_fit = to_k(df['FIT'].sum())
    
    # 按渠道
    wphk_all = to_k(df[df['损益实际归属主体'] == 'CFT-WPHK']['损益金额'].sum())
    cft_all = to_k(df[df['损益实际归属主体'] == 'CFT']['损益金额'].sum())
    mso_all = to_k(df[df['损益实际归属主体'] == 'MSO']['损益金额'].sum())
    mpi_all = to_k(df[df['损益实际归属主体'] == 'MPI']['损益金额'].sum())
    
    print(f"  全量: 损益={total} WX={total_wx} FIT={total_fit}")
    print(f"  WPHK={wphk_all} CFT={cft_all} MSO={mso_all} MPI={mpi_all}")
    print(f"  WPHK+MSO+MPI(不含CFT)={wphk_all+mso_all+mpi_all}")
    
    # 截图: 税后=业务侧+平台侧, WXG=?, FIT侧=?
    print(f"\n  截图: 税后={S['税后汇兑损益'][m_idx]} 跨境收单损益={S['跨境收单损益'][m_idx]} WXG={S['WXG侧损益'][m_idx]} FIT={S['FIT侧损益'][m_idx]}")
    print(f"  全量总计={total}")
    
    # 验证: 截图里 税后+跨境收单损益 应该等于某个总量?
    # 税后 = 业务侧 + 平台侧 = 4477(1月)
    # 加上跨境收单损益 = 4477 + 17744 = 22221
    # WXG = 22250 → 差29
    # 差29千元可能是四舍五入
    
    # WXG侧 ≈ 税后 + 跨境收单损益
    wxg_calc = S['税后汇兑损益'][m_idx] + S['跨境收单损益'][m_idx]
    print(f"  税后+跨境收单损益={wxg_calc} vs WXG={S['WXG侧损益'][m_idx]} 差{wxg_calc - S['WXG侧损益'][m_idx]}")
    
    # WXG + FIT = ?
    wxg_fit = S['WXG侧损益'][m_idx] + S['FIT侧损益'][m_idx]
    print(f"  WXG+FIT={wxg_fit} vs 全量={total} 差{wxg_fit - total}")
