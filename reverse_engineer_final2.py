# -*- coding: utf-8 -*-
"""Reverse engineer FINAL2: 基于已验证关系推导完整映射"""
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

def K(v): return round(v / 1000)

# 截图 (千元) — 纠正后
S = {
    '跨境汇款': (1173, 703), '汇款互联': (532, 534), '港陆汇款': (0, 0),
    '留学缴费': (641, 169),
    '企业外汇': (4603, 4481), '境内账户服务': (3738, 4063),
    '境外账户服务': (443, 226), '基础通道服务': (423, 192),
    '业务侧小计': (5777, 5184),
    '平台侧': (-1300, 10824),
    '税后': (4477, 16008),
    '跨境收单损益': (17744, -24274),
    'WXG': (20766, -33462),
    'FIT侧': (-3023, 9188),
    '平台不含FiT': (1723, 1636),
}

print("=" * 90)
print("已验证的恒等式:")
print("  ✅ 税后 = 业务侧 + 平台侧")
print("  ✅ 平台侧 = 平台不含FiT + FIT侧")  
print("  ✅ WXG + FIT侧 = 跨境收单损益 (差≤1)")
print("  ✅ 截图单位 = 千元 (表头明确写了)")
print("=" * 90)

# =======================================================
# 从恒等式推导报表结构:
# 
# 全局 = 税后 + 跨境收单损益   (?)
#       = 业务侧 + 平台侧 + 跨境收单损益
#       = 业务侧 + (平台不含FiT + FIT侧) + 跨境收单损益
#       = 业务侧 + 平台不含FiT + (WXG + FIT侧)  ← 因为WXG+FIT=跨境收单损益
# 
# 但注意: 截图说 "FIT侧损益(已包含在平台侧汇兑)"
# 所以 FIT侧 是 平台侧 的子集, 不是加在上面的!
# 
# 真正的结构:
# 税后 = 业务侧 + 平台侧 (其中平台侧 = 平台不含FiT + FIT侧)
# 跨境收单损益 = WXG + FIT侧 (这个FIT侧和平台侧中的FIT侧是同一个数!)
# 
# 所以整个报表的全量 = 税后 + 跨境收单损益 - FIT侧 (避免重复计算?)
# 不... 让我重新想
# 
# 也许结构是:
# 总损益 = 汇兑损益(税后) + 跨境收单损益
# 
# 其中:
#   汇兑损益(税后) = 业务侧 + 平台侧
#   跨境收单损益 是另一块独立的
#   WXG = 汇兑(税后) + 跨境收单损益 中归属WXG部门的部分
#   FIT侧 = 归属FIT部门的部分 (同时出现在平台侧和跨境收单损益中)
# =======================================================

print("\n" + "=" * 90)
print("结构推导: 全量 = 税后 + 跨境收单损益")
print("=" * 90)

for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    total_csv = K(df['损益金额'].sum())
    total_report = S['税后'][m_idx] + S['跨境收单损益'][m_idx]
    
    print(f"\n{label}:")
    print(f"  CSV全量: {total_csv}")
    print(f"  税后+跨境收单损益: {S['税后'][m_idx]} + {S['跨境收单损益'][m_idx]} = {total_report}")
    print(f"  差: {total_csv - total_report}")
    # 1月: 25566 vs 22221, 差3345
    # 说明 CSV全量 ≠ 税后+跨境收单损益
    # 多出来的3345可能是SVF?

    # SVF
    svf = K(df[df['所属业务'] == 'SVF平台']['损益金额'].sum())
    print(f"  SVF平台: {svf}")
    print(f"  全量 - SVF = {total_csv - svf}")
    print(f"  全量 - SVF vs 报表: 差{total_csv - svf - total_report}")
    # 1月: 25566 - 5407 = 20159 vs 22221 → 差-2062
    # 还是不对

# =======================================================
# 换个思路: 按渠道分拆
# =======================================================

print("\n" + "=" * 90)
print("按渠道分拆对比")
print("=" * 90)

for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n{'='*40} {label} {'='*40}")
    
    # 按渠道×业务 列出所有
    detail = df.groupby(['损益实际归属主体', '所属业务'])[['损益金额', 'FIT', '其中WX']].sum()
    
    wphk_total = K(df[df['损益实际归属主体'] == 'CFT-WPHK']['损益金额'].sum())
    cft_total = K(df[df['损益实际归属主体'] == 'CFT']['损益金额'].sum())
    mso_total = K(df[df['损益实际归属主体'] == 'MSO']['损益金额'].sum())
    mpi_total = K(df[df['损益实际归属主体'] == 'MPI']['损益金额'].sum())
    
    print(f"  WPHK: {wphk_total}")
    print(f"  CFT:  {cft_total}")
    print(f"  MSO:  {mso_total}")
    print(f"  MPI:  {mpi_total}")
    print(f"  合计: {wphk_total + cft_total + mso_total + mpi_total}")
    
    # 截图 WXG侧 vs CFT-WPHK+MSO+MPI (不含CFT)?
    no_cft = wphk_total + mso_total + mpi_total
    print(f"\n  WPHK+MSO+MPI(不含CFT): {no_cft} (WXG截图:{S['WXG'][m_idx]})")
    # 1月: 28909 vs 20766 → 不match
    
    # WPHK 按业务拆
    print(f"\n  WPHK 按业务:")
    wphk = df[df['损益实际归属主体'] == 'CFT-WPHK']
    for biz in sorted(wphk['所属业务'].unique()):
        sub = wphk[wphk['所属业务'] == biz]
        print(f"    {biz:15s}: {K(sub['损益金额'].sum()):>7,}")
    
    # CFT 按业务拆
    print(f"\n  CFT 按业务:")
    cft = df[df['损益实际归属主体'] == 'CFT']
    for biz in sorted(cft['所属业务'].unique()):
        sub = cft[cft['所属业务'] == biz]
        print(f"    {biz:15s}: {K(sub['损益金额'].sum()):>7,}")

# =======================================================
# 关键突破口: 截图留学=641, CSV留学=661, 差20
# 也许截图排除了某些币种的留学?
# =======================================================

print("\n" + "=" * 90)
print("留学缴费差异分析: CSV=661 vs 截图=641 (1月)")
print("=" * 90)

for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n--- {label} ---")
    lx = df[df['所属业务'] == '留学缴费']
    print(f"  CSV留学缴费: {K(lx['损益金额'].sum())} (截图:{S['留学缴费'][m_idx]})")
    print(f"  差: {K(lx['损益金额'].sum()) - S['留学缴费'][m_idx]}")
    
    # 按币种拆
    lx_by_ccy = lx.groupby('原币种')['损益金额'].sum().sort_values(ascending=False)
    cum = 0
    for ccy, v in lx_by_ccy.items():
        vk = K(v)
        cum += vk
        if abs(vk) >= 1:
            print(f"    {ccy:5s}: {vk:>6,}  累计:{cum:>7,}")
    
    # 1月差20千 → 看看哪些币种可以凑出20
    # 也许排除了CNY?
    lx_no_cny = lx[lx['原币种'] != 'CNY']
    print(f"  留学(不含CNY): {K(lx_no_cny['损益金额'].sum())}")
    
    # 看看有没有垫资
    lx_dz = lx[(lx['期初垫资余额'] != 0) | (lx['期末垫资余额'] != 0)]
    lx_no_dz = lx[(lx['期初垫资余额'] == 0) & (lx['期末垫资余额'] == 0)]
    print(f"  留学(有垫资): {K(lx_dz['损益金额'].sum())} ({len(lx_dz)}行)")
    print(f"  留学(无垫资): {K(lx_no_dz['损益金额'].sum())} ({len(lx_no_dz)}行)")
    
    # 看渠道
    print(f"  留学按渠道:")
    lx_by_entity = lx.groupby('损益实际归属主体')['损益金额'].sum()
    for e, v in lx_by_entity.items():
        print(f"    {e}: {K(v)}")
    # 留学只有MSO渠道

print("\n" + "=" * 90)
print("所有业务的CSV千元 vs 截图千元")
print("=" * 90)

# 整理CSV中所有业务的值(千元), 并跟截图每一行做对比
for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n{'='*40} {label} {'='*40}")
    
    by_biz = df.groupby('所属业务')['损益金额'].sum().sort_values(ascending=False)
    print(f"\n  CSV按所属业务(千元):")
    for biz, v in by_biz.items():
        vk = K(v)
        if abs(vk) >= 1:
            print(f"    {biz:20s}: {vk:>7,}")
    
    # 截图中没有的业务: SVF平台, 融合一期, 融合三期, 出境机酒, MSO平台
    # 这些是否被归入了截图的某些行中?
    
    svf = K(df[df['所属业务'] == 'SVF平台']['损益金额'].sum())
    rh1 = K(df[df['所属业务'] == '融合一期']['损益金额'].sum())
    rh3 = K(df[df['所属业务'] == '融合三期']['损益金额'].sum())
    cj = K(df[df['所属业务'] == '出境机酒']['损益金额'].sum())
    mso = K(df[df['所属业务'] == 'MSO平台']['损益金额'].sum())
    lx_lock = K(df[df['所属业务'] == '留学锁价商户']['损益金额'].sum())
    
    print(f"\n  截图中缺失的业务:")
    print(f"    SVF平台:    {svf:>7,}")
    print(f"    融合一期:    {rh1:>7,}")
    print(f"    融合三期:    {rh3:>7,}")
    print(f"    出境机酒:    {cj:>7,}")
    print(f"    MSO平台:    {mso:>7,}")
    print(f"    留学锁价:    {lx_lock:>7,}")
    print(f"    小计:       {svf+rh1+rh3+cj+mso+lx_lock:>7,}")
    
    # 截图行 vs CSV业务 的可能映射:
    # 截图"跨境汇款" ← CSV跨境收单的某个子集
    # 截图"境内账户服务" ← CSV出境机酒 + MSO平台的某个子集?
    # 截图"境外账户服务" ← SVF平台的某个子集?
    
    # 如果 境内 = 出境机酒 + MSO平台的换汇+收款 (但这加起来5596≠3738)
    # 或者 境内 = 出境机酒 + 留学缴费? (3039+661=3700≈3738, 差38!!)
    # 等等!!! 出境机酒(3039) + 留学(661) = 3700 → 截图3738, 差38
    # 接近但不精确
    
    # 但截图里"留学缴费"单独是一行641...
    # 如果 留学缴费 同时出现在两个地方, 不太合理
    
    # 试另一个: 境内 = 出境机酒 + MSO收款?
    # 3039+300=3339, 差399
    
    # 试: 境内 = 出境机酒 + MSO换汇(损益户) + 融合一期部分?
    mso_hh = K(df[(df['所属业务'] == 'MSO平台') & (df['产品类型'] == '换汇平台') & (df['商户类型'] == '损益户')]['损益金额'].sum())
    mso_sk = K(df[(df['所属业务'] == 'MSO平台') & (df['产品类型'] == '收款业务') & (df['商户类型'] == '损益户')]['损益金额'].sum())
    
    # 也许是按产品类型分的?
    # 产品类型有: 跨境收单, 换汇平台, 企业外汇-出境, 留学缴费, 互联汇款, 企业外汇-纯汇兑, 收款业务
    # 截图的"境内账户服务"可能对应 产品类型=换汇平台(损益户,不含SVF)?
    
    hh_no_svf = df[(df['产品类型'] == '换汇平台') & (~df['所属业务'].isin(['SVF平台']))]
    hh_no_svf_pnl = df[(df['产品类型'] == '换汇平台') & (~df['所属业务'].isin(['SVF平台'])) & (df['商户类型'] == '损益户')]
    
    print(f"\n  === 境内账户服务映射尝试 ===")
    print(f"  截图={S['境内账户服务'][m_idx]}")
    print(f"    换汇平台(不含SVF,损益户): {K(hh_no_svf_pnl['损益金额'].sum())}")
    print(f"    换汇平台(不含SVF,全部): {K(hh_no_svf['损益金额'].sum())}")
    
    # 也许: 境内 = MSO换汇(损益户) + MSO收款(损益户) + 出境机酒 + MSO互联收单?
    mso_hlsd = df[(df['所属业务'] == 'MSO平台') & (df['产品类型'] == '互联收单')]
    combo = mso_hh + mso_sk + cj + K(mso_hlsd['损益金额'].sum())
    print(f"    MSO换汇+收款+出境+互联收单: {combo}")
    
    # 境内 = MSO换汇 + 出境?
    print(f"    MSO换汇+出境: {mso_hh + cj}")
    # 1月: 2257+3039=5296, 截图3738 → 差-1558
    
    # 境内 = 出境+MSO收款+纯汇兑?
    print(f"    出境+收款+纯汇兑: {cj+mso_sk+K(df[df['所属业务']=='纯汇兑']['损益金额'].sum())}")
    # 1月: 3039+300+423=3762, 截图3738 → 差24!!! 接近!
    
    # 不对, 纯汇兑已经是基础通道了
    # 但如果截图的分类跟我想的不一样呢?
    # 也许"企业外汇"整体 = 出境+MSO换汇+MSO收款+纯汇兑+SVF的某部分?
    
    print(f"\n  === 企业外汇整体验证 ===")
    print(f"  截图企业外汇小计={S['企业外汇'][m_idx]}")
    qywh_combo = cj + mso_hh + mso_sk + K(df[df['所属业务']=='纯汇兑']['损益金额'].sum())
    print(f"    出境+MSO换汇+收款+纯汇兑: {qywh_combo}")
    # 1月: 3039+2257+300+423=6019, 截图4603, 差1416
    
    # 也许排除MSO换汇?
    qywh2 = cj + mso_sk + K(df[df['所属业务']=='纯汇兑']['损益金额'].sum())
    print(f"    出境+收款+纯汇兑: {qywh2}")
    # 1月: 3039+300+423=3762, 截图4603, 差-841
    
    # 也许 企业外汇 不含基础通道? 截图=4603, 减去基础通道423=4180
    # 4180 vs 出境(3039)+MSO换汇(2257)+收款(300)=5596 → 差-1416
    
    # 完全不同的思路: 也许截图的分类是基于 产品类型 而非 所属业务!
    # 境内账户服务 → 产品类型=换汇平台+收款业务(MSO,不含SVF)?
    # 1月: MSO换汇(2257)+MSO收款(300)=2557, 截图3738 → 差1181
    
    # 加上出境: 2557+3039=5596 → 太大
    # 或者"境内账户服务"就是"换汇平台(全部,含SVF)"?
    hh_all = K(df[df['产品类型']=='换汇平台']['损益金额'].sum())
    print(f"    换汇平台(全部): {hh_all}")
    # 1月: 7663 → 太大

    # 我在绕圈了... 让我聚焦最有可能的映射

print("\n" + "=" * 90)
print("总结: 能确定和不能确定的映射")
print("=" * 90)

print("""
══════════════════════════════════════════════════════════════════════
  截图完整结构 (千元, 表头"汇兑损益（千元）"):
══════════════════════════════════════════════════════════════════════

  业务侧汇兑损益:
    跨境汇款          1,173    703     ← ??
    汇款互联            532    534     ← CSV互联汇款 ✅
    港陆汇款              0      0     ← ??
    留学缴费            641    169     ← CSV留学缴费(差20/12千,接近)
    企业外汇          4,603  4,481     = 境内+境外+基础
      境内账户服务     3,738  4,063     ← ??
      境外账户服务       443    226     ← ??
      基础通道服务       423    192     ← CSV纯汇兑 ✅
    (隐藏行)        -1,172   -703     ← ??
    业务侧小计       5,777  5,184
  平台侧汇兑损益    -1,300 10,824     = 平台不含FiT + FIT侧 ✅
  税后汇兑损益       4,477 16,008     = 业务侧 + 平台侧 ✅
  跨境收单损益      17,744 -24,274    = WXG + FIT侧(差≤1) ✅
  WXG侧损益       20,766 -33,462
  FIT侧损益(含在平台侧) -3,023  9,188
  平台不含跨境FiT    1,723  1,636

  恒等式:
    税后 = 业务侧 + 平台侧                    ✅ 两月验证
    平台侧 = 平台不含FiT + FIT侧               ✅ 两月验证
    跨境收单损益 ≈ WXG + FIT侧                 ✅ 两月验证(差≤1)

  已确认映射:
    汇款互联 = CSV 所属业务=互联汇款             ✅ 精确匹配
    基础通道服务 = CSV 所属业务=纯汇兑           ✅ 精确匹配
    留学缴费 ≈ CSV 所属业务=留学缴费             ~近似(差20/12千)

  未确认映射:
    跨境汇款: CSV跨境收单(全量)=15076≫截图1173
    境内账户服务: 截图3738, 无精确匹配组合
    境外账户服务: 截图443, 无精确匹配组合
    隐藏行: -1172(1月)/-703(2月), 穷举搜索无精确匹配

  结论:
    截图和CSV出自同一数据源(互联汇款/纯汇兑精确匹配)
    但截图使用了一个额外的业务归类维度,将原始CSV数据重新分配
    这个归类规则无法仅从18个原子项的穷举组合中反推出来
    → 需要看到分类映射定义(业务归类配置)才能精确复现
""")
