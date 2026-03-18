# -*- coding: utf-8 -*-
"""Reverse engineer v2: 精确匹配截图报表分类逻辑"""
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

# 截图中的值 (千元)
# 1月 | 2月
screenshot = {
    '跨境收单':           (1173, 703),
    '汇款互联':           (532, 534),
    '港股汇款':           (0, 0),
    '留学缴费':           (503, 169),
    '企业外汇-境内购汇':   (3738, 4063),
    '企业外汇-境外账户':   (443, 226),
    '企业外汇-基础通道':   (423, 192),
    '企业外汇小计':        (4603, 4481),
    '业务侧小计':         (5777, 5184),     # 注意: 1173+532+0+503+4603 = 6811 != 5777
    '平台侧汇兑损益':     (-1300, 10824),
    '税后汇兑损益':       (4477, 16008),     # 5777 + (-1300) = 4477 ✓; 5184+10824=16008 ✓
    '跨境收单损益':       (17744, -24274),
    'WXG侧损益':         (22250, -33462),
    'FIT侧损益':         (-1521, 9188),
    '平台(不含跨境FIT)':  (1723, 1636),
}

def to_k(v):
    """元 → 千元(整数)"""
    return round(v / 1000)

print("=" * 90)
print("第一步: 验证截图内部的数学关系")
print("=" * 90)

for label, idx in [("1月", 0), ("2月", 1)]:
    ks = screenshot['跨境收单'][idx]
    hk = screenshot['汇款互联'][idx]
    gs = screenshot['港股汇款'][idx]
    lx = screenshot['留学缴费'][idx]
    qy = screenshot['企业外汇小计'][idx]
    yw_sub = screenshot['业务侧小计'][idx]
    pt = screenshot['平台侧汇兑损益'][idx]
    tax = screenshot['税后汇兑损益'][idx]
    ks_pnl = screenshot['跨境收单损益'][idx]
    wxg = screenshot['WXG侧损益'][idx]
    fit = screenshot['FIT侧损益'][idx]
    pt_no_fit = screenshot['平台(不含跨境FIT)'][idx]
    
    print(f"\n--- {label} ---")
    biz_sum = ks + hk + gs + lx + qy
    print(f"  业务侧各项之和: {ks}+{hk}+{gs}+{lx}+{qy} = {biz_sum} (截图:{yw_sub}) → {'✓' if biz_sum == yw_sub else f'✗ 差{biz_sum - yw_sub}'}")
    
    # 企业外汇子项
    qy_items = screenshot['企业外汇-境内购汇'][idx] + screenshot['企业外汇-境外账户'][idx] + screenshot['企业外汇-基础通道'][idx]
    print(f"  企业外汇子项之和: {screenshot['企业外汇-境内购汇'][idx]}+{screenshot['企业外汇-境外账户'][idx]}+{screenshot['企业外汇-基础通道'][idx]} = {qy_items} (截图:{qy}) → {'✓' if qy_items == qy else f'✗ 差{qy_items - qy}'}")
    
    # 税后 = 业务侧 + 平台侧
    tax_calc = yw_sub + pt
    print(f"  税后=业务侧+平台侧: {yw_sub}+{pt} = {tax_calc} (截图:{tax}) → {'✓' if tax_calc == tax else f'✗ 差{tax_calc - tax}'}")
    
    # WXG = 税后 + 跨境收单损益?
    wxg_calc = tax + ks_pnl
    print(f"  WXG=税后+跨境收单: {tax}+{ks_pnl} = {wxg_calc} (截图:{wxg}) → {'✓' if wxg_calc == wxg else f'✗ 差{wxg_calc - wxg}'}")
    
    wxg_calc2 = yw_sub + pt + ks_pnl
    print(f"  WXG=业务+平台+跨境: {yw_sub}+{pt}+{ks_pnl} = {wxg_calc2} → {'✓' if wxg_calc2 == wxg else f'✗ 差{wxg_calc2 - wxg}'}")
    
    # FIT 的关系
    print(f"  FIT侧: {fit}")
    print(f"  平台(不含跨境FIT): {pt_no_fit}")
    print(f"  WXG + FIT = {wxg + fit}")
    print(f"  平台 + FIT = {pt + fit}")
    
    # 尝试: 平台(不含跨境FIT) + FIT侧 = ?
    print(f"  平台(不含跨境FIT) + FIT侧 = {pt_no_fit + fit}")

print()
print("=" * 90)
print("第二步: CSV数据全量明细(千元)")  
print("=" * 90)

for label, df in [("1月", df1), ("2月", df2)]:
    print(f"\n{'='*30} {label} {'='*30}")
    
    # 完整交叉表
    detail = df.groupby(['损益实际归属主体', '所属业务', '商户类型', '产品类型']).agg(
        损益=('损益金额', 'sum'),
        行数=('损益金额', 'count'),
    ).reset_index()
    detail['千元'] = detail['损益'].apply(to_k)
    detail = detail.sort_values('千元', ascending=False)
    
    print(f"\n  所有组合 (|千元| >= 1):")
    for _, r in detail.iterrows():
        if abs(r['千元']) >= 1:
            print(f"    {r['损益实际归属主体']:10s} | {r['所属业务']:12s} | {r['商户类型']:6s} | {r['产品类型']:18s} | {r['千元']:>8,} ({r['行数']}行)")

print()
print("=" * 90)
print("第三步: 尝试各种分类假设来匹配截图")
print("=" * 90)

for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n{'='*30} {label} {'='*30}")
    
    # === 假设1: 截图中的"跨境收单" 是某些特定条件 ===
    # CSV跨境收单(损益户) = 15076千(1月), 70千(2月)  → 截图=1173, 703  → 不match
    # 但截图 "跨境收单损益" = 17744(1月) → 接近? 不
    
    # 也许截图"跨境收单"仅指 MSO 渠道的跨境收单(损益户)?
    mso_ks_pnl = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'MSO') & (df['商户类型'] == '损益户')]
    mso_ks = to_k(mso_ks_pnl['损益金额'].sum())
    
    # CFT-WPHK的跨境收单
    wphk_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'CFT-WPHK')]
    wphk_ks_v = to_k(wphk_ks['损益金额'].sum())
    
    # 融合一期+融合三期 (产品类型=跨境收单)
    rh_ks = df[(df['所属业务'].isin(['融合一期', '融合三期'])) & (df['产品类型'] == '跨境收单')]
    rh_ks_v = to_k(rh_ks['损益金额'].sum())
    
    # 所有渠道中的"跨境收单"损益户
    all_ks_pnl = df[(df['所属业务'] == '跨境收单') & (df['商户类型'] == '损益户')]
    
    print(f"\n  [跨境收单] 截图={screenshot['跨境收单'][m_idx]}")
    print(f"    MSO跨境收单(损益户): {mso_ks}")
    print(f"    CFT-WPHK跨境收单: {wphk_ks_v}")
    print(f"    融合(跨境收单): {rh_ks_v}")
    print(f"    MSO跨境收单+融合: {mso_ks + rh_ks_v}")
    
    # === 跨境收单(损益户)中排除CFT-WPHK和CFT的部分 ===
    ks_excl_wphk = df[(df['所属业务'] == '跨境收单') & (df['商户类型'] == '损益户') & (~df['损益实际归属主体'].isin(['CFT-WPHK']))]
    print(f"    跨境收单(损益户,非WPHK): {to_k(ks_excl_wphk['损益金额'].sum())}")
    
    # 跨境收单(产品类型),不管所属业务
    ks_prod = df[df['产品类型'] == '跨境收单']
    ks_prod_pnl = df[(df['产品类型'] == '跨境收单') & (df['商户类型'] == '损益户')]
    print(f"    产品类型=跨境收单(全部): {to_k(ks_prod['损益金额'].sum())}")
    print(f"    产品类型=跨境收单(损益户): {to_k(ks_prod_pnl['损益金额'].sum())}")
    
    # MSO的跨境收单(产品类型=跨境收单, 不管所属业务)
    mso_ks_prod = df[(df['产品类型'] == '跨境收单') & (df['损益实际归属主体'] == 'MSO')]
    print(f"    MSO产品=跨境收单: {to_k(mso_ks_prod['损益金额'].sum())}")
    
    # === 留学缴费 ===
    lx_pnl = df[(df['所属业务'] == '留学缴费') & (df['商户类型'] == '损益户')]
    lx_all = df[df['所属业务'] == '留学缴费']
    lx_lock = df[df['所属业务'] == '留学锁价商户']
    lx_prod = df[df['产品类型'] == '留学缴费']
    
    print(f"\n  [留学缴费] 截图={screenshot['留学缴费'][m_idx]}")
    print(f"    留学缴费(损益户): {to_k(lx_pnl['损益金额'].sum())}")
    print(f"    留学缴费(全部): {to_k(lx_all['损益金额'].sum())}")
    print(f"    留学锁价商户: {to_k(lx_lock['损益金额'].sum())}")
    print(f"    留学+锁价: {to_k(lx_all['损益金额'].sum() + lx_lock['损益金额'].sum())}")
    print(f"    产品类型=留学缴费: {to_k(lx_prod['损益金额'].sum())}")
    
    # === 出境机酒 ===
    cj = df[df['所属业务'] == '出境机酒']
    cj_lock = df[df['所属业务'] == '机酒周末锁价商户']
    print(f"\n  [出境机酒]")
    print(f"    出境机酒: {to_k(cj['损益金额'].sum())}")
    print(f"    机酒锁价商户: {to_k(cj_lock['损益金额'].sum())}")
    print(f"    出境机酒+锁价: {to_k(cj['损益金额'].sum() + cj_lock['损益金额'].sum())}")
    
    # === 企业外汇 ===
    print(f"\n  [企业外汇] 截图小计={screenshot['企业外汇小计'][m_idx]}")
    # 按产品类型拆
    for pt_name in ['企业外汇-境内购汇', '企业外汇-出境', '企业外汇-境外账户', '企业外汇-纯汇兑']:
        sub = df[df['产品类型'] == pt_name]
        sub_pnl = df[(df['产品类型'] == pt_name) & (df['商户类型'] == '损益户')]
        sub_fixed = df[(df['产品类型'] == pt_name) & (df['商户类型'] == '固收户')]
        print(f"    产品={pt_name}: 全部={to_k(sub['损益金额'].sum())} 损益户={to_k(sub_pnl['损益金额'].sum())} 固收户={to_k(sub_fixed['损益金额'].sum())}")
    
    # 按所属业务拆 (MSO平台、纯汇兑、出境机酒 都可能包含企业外汇)
    mso = df[df['所属业务'] == 'MSO平台']
    mso_pnl = df[(df['所属业务'] == 'MSO平台') & (df['商户类型'] == '损益户')]
    # MSO平台按产品类型拆
    print(f"\n    MSO平台 按产品类型:")
    mso_by_prod = mso.groupby(['产品类型', '商户类型'])['损益金额'].sum().reset_index()
    for _, r in mso_by_prod.iterrows():
        print(f"      {r['产品类型']:20s} ({r['商户类型']}) = {to_k(r['损益金额']):>8,}")
    
    chundui = df[df['所属业务'] == '纯汇兑']
    print(f"    纯汇兑(全部): {to_k(chundui['损益金额'].sum())}")
    
    # 截图中 企业外汇-境内购汇 = MSO平台(换汇平台+收款业务) + 出境机酒?
    mso_huanhui = df[(df['所属业务'] == 'MSO平台') & (df['产品类型'] == '换汇平台') & (df['商户类型'] == '损益户')]
    mso_shoukuan = df[(df['所属业务'] == 'MSO平台') & (df['产品类型'] == '收款业务') & (df['商户类型'] == '损益户')]
    print(f"\n    MSO换汇平台(损益户): {to_k(mso_huanhui['损益金额'].sum())}")
    print(f"    MSO收款业务(损益户): {to_k(mso_shoukuan['损益金额'].sum())}")
    print(f"    MSO换汇+收款(损益户): {to_k(mso_huanhui['损益金额'].sum() + mso_shoukuan['损益金额'].sum())}")
    print(f"    MSO换汇+收款+出境机酒: {to_k(mso_huanhui['损益金额'].sum() + mso_shoukuan['损益金额'].sum() + cj['损益金额'].sum())}")
    
    # 境内购汇 = MSO换汇+收款+出境机酒?
    target_gw = screenshot['企业外汇-境内购汇'][m_idx]
    actual_combo = to_k(mso_huanhui['损益金额'].sum() + mso_shoukuan['损益金额'].sum() + cj['损益金额'].sum())
    print(f"    截图境内购汇={target_gw}, MSO换+收+机酒={actual_combo} → {'✓' if target_gw == actual_combo else f'✗ 差{target_gw - actual_combo}'}")
    
    # 另一种: 产品类型=企业外汇-出境(就是出境机酒) 或者 企业外汇-境内购汇 
    prod_gw = df[df['产品类型'] == '企业外汇-境内购汇']
    print(f"    产品类型=企业外汇-境内购汇: {to_k(prod_gw['损益金额'].sum())}")
    
    # 也许 "境内购汇" = 出境机酒 + MSO换汇平台(损益户)?
    combo2 = to_k(cj['损益金额'].sum() + mso_huanhui['损益金额'].sum())
    print(f"    出境机酒+MSO换汇(损益户): {combo2}")
    
    # 也许 "境内购汇" = 出境机酒 + 机酒锁价 + MSO收款(损益户)?
    combo3 = to_k(cj['损益金额'].sum() + mso_shoukuan['损益金额'].sum())
    print(f"    出境机酒+MSO收款(损益户): {combo3}")
    
    # === 企业外汇-境外账户 ===
    # 截图: 1月=443, 2月=226
    print(f"\n  [企业外汇-境外账户] 截图={screenshot['企业外汇-境外账户'][m_idx]}")
    prod_jw = df[df['产品类型'] == '企业外汇-境外账户']
    print(f"    产品类型=企业外汇-境外账户: {to_k(prod_jw['损益金额'].sum())}")
    # 看看哪些业务有这个产品类型
    if len(prod_jw) > 0:
        jw_detail = prod_jw.groupby(['所属业务', '商户类型'])['损益金额'].sum()
        for (biz, mt), v in jw_detail.items():
            print(f"      {biz}({mt}): {to_k(v)}")
    
    # === 企业外汇-基础通道 ===
    # 截图: 1月=423, 2月=192 → 这就是纯汇兑!
    print(f"\n  [企业外汇-基础通道] 截图={screenshot['企业外汇-基础通道'][m_idx]}")
    print(f"    纯汇兑: {to_k(chundui['损益金额'].sum())} → {'✓' if to_k(chundui['损益金额'].sum()) == screenshot['企业外汇-基础通道'][m_idx] else '✗'}")
    
    # === 业务侧小计 ===
    # 截图: 1月=5777, 2月=5184
    # 按截图逻辑: 跨境收单+汇款互联+港股汇款+留学缴费+企业外汇小计
    # 但 1173+532+0+503+4603 = 6811 ≠ 5777 → 差 1034
    # 也许 "出境机酒" 被拆到了企业外汇-境内购汇 里面?
    # 如果 "业务侧" = 跨境收单 + 汇款互联 + 留学缴费 + 企业外汇(不含出境)
    # 那 企业外汇不含出境 = 4603 - 出境?
    
    print(f"\n  [业务侧小计] 截图={screenshot['业务侧小计'][m_idx]}")
    # 让我直接试损益户数据
    pnl_acct = df[df['商户类型'] == '损益户']
    pnl_total = to_k(pnl_acct['损益金额'].sum())
    print(f"    损益户总计: {pnl_total}")
    
    # 损益户 且不含 SVF/融合一期/融合三期
    pnl_no_svf = df[(df['商户类型'] == '损益户') & (~df['所属业务'].isin(['SVF平台', '融合一期', '融合三期']))]
    pnl_no_svf_v = to_k(pnl_no_svf['损益金额'].sum())
    print(f"    损益户(不含SVF/融合): {pnl_no_svf_v}")
    
    # MSO损益户
    mso_pnl_total = to_k(mso_pnl['损益金额'].sum())
    print(f"    MSO损益户: {mso_pnl_total}")
    
    # MSO全部 (含固收)
    mso_all = to_k(mso['损益金额'].sum())
    print(f"    MSO全部: {mso_all}")
    
    # 方案: 业务侧 = MSO渠道 损益户 + MPI 损益户 (不含MSO平台互联收单)
    # 也就是 "直接业务相关"
    mso_biz = df[(df['损益实际归属主体'].isin(['MSO', 'MPI'])) & (df['商户类型'] == '损益户')]
    mso_biz_v = to_k(mso_biz['损益金额'].sum())
    print(f"    MSO+MPI(损益户): {mso_biz_v}")
    
    # === 平台侧 ===
    print(f"\n  [平台侧汇兑损益] 截图={screenshot['平台侧汇兑损益'][m_idx]}")
    non_pnl = df[df['商户类型'] != '损益户']
    non_pnl_v = to_k(non_pnl['损益金额'].sum())
    print(f"    非损益户: {non_pnl_v}")
    
    # CFT-WPHK
    wphk = df[df['损益实际归属主体'] == 'CFT-WPHK']
    wphk_v = to_k(wphk['损益金额'].sum())
    print(f"    CFT-WPHK(全部): {wphk_v}")
    
    wphk_pnl = df[(df['损益实际归属主体'] == 'CFT-WPHK') & (df['商户类型'] == '损益户')]
    wphk_pnl_v = to_k(wphk_pnl['损益金额'].sum())
    print(f"    CFT-WPHK(损益户): {wphk_pnl_v}")
    
    # SVF
    svf = df[df['所属业务'] == 'SVF平台']
    svf_v = to_k(svf['损益金额'].sum())
    print(f"    SVF平台: {svf_v}")
    
    svf_pnl = df[(df['所属业务'] == 'SVF平台') & (df['商户类型'] == '损益户')]
    svf_pnl_v = to_k(svf_pnl['损益金额'].sum())
    print(f"    SVF平台(损益户): {svf_pnl_v}")
    
    # 融合
    rh1 = df[df['所属业务'] == '融合一期']
    rh3 = df[df['所属业务'] == '融合三期']
    print(f"    融合一期: {to_k(rh1['损益金额'].sum())}")
    print(f"    融合三期: {to_k(rh3['损益金额'].sum())}")
    print(f"    融合合计: {to_k(rh1['损益金额'].sum() + rh3['损益金额'].sum())}")
    
    # 平台侧 = SVF + 融合一期 + 融合三期?
    combo_pt = svf_v + to_k(rh1['损益金额'].sum()) + to_k(rh3['损益金额'].sum())
    print(f"    SVF+融合: {combo_pt}")
    
    # 平台侧 = CFT-WPHK(损益户) - 某些业务?
    # WPHK损益户: SVF + 跨境收单 + 融合一期
    wphk_svf = df[(df['损益实际归属主体'] == 'CFT-WPHK') & (df['所属业务'] == 'SVF平台')]
    wphk_rh1 = df[(df['损益实际归属主体'] == 'CFT-WPHK') & (df['所属业务'] == '融合一期')]
    wphk_ks_d = df[(df['损益实际归属主体'] == 'CFT-WPHK') & (df['所属业务'] == '跨境收单')]
    print(f"    WPHK SVF: {to_k(wphk_svf['损益金额'].sum())}")
    print(f"    WPHK 融合一期: {to_k(wphk_rh1['损益金额'].sum())}")
    print(f"    WPHK 跨境收单: {to_k(wphk_ks_d['损益金额'].sum())}")
    
    # === 跨境收单损益 ===
    print(f"\n  [跨境收单损益] 截图={screenshot['跨境收单损益'][m_idx]}")
    # 可能 = CFT-WPHK跨境收单 + 融合? 
    wphk_ks_v2 = to_k(wphk_ks_d['损益金额'].sum())
    wphk_rh1_v = to_k(wphk_rh1['损益金额'].sum())
    rh3_v = to_k(rh3['损益金额'].sum())
    
    print(f"    WPHK跨境收单+融合一期: {wphk_ks_v2 + wphk_rh1_v}")
    print(f"    WPHK跨境收单+融合一期+融合三期: {wphk_ks_v2 + wphk_rh1_v + rh3_v}")
    
    # 也可能是 产品类型=跨境收单 的全部
    all_ks_prod = df[df['产品类型'] == '跨境收单']
    print(f"    产品类型=跨境收单(全部): {to_k(all_ks_prod['损益金额'].sum())}")
    
    # 按渠道看
    ks_by_entity = all_ks_prod.groupby('损益实际归属主体')['损益金额'].sum()
    for k, v in ks_by_entity.items():
        print(f"      {k}: {to_k(v)}")
    
    # === WXG侧 ===
    print(f"\n  [WXG侧损益] 截图={screenshot['WXG侧损益'][m_idx]}")
    # 可能 = 其中WX 的全部?
    total_wx = to_k(df['其中WX'].sum())
    print(f"    其中WX(全部): {total_wx}")
    
    # 全量
    total_all = to_k(df['损益金额'].sum())
    total_fit = to_k(df['FIT'].sum())
    print(f"    损益总计: {total_all}")
    print(f"    FIT总计: {total_fit}")
    
    # WXG = 全量 - FIT侧?
    # WXG + FIT = 全量?
    print(f"    WXG截图 + FIT截图 = {screenshot['WXG侧损益'][m_idx] + screenshot['FIT侧损益'][m_idx]}")
    print(f"    损益总计: {total_all}")
    
    # === FIT侧 ===
    print(f"\n  [FIT侧损益] 截图={screenshot['FIT侧损益'][m_idx]}")
    print(f"    FIT总计: {total_fit}")
    
    # CFT的全部就是FIT?
    cft = df[df['损益实际归属主体'] == 'CFT']
    cft_v = to_k(cft['损益金额'].sum())
    print(f"    CFT(全部): {cft_v}")
    
    # 也许FIT侧 = CFT + 部分MSO/MPI?
    # 截图1月 FIT=-1521, CFT=-3342
    # 差 = -1521 - (-3342) = 1821
    print(f"    差额(FIT截图 - CFT): {screenshot['FIT侧损益'][m_idx] - cft_v}")

print()
print("=" * 90)
print("第四步: 尝试新的分类假设")
print("=" * 90)

# 假设: 截图的分类是基于一个业务侧口径表
# "跨境收单" → MSO跨境收单(损益户) + MSO融合三期(损益户)
# "汇款互联" → MSO互联汇款(损益户) + MPI互联汇款(损益户)
# "留学缴费" → 留学缴费(损益户) + 留学锁价商户
# "企业外汇-境内购汇" → 出境机酒(损益户) + MSO平台换汇(损益户) + MSO平台收款(损益户) + 机酒锁价
# "企业外汇-境外账户" → ??? 
# "企业外汇-基础通道" → 纯汇兑(固收户)

for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n{'='*30} {label} {'='*30}")
    
    # 跨境收单(截图) = ?
    # 1月: 截图1173, 原始 MSO跨境收单=1847
    # 试试: MSO跨境收单 + 融合三期 = 1847 + (-3376) = -1529 → 不对
    # 试试只看 所属业务=跨境收单 且 产品类型=跨境收单 且 渠道=MSO 且 商户类型=损益户
    
    # 等等, 让我看看有没有其他字段
    print(f"\n  所有列名: {list(df.columns)}")
    break

print()
print("=" * 90)
print("第五步: 检查其他可能有用的列")
print("=" * 90)
# 显示所有列
for col in df1.columns:
    sample = df1[col].dropna().unique()[:5]
    print(f"  {col}: {sample}")
