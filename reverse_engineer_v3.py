# -*- coding: utf-8 -*-
"""Reverse engineer v3: 精确匹配 — 关注FIT列分拆"""
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

def to_k(v):
    return round(v / 1000)

# 截图值 (千元)
S = {
    '跨境收单':           (1173, 703),
    '汇款互联':           (532, 534),
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
print("关键发现: 截图可能是看FIT列而不是损益列!")
print("=" * 90)

for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n{'='*40} {label} {'='*40}")
    
    # ============ 看FIT列 ============
    # 业务侧的分类可能基于FIT而不是损益金额
    
    # 跨境收单
    # MSO 跨境收单 FIT
    mso_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'MSO') & (df['商户类型'] == '损益户')]
    print(f"\n  [跨境收单] 截图={S['跨境收单'][m_idx]}")
    print(f"    MSO跨境收单(损益户) 损益={to_k(mso_ks['损益金额'].sum())} FIT={to_k(mso_ks['FIT'].sum())}")
    
    # 跨境收单 全渠道 损益户
    all_ks = df[(df['所属业务'] == '跨境收单') & (df['商户类型'] == '损益户')]
    print(f"    全渠道跨境收单(损益户) 损益={to_k(all_ks['损益金额'].sum())} FIT={to_k(all_ks['FIT'].sum())}")
    
    # 产品类型=跨境收单 损益户
    prod_ks = df[(df['产品类型'] == '跨境收单') & (df['商户类型'] == '损益户')]
    print(f"    产品类型=跨境收单(损益户) 损益={to_k(prod_ks['损益金额'].sum())} FIT={to_k(prod_ks['FIT'].sum())}")
    
    # MSO 产品=跨境收单
    mso_prod_ks = df[(df['产品类型'] == '跨境收单') & (df['损益实际归属主体'] == 'MSO') & (df['商户类型'] == '损益户')]
    print(f"    MSO产品=跨境收单(损益户) 损益={to_k(mso_prod_ks['损益金额'].sum())} FIT={to_k(mso_prod_ks['FIT'].sum())}")
    
    # MSO+CFT 跨境收单(损益户)
    mso_cft_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'].isin(['MSO', 'CFT'])) & (df['商户类型'] == '损益户')]
    print(f"    MSO+CFT跨境收单(损益户) 损益={to_k(mso_cft_ks['损益金额'].sum())} FIT={to_k(mso_cft_ks['FIT'].sum())}")
    
    # MSO跨境收单 + 融合三期 (但只有MSO的)
    mso_rh3 = df[(df['所属业务'] == '融合三期') & (df['损益实际归属主体'] == 'MSO')]
    print(f"    MSO融合三期 损益={to_k(mso_rh3['损益金额'].sum())} FIT={to_k(mso_rh3['FIT'].sum())}")
    
    # ============ 互联汇款 ============
    print(f"\n  [汇款互联] 截图={S['汇款互联'][m_idx]}")
    hl = df[df['所属业务'] == '互联汇款']
    hl_pnl = df[(df['所属业务'] == '互联汇款') & (df['商户类型'] == '损益户')]
    print(f"    互联汇款(全部) 损益={to_k(hl['损益金额'].sum())} FIT={to_k(hl['FIT'].sum())}")
    print(f"    互联汇款(损益户) 损益={to_k(hl_pnl['损益金额'].sum())} FIT={to_k(hl_pnl['FIT'].sum())}")
    
    # ============ 留学 ============
    print(f"\n  [留学缴费] 截图={S['留学缴费'][m_idx]}")
    lx = df[df['所属业务'] == '留学缴费']
    lx_lock = df[df['所属业务'] == '留学锁价商户']
    print(f"    留学缴费 损益={to_k(lx['损益金额'].sum())} FIT={to_k(lx['FIT'].sum())}")
    print(f"    留学锁价 损益={to_k(lx_lock['损益金额'].sum())} FIT={to_k(lx_lock['FIT'].sum())}")
    print(f"    留学+锁价 损益={to_k(lx['损益金额'].sum()+lx_lock['损益金额'].sum())} FIT={to_k(lx['FIT'].sum()+lx_lock['FIT'].sum())}")
    
    # ============ 企业外汇 ============
    print(f"\n  [企业外汇-境内购汇] 截图={S['企业外汇-境内购汇'][m_idx]}")
    # 出境机酒
    cj = df[df['所属业务'] == '出境机酒']
    cj_lock = df[df['所属业务'] == '机酒周末锁价商户']
    # MSO换汇
    mso_hh = df[(df['所属业务'] == 'MSO平台') & (df['产品类型'] == '换汇平台') & (df['商户类型'] == '损益户')]
    mso_sk = df[(df['所属业务'] == 'MSO平台') & (df['产品类型'] == '收款业务') & (df['商户类型'] == '损益户')]
    
    cj_fit = to_k(cj['FIT'].sum())
    mso_hh_fit = to_k(mso_hh['FIT'].sum())
    mso_sk_fit = to_k(mso_sk['FIT'].sum())
    
    print(f"    出境机酒 损益={to_k(cj['损益金额'].sum())} FIT={cj_fit}")
    print(f"    MSO换汇(损益户) 损益={to_k(mso_hh['损益金额'].sum())} FIT={mso_hh_fit}")
    print(f"    MSO收款(损益户) 损益={to_k(mso_sk['损益金额'].sum())} FIT={mso_sk_fit}")
    print(f"    机酒+换汇+收款 FIT={cj_fit + mso_hh_fit + mso_sk_fit}")
    print(f"    机酒+换汇 FIT={cj_fit + mso_hh_fit}")
    
    # 产品类型=企业外汇-出境
    prod_cj = df[df['产品类型'] == '企业外汇-出境']
    print(f"    产品=企业外汇-出境 损益={to_k(prod_cj['损益金额'].sum())} FIT={to_k(prod_cj['FIT'].sum())}")
    # 产品类型=企业外汇-境内购汇 (可能不存在这个值?)
    prod_gw = df[df['产品类型'] == '企业外汇-境内购汇']
    if len(prod_gw) > 0:
        print(f"    产品=企业外汇-境内购汇 损益={to_k(prod_gw['损益金额'].sum())} FIT={to_k(prod_gw['FIT'].sum())}")
    else:
        print(f"    (无'企业外汇-境内购汇'产品类型)")
    
    print(f"\n  [企业外汇-境外账户] 截图={S['企业外汇-境外账户'][m_idx]}")
    prod_jw = df[df['产品类型'] == '企业外汇-境外账户']
    if len(prod_jw) > 0:
        print(f"    产品=企业外汇-境外账户 损益={to_k(prod_jw['损益金额'].sum())} FIT={to_k(prod_jw['FIT'].sum())}")
    else:
        print(f"    (无此产品类型)")
    # SVF平台可能就是境外账户?
    svf = df[df['所属业务'] == 'SVF平台']
    svf_pnl = df[(df['所属业务'] == 'SVF平台') & (df['商户类型'] == '损益户')]
    print(f"    SVF平台(全) 损益={to_k(svf['损益金额'].sum())} FIT={to_k(svf['FIT'].sum())}")
    print(f"    SVF平台(损益户) 损益={to_k(svf_pnl['损益金额'].sum())} FIT={to_k(svf_pnl['FIT'].sum())}")
    
    # 也许 "境外账户" 对应 MSO平台 的某个子集？
    # 截图1月=443, 看MSO平台按产品
    mso = df[df['所属业务'] == 'MSO平台']
    mso_by_prod = mso.groupby(['产品类型','商户类型']).agg(
        损益=('损益金额','sum'), FIT=('FIT','sum'), 行数=('损益金额','count')
    )
    print(f"    MSO平台明细:")
    for (pt, mt), row in mso_by_prod.iterrows():
        print(f"      {pt}({mt}): 损益={to_k(row['损益'])} FIT={to_k(row['FIT'])} ({row['行数']}行)")
    
    # MSO收款(损益户) = 300(1月), 127(2月) → 截图境外=443, 226 → 不match
    # MSO互联收单(损益户)?
    mso_hlsd = df[(df['所属业务'] == 'MSO平台') & (df['产品类型'] == '互联收单')]
    print(f"    MSO互联收单 损益={to_k(mso_hlsd['损益金额'].sum())} FIT={to_k(mso_hlsd['FIT'].sum())}")
    
    print(f"\n  [企业外汇-基础通道] 截图={S['企业外汇-基础通道'][m_idx]}")
    chun = df[df['所属业务'] == '纯汇兑']
    print(f"    纯汇兑 损益={to_k(chun['损益金额'].sum())} FIT={to_k(chun['FIT'].sum())}")
    
    # ============ 业务侧重新算 ============
    print(f"\n  [业务侧小计] 截图={S['业务侧小计'][m_idx]}")
    # 假设: 跨境收单截图值 可能 = MSO跨境收单(损益户) - CFT跨境收单(损益户)?
    # 1月: 1847 - (-927) = 2774 → 不对
    # 假设: 截图的跨境收单 = 业务侧小计 - 汇款互联 - 留学缴费 - 企业外汇小计
    implied_ks = S['业务侧小计'][m_idx] - S['汇款互联'][m_idx] - S['留学缴费'][m_idx] - S['企业外汇小计'][m_idx]
    print(f"    推算跨境收单 = 业务侧 - 互联 - 留学 - 企业 = {implied_ks} (截图:{S['跨境收单'][m_idx]}) → {'✓' if implied_ks == S['跨境收单'][m_idx] else '✗'}")
    # 2月: 5184-534-169-4481 = 0 ≠ 703
    
    # 也许截图中还有一行"出境机酒"没写出来?
    # 1月: 1173+532+0+503+4603 = 6811, 业务侧=5777, 差=-1034
    # 是否有一行负值没显示? 如 "出境机酒" = -1034?
    # 但出境机酒=3039... 不对
    
    # 看看 FIT 列
    print(f"\n  === 用 FIT 列重算 ===")
    
    # MSO跨境收单 FIT
    v1 = to_k(mso_ks['FIT'].sum()) if len(mso_ks) > 0 else 0
    # 互联汇款 FIT
    v2 = to_k(hl['FIT'].sum())
    # 留学+锁价 FIT
    v3 = to_k(lx['FIT'].sum() + lx_lock['FIT'].sum())
    # 出境机酒 FIT + MSO换汇+收款 FIT + 纯汇兑 FIT
    v4_gw = to_k(cj['FIT'].sum() + mso_hh['FIT'].sum() + mso_sk['FIT'].sum())
    v4_jw = to_k(svf_pnl['FIT'].sum()) if len(svf_pnl) > 0 else 0
    v4_base = to_k(chun['FIT'].sum())
    v4 = v4_gw + v4_jw + v4_base
    
    biz_fit = v1 + v2 + v3 + v4
    print(f"    跨境收单FIT: {v1}")
    print(f"    互联FIT: {v2}")
    print(f"    留学FIT: {v3}")
    print(f"    企业(境内FIT={v4_gw} + 境外FIT={v4_jw} + 基础FIT={v4_base}): {v4}")
    print(f"    业务侧FIT合计: {biz_fit} (截图:{S['业务侧小计'][m_idx]})")
    
    # ============ 用损益列和FIT列分别看看总量匹配 ============
    total_pnl = to_k(df['损益金额'].sum())
    total_fit = to_k(df['FIT'].sum())
    total_wx = to_k(df['其中WX'].sum())
    
    print(f"\n  === 总量 ===")
    print(f"    损益总计={total_pnl} FIT总计={total_fit} WX总计={total_wx}")
    print(f"    截图: 税后={S['税后汇兑损益'][m_idx]} WXG={S['WXG侧损益'][m_idx]} FIT侧={S['FIT侧损益'][m_idx]}")
    print(f"    WXG+FIT = {S['WXG侧损益'][m_idx] + S['FIT侧损益'][m_idx]}")
    
    # 也许截图的 "WXG侧" 和 "FIT侧" 不是 WX 和 FIT，
    # 而是按"归属主体"分？WXG=WPHK相关, FIT=CFT相关?

    # CFT-WPHK 全部
    wphk_all = df[df['损益实际归属主体'] == 'CFT-WPHK']
    cft_all = df[df['损益实际归属主体'] == 'CFT']
    mso_all = df[df['损益实际归属主体'] == 'MSO']
    mpi_all = df[df['损益实际归属主体'] == 'MPI']
    
    print(f"\n  === 按渠道(归属主体)损益 ===")
    print(f"    CFT-WPHK: 损益={to_k(wphk_all['损益金额'].sum())} FIT={to_k(wphk_all['FIT'].sum())} WX={to_k(wphk_all['其中WX'].sum())}")
    print(f"    CFT:      损益={to_k(cft_all['损益金额'].sum())} FIT={to_k(cft_all['FIT'].sum())} WX={to_k(cft_all['其中WX'].sum())}")
    print(f"    MSO:      损益={to_k(mso_all['损益金额'].sum())} FIT={to_k(mso_all['FIT'].sum())} WX={to_k(mso_all['其中WX'].sum())}")
    print(f"    MPI:      损益={to_k(mpi_all['损益金额'].sum())} FIT={to_k(mpi_all['FIT'].sum())} WX={to_k(mpi_all['其中WX'].sum())}")
    
    # 试: WXG = WPHK + MSO + MPI (不含CFT)?
    no_cft = to_k((wphk_all['损益金额'].sum() + mso_all['损益金额'].sum() + mpi_all['损益金额'].sum()))
    print(f"    WPHK+MSO+MPI: {no_cft}")
    
    # 试: WXG = 全量 - CFT?
    excl_cft = total_pnl - to_k(cft_all['损益金额'].sum())
    print(f"    全量-CFT: {excl_cft}")

print()
print("=" * 90)
print("第六步: 万元级匹配 (截图值是万元?)")
print("=" * 90)

# 等等，用户说 "1,173 是1173万的意思"
# 但 "15076这里应该是15,076,000应该是1507 万"
# 所以截图值的单位是 万元！
# 那 CSV 数据要除以 10000 (万元) 来比较

for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n{'='*40} {label} {'='*40}")
    
    def to_w(v):
        """元 → 万元"""
        return round(v / 10000)
    
    # 跨境收单
    mso_ks = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'MSO') & (df['商户类型'] == '损益户')]
    all_ks_pnl = df[(df['所属业务'] == '跨境收单') & (df['商户类型'] == '损益户')]
    print(f"\n  [跨境收单] 截图={S['跨境收单'][m_idx]}")
    print(f"    MSO跨境收单(损益户): {to_w(mso_ks['损益金额'].sum())}")
    print(f"    全渠道跨境收单(损益户): {to_w(all_ks_pnl['损益金额'].sum())}")
    
    # 互联汇款
    hl = df[df['所属业务'] == '互联汇款']
    print(f"\n  [汇款互联] 截图={S['汇款互联'][m_idx]}")
    print(f"    互联汇款: {to_w(hl['损益金额'].sum())}")
    
    # 留学缴费
    lx = df[df['所属业务'] == '留学缴费']
    lx_lock = df[df['所属业务'] == '留学锁价商户']
    print(f"\n  [留学缴费] 截图={S['留学缴费'][m_idx]}")
    print(f"    留学缴费: {to_w(lx['损益金额'].sum())}")
    print(f"    留学+锁价: {to_w(lx['损益金额'].sum()+lx_lock['损益金额'].sum())}")
    
    # 出境机酒
    cj = df[df['所属业务'] == '出境机酒']
    cj_lock = df[df['所属业务'] == '机酒周末锁价商户']
    print(f"\n  [出境机酒]")
    print(f"    出境机酒: {to_w(cj['损益金额'].sum())}")
    
    # 企业外汇
    mso_hh = df[(df['所属业务'] == 'MSO平台') & (df['产品类型'] == '换汇平台') & (df['商户类型'] == '损益户')]
    mso_sk = df[(df['所属业务'] == 'MSO平台') & (df['产品类型'] == '收款业务') & (df['商户类型'] == '损益户')]
    chun = df[df['所属业务'] == '纯汇兑']
    svf_pnl = df[(df['所属业务'] == 'SVF平台') & (df['商户类型'] == '损益户')]
    
    print(f"\n  [企业外汇子项]")
    print(f"    MSO换汇(损益户): {to_w(mso_hh['损益金额'].sum())}")
    print(f"    MSO收款(损益户): {to_w(mso_sk['损益金额'].sum())}")
    print(f"    出境机酒: {to_w(cj['损益金额'].sum())}")
    print(f"    出境+换汇+收款: {to_w(cj['损益金额'].sum()+mso_hh['损益金额'].sum()+mso_sk['损益金额'].sum())}")
    print(f"    纯汇兑: {to_w(chun['损益金额'].sum())}")
    print(f"    SVF(损益户): {to_w(svf_pnl['损益金额'].sum())}")
    
    # 截图境内购汇=3738(1月)
    # 出境+换汇+收款 = 3039+2257+300 = 5596(千元) = 560(万元) ≠ 3738
    # 嗯... 
    
    # 等等, 我再看看截图单位
    # 用户说 "1,173 是1173万的意思"  
    # 然后 "15076这里应该是15,076,000应该是1507万"
    # 所以 15076(千元) = 1507(万元)？ 那说明截图是千元！
    # 因为 15076千元 ÷ 10 = 1507万元... 不对
    # 15,076,000 / 10000 = 1507.6 万 → 约 1508万
    # 但用户说 "应该是1507万"
    # 所以 15076 应该是 15076 千元 = 15,076,000 元 = 1507.6 万
    # 截图中的值就是 千元
    # 而用户说 "1,173是1173万" → 1173千元 = 117.3万？ 不对
    # 还是 1,173 代表 1,173万 = 11730千元 = 11,730,000元?
    
    # 让我重新理解: 截图上写的是 千元 单位
    # 但用户口误说成 "万"? 不, 用户说的是:
    # "1,173 是1173万的意思" → 可能截图单位是 万元!
    # "15076这里应该是15,076,000应该是1507 万" → 15076千元=15076000元=1507.6万
    
    # 所以截图单位确实是千元, 用户说"万"时是转换了下
    
    print(f"\n  === 综合对比(千元) ===")
    # 回到千元
    ks_all_pnl = to_k(all_ks_pnl['损益金额'].sum())
    hl_v = to_k(hl['损益金额'].sum())
    lx_v = to_k((lx['损益金额'].sum()+lx_lock['损益金额'].sum()))
    cj_v = to_k(cj['损益金额'].sum())
    
    print(f"    跨境收单(全渠道损益户): {ks_all_pnl} 截图:{S['跨境收单'][m_idx]} 差:{ks_all_pnl - S['跨境收单'][m_idx]}")
    print(f"    互联汇款: {hl_v} 截图:{S['汇款互联'][m_idx]} 差:{hl_v - S['汇款互联'][m_idx]}")
    print(f"    留学(含锁价): {lx_v} 截图:{S['留学缴费'][m_idx]} 差:{lx_v - S['留学缴费'][m_idx]}")

    # 1月: 跨境收单 15076 vs 截图1173, 差 13903
    # 13903千元 → 接近 WPHK跨境收单 14156!
    # 15076 - 14156 = 920  → 接近MSO跨境收单1847-920 = 927 = CFT跨境收单的绝对值!
    # 即: 截图跨境收单 = MSO跨境收单(1847) + CFT跨境收单(-927) + MSO融合三期(74) + WPHK融合三期(-1035)??
    # = 1847 - 927 + 74 - 1035 = -41... 不对
    
    # 让我重新拆:
    # 截图跨境收单(1月) = 1173
    # MSO跨境收单(损益户) = 1847, CFT跨境收单(损益户) = -927
    # 1847 + (-927) = 920 → 不是1173
    
    # 再试: 排除WPHK, MSO+CFT跨境收单 = 920, 加上融合三期中MSO的=74 → 994
    # 加上WPHK融合一期? 不，那太大了
    
    # 会不会截图中的"跨境收单"是按产品类型分的，但只含 MSO 渠道?
    # MSO产品=跨境收单 = 1847+74=1921 (含融合三期) → 不是1173

    # 或者: MSO跨境收单(1847) + CFT跨境收单(-927) + 某些调整 = 1173?
    # 差值 = 1173 - 920 = 253... 

    # 拆更细
    print(f"\n  === 跨境收单详细拆解 ===")
    ks_detail = df[df['所属业务'] == '跨境收单'].groupby(['损益实际归属主体','商户类型'])[['损益金额','FIT','其中WX']].sum()
    for (entity, mt), row in ks_detail.iterrows():
        print(f"    {entity}({mt}): 损益={to_k(row['损益金额'])} FIT={to_k(row['FIT'])} WX={to_k(row['其中WX'])}")
    
    rh1_detail = df[df['所属业务'] == '融合一期'].groupby(['损益实际归属主体','商户类型'])[['损益金额','FIT','其中WX']].sum()
    for (entity, mt), row in rh1_detail.iterrows():
        print(f"    融合一期-{entity}({mt}): 损益={to_k(row['损益金额'])} FIT={to_k(row['FIT'])} WX={to_k(row['其中WX'])}")
    
    rh3_detail = df[df['所属业务'] == '融合三期'].groupby(['损益实际归属主体','商户类型'])[['损益金额','FIT','其中WX']].sum()
    for (entity, mt), row in rh3_detail.iterrows():
        print(f"    融合三期-{entity}({mt}): 损益={to_k(row['损益金额'])} FIT={to_k(row['FIT'])} WX={to_k(row['其中WX'])}")
    
    # 也许截图中的口径完全不同
    # 截图"跨境收单" = MSO收款业务(损益户) + MSO互联收单 + ... ?
    # MSO收款=300, 截图=1173... 不match

    # 我觉得可能截图采用了"不含CFT-WPHK跨境收单(单独归入'跨境收单损益')"的逻辑
    # 也就是: 
    #   业务侧跨境收单 = MSO跨境收单 + CFT跨境收单 (排除WPHK跨境收单)
    #   跨境收单损益 = WPHK跨境收单 + 融合一期 + 融合三期
    
    mso_cft_ks_val = df[(df['所属业务'] == '跨境收单') & (df['损益实际归属主体'].isin(['MSO','CFT']))]['损益金额'].sum()
    wphk_rh_val = df[((df['所属业务'] == '跨境收单') & (df['损益实际归属主体'] == 'CFT-WPHK')) |
                     (df['所属业务'].isin(['融合一期','融合三期']))]['损益金额'].sum()
    
    print(f"\n    MSO+CFT跨境收单: {to_k(mso_cft_ks_val)}")
    print(f"    WPHK跨境收单+融合一期+融合三期: {to_k(wphk_rh_val)}")

print()
print("=" * 90)
print("第七步: 穷举组合搜索匹配 截图'跨境收单'=1173(1月)")
print("=" * 90)

# 1月数据, 所有(业务×渠道×商户类型)组合的损益值
combos = df1.groupby(['损益实际归属主体', '所属业务', '商户类型'])['损益金额'].sum().reset_index()
combos['千元'] = combos['损益金额'].apply(to_k)
vals = list(zip(combos.index, combos['千元']))

# 找出哪些组合加起来=1173
target = S['跨境收单'][0]  # 1173
print(f"寻找组合: 和={target}")
print(f"可用的组合(|千元|>=1):")
for _, row in combos.iterrows():
    if abs(row['千元']) >= 1:
        label = f"{row['损益实际归属主体']}/{row['所属业务']}/{row['商户类型']}"
        print(f"  {label:45s} = {row['千元']:>8,}")

# 暴力搜索(最多3项组合)
items = combos[combos['千元'].abs() >= 1].reset_index(drop=True)
n = len(items)
print(f"\n搜索{n}个非零项的组合(<=3项)...")

found = []
for i in range(n):
    if items.loc[i, '千元'] == target:
        found.append([i])
    for j in range(i+1, n):
        s2 = items.loc[i,'千元'] + items.loc[j,'千元']
        if s2 == target:
            found.append([i,j])
        for k in range(j+1, n):
            s3 = s2 + items.loc[k,'千元']
            if s3 == target:
                found.append([i,j,k])

print(f"\n找到 {len(found)} 种组合:")
for combo in found[:20]:  # 最多显示20个
    parts = []
    for idx in combo:
        row = items.loc[idx]
        parts.append(f"{row['损益实际归属主体']}/{row['所属业务']}/{row['商户类型']}={row['千元']}")
    print(f"  {' + '.join(parts)}")

# 同样搜索 业务侧=5777
print(f"\n\n搜索 业务侧={S['业务侧小计'][0]}:")
target2 = S['业务侧小计'][0]
# 先看看几个大项能不能凑出来
# MSO损益户(不含SVF/融合) + 纯汇兑 + MPI
mso_no_svf = df1[(df1['损益实际归属主体'].isin(['MSO','MPI'])) & (df1['商户类型'] == '损益户')]
mso_biz_names = mso_no_svf['所属业务'].unique()
print(f"  MSO+MPI 损益户的业务: {mso_biz_names}")
for biz in mso_biz_names:
    sub = mso_no_svf[mso_no_svf['所属业务'] == biz]
    print(f"    {biz}: {to_k(sub['损益金额'].sum())}")
print(f"  MSO+MPI损益户合计: {to_k(mso_no_svf['损益金额'].sum())}")
# 加上纯汇兑(固收户)
chun1 = df1[df1['所属业务'] == '纯汇兑']
print(f"  纯汇兑: {to_k(chun1['损益金额'].sum())}")
print(f"  MSO+MPI损益户 + 纯汇兑: {to_k(mso_no_svf['损益金额'].sum() + chun1['损益金额'].sum())}")
