# -*- coding: utf-8 -*-
"""聚焦跨境收单损益 — 最大头"""
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

# 截图 (千元)
# 跨境收单损益: 1月=17,744  2月=-24,274
# WXG侧损益:   1月=20,766  2月=-33,462
# FIT侧损益:   1月=-3,023  2月=9,188
# 恒等式: 跨境收单损益 = WXG + FIT侧 (验证通过)

print("=" * 90)
print("聚焦: 跨境收单损益 (千元)")
print("  1月: 17,744    2月: -24,274")
print("  = WXG + FIT侧")
print("=" * 90)

for label, df, scr_ks in [("1月", df1, 17744), ("2月", df2, -24274)]:
    print(f"\n{'='*40} {label} {'='*40}")
    total = K(df['损益金额'].sum())
    print(f"  CSV全量: {total}")
    print(f"  截图跨境收单损益: {scr_ks}")
    
    # 截图结构:
    # 税后(4477) + 跨境收单损益(17744) = 22221 (1月)
    # 全量 = 25566
    # 差 = 25566 - 22221 = 3345
    # SVF = 5407 → 全量-SVF = 20159 → 跟22221差2062
    
    # 但是! 截图行名是"跨境收单损益"
    # CSV中"产品类型=跨境收单"的全部
    prod_ks = df[df['产品类型'] == '跨境收单']
    print(f"\n  产品类型=跨境收单 (全部): {K(prod_ks['损益金额'].sum())}")
    
    # 按渠道拆
    prod_ks_by_entity = prod_ks.groupby('损益实际归属主体')['损益金额'].sum()
    for e, v in prod_ks_by_entity.items():
        print(f"    {e}: {K(v)}")
    
    # 按所属业务拆
    prod_ks_by_biz = prod_ks.groupby('所属业务')['损益金额'].sum()
    for b, v in prod_ks_by_biz.items():
        print(f"    业务={b}: {K(v)}")
    
    # 产品类型=跨境收单 包含: 所属业务=跨境收单 + 融合一期 + 融合三期
    # 因为这三种业务的产品类型都是"跨境收单"!
    
    # 1月 产品类型=跨境收单:
    # 跨境收单: WPHK=14156, MSO=1847, CFT=-927
    # 融合一期: WPHK=1277
    # 融合三期: WPHK=-1035, MSO=74, CFT=-2415
    # 合计 = 14156+1847-927+1277-1035+74-2415 = 12977
    # 截图 = 17744
    # 差 = 17744-12977 = 4767
    
    print(f"\n  差(截图-产品跨境收单): {scr_ks - K(prod_ks['损益金额'].sum())}")
    
    # 也许"跨境收单损益"不仅包含产品类型=跨境收单，还包含其他?
    # 差4767 ≈ SVF(5407)? 接近!
    # 也许: 跨境收单损益 = 产品类型=跨境收单 + SVF?
    svf = K(df[df['所属业务'] == 'SVF平台']['损益金额'].sum())
    prod_ks_plus_svf = K(prod_ks['损益金额'].sum()) + svf
    print(f"  产品跨境收单 + SVF: {prod_ks_plus_svf} (截图:{scr_ks}) 差{prod_ks_plus_svf - scr_ks}")
    # 1月: 12977+5407=18384 vs 17744 → 差640
    # 2月: -14496+(-9778)=-24274 vs -24274 → 差0!!!! 🎯🎯🎯
    
    print(f"  *** 产品=跨境收单 + SVF平台 = {prod_ks_plus_svf} ***")
    
    # 2月完美匹配!! 1月差640
    # 640 ≈ 留学缴费(661)? 接近!
    # 也许1月的差异来自四舍五入?
    
    # 用精确值(不四舍五入)再算
    prod_ks_exact = prod_ks['损益金额'].sum()
    svf_exact = df[df['所属业务'] == 'SVF平台']['损益金额'].sum()
    combo_exact = prod_ks_exact + svf_exact
    print(f"  精确值: 产品跨境收单={prod_ks_exact:.2f} SVF={svf_exact:.2f} 合计={combo_exact:.2f}")
    print(f"  合计/1000={combo_exact/1000:.1f} 四舍五入={round(combo_exact/1000)}")
    print(f"  截图:{scr_ks}")

print("\n" + "=" * 90)
print("🎯 重大发现！2月完美匹配！")
print("  跨境收单损益 = 产品类型=跨境收单 + SVF平台")
print("  2月: -14496 + (-9778) = -24274 = 截图-24274 ✅✅✅")
print("  1月: 12977 + 5407 = 18384 vs 截图17744 (差640)")
print("=" * 90)

# 1月差640... 看看是不是因为SVF平台中有固收户?
print("\n" + "=" * 90)
print("分析1月的640差异")
print("=" * 90)

# SVF 1月 按商户类型
svf1 = df1[df1['所属业务'] == 'SVF平台']
svf1_by_type = svf1.groupby('商户类型')['损益金额'].sum()
for t, v in svf1_by_type.items():
    print(f"  SVF {t}: {K(v)}")
# SVF 损益户=5407, 固收户=1 → 如果只取损益户: 12977+5407=18384, 跟全部一样

# 也许跨境收单中要排除某些部分?
# 产品类型=跨境收单 的 商户类型
prod_ks1_by_type = df1[df1['产品类型'] == '跨境收单'].groupby('商户类型')['损益金额'].sum()
for t, v in prod_ks1_by_type.items():
    print(f"  产品跨境收单 {t}: {K(v)}")
# 全部都是损益户

# 用精确值计算差异
prod_ks1_val = df1[df1['产品类型'] == '跨境收单']['损益金额'].sum()
svf1_val = df1[df1['所属业务'] == 'SVF平台']['损益金额'].sum()
print(f"\n  精确: 产品跨境收单={prod_ks1_val/1000:.3f}千 + SVF={svf1_val/1000:.3f}千 = {(prod_ks1_val+svf1_val)/1000:.3f}千")
print(f"  截图: 17744千")
print(f"  差: {(prod_ks1_val+svf1_val)/1000 - 17744:.3f}千")

# 也许不是产品类型=跨境收单, 而是其他口径?
# 看看 WPHK 的全部 (WPHK包含: 跨境收单+SVF+融合一期+融合三期)
wphk1 = K(df1[df1['损益实际归属主体'] == 'CFT-WPHK']['损益金额'].sum())
print(f"\n  WPHK全部: {wphk1}")
# 1月WPHK=19806, 截图跨境收单损益=17744, 差2062

# WPHK + CFT?
cft1 = K(df1[df1['损益实际归属主体'] == 'CFT']['损益金额'].sum())
print(f"  WPHK+CFT: {wphk1 + cft1}")
# 19806+(-3342)=16464 vs 17744 → 差-1280

# WPHK + CFT + 部分MSO?
# 部分MSO = 跨境收单MSO(1847) + 融合三期MSO(74)?
mso_ks = K(df1[(df1['所属业务'] == '跨境收单') & (df1['损益实际归属主体'] == 'MSO')]['损益金额'].sum())
mso_rh3 = K(df1[(df1['所属业务'] == '融合三期') & (df1['损益实际归属主体'] == 'MSO')]['损益金额'].sum())
print(f"  WPHK+CFT+MSO跨境收单+MSO融合三: {wphk1 + cft1 + mso_ks + mso_rh3}")
# 16464+1847+74=18385 → 接近18384(产品跨境+SVF)

# 嗯, 基本就是: 产品类型=跨境收单 的全部 + SVF平台的全部
# = WPHK全部 + CFT全部 + MSO跨境收单 + MSO融合三期
# = 所有渠道中, 所属业务为(跨境收单/融合一期/融合三期/SVF平台)的全部

# 验证:
biz_set = ['跨境收单', '融合一期', '融合三期', 'SVF平台']
combo1 = K(df1[df1['所属业务'].isin(biz_set)]['损益金额'].sum())
combo2 = K(df2[df2['所属业务'].isin(biz_set)]['损益金额'].sum())
print(f"\n  1月 跨境收单+融合一+融合三+SVF: {combo1} (截图:17744, 差{combo1-17744})")
print(f"  2月 跨境收单+融合一+融合三+SVF: {combo2} (截图:-24274, 差{combo2-(-24274)})")

# 1月: 15076+1277-3376+5407=18384 vs 17744 → 差640
# 2月: 70+(-1576)+(-12990)+(-9778)=-24274 → 差0 ✅

# 差640只在1月... 也许1月有个额外的调整?
# 640千 → 看看有没有这个数的来源

# 留学缴费截图=641 vs CSV=661, 差=-20
# 出境机酒什么的 640? 

# 看看SVF平台的明细
print(f"\n  === SVF平台1月明细 ===")
svf1_detail = df1[df1['所属业务'] == 'SVF平台'].groupby(['损益实际归属主体','商户类型','原币种'])['损益金额'].sum()
svf1_detail = svf1_detail.reset_index()
svf1_detail['千元'] = svf1_detail['损益金额'].apply(K)
svf1_detail = svf1_detail.sort_values('千元', ascending=False)
for _, r in svf1_detail.iterrows():
    if abs(r['千元']) >= 10:
        print(f"    {r['损益实际归属主体']} {r['商户类型']} {r['原币种']:5s}: {r['千元']:>7,}")

# 总结: 跨境收单损益(截图) ≈ 产品类型=跨境收单(全部) + SVF平台(全部)
# 或等价于: 所属业务 in (跨境收单, 融合一期, 融合三期, SVF平台) 的全部
# 2月完美匹配, 1月差640千(约3.6%)

print("\n\n" + "=" * 90)
print("进一步验证: 如果跨境收单损益 = WPHK全部 + CFT全部")
print("那 税后 = MSO + MPI")  
print("=" * 90)

for label, df, scr_tax, scr_ks in [("1月", df1, 4477, 17744), ("2月", df2, 16008, -24274)]:
    print(f"\n--- {label} ---")
    
    wphk = K(df[df['损益实际归属主体'] == 'CFT-WPHK']['损益金额'].sum())
    cft = K(df[df['损益实际归属主体'] == 'CFT']['损益金额'].sum())
    mso = K(df[df['损益实际归属主体'] == 'MSO']['损益金额'].sum())
    mpi = K(df[df['损益实际归属主体'] == 'MPI']['损益金额'].sum())
    
    print(f"  WPHK+CFT = {wphk+cft} (截图跨境收单损益:{scr_ks}) 差{wphk+cft-scr_ks}")
    print(f"  MSO+MPI  = {mso+mpi} (截图税后:{scr_tax}) 差{mso+mpi-scr_tax}")
    
    # 1月: WPHK+CFT=16464, 截图=17744, 差-1280
    # MSO+MPI=9103, 截图税后=4477, 差4626
    # 不match
    
    # 也许: 跨境收单损益 = WPHK全部 + CFT(跨境收单+融合三期) + MSO(跨境收单+融合三期)
    # = 产品类型=跨境收单 中的全部 + SVF
    # 已知: 产品跨境收单+SVF = 18384(1月), 截图17744, 差640
    
    # 试: WPHK(不含SVF的固收户部分)?
    svf_fixed = K(df[(df['所属业务'] == 'SVF平台') & (df['商户类型'] != '损益户')]['损益金额'].sum())
    print(f"  SVF非损益户: {svf_fixed}")
    # 1月: SVF固收户=1 → 不影响

# 也许640来自于留学缴费的差异(20千)和某些其他四舍五入?
# 20千 << 640千, 不太可能

# 看看如果用 产品类型=跨境收单 + SVF(损益户)
print("\n" + "=" * 90)
print("试: 跨境收单损益 = 产品=跨境收单(损益户) + SVF(损益户)")
print("=" * 90)
for label, df, scr in [("1月", df1, 17744), ("2月", df2, -24274)]:
    prod_ks_pnl = K(df[(df['产品类型'] == '跨境收单') & (df['商户类型'] == '损益户')]['损益金额'].sum())
    svf_pnl = K(df[(df['所属业务'] == 'SVF平台') & (df['商户类型'] == '损益户')]['损益金额'].sum())
    combo = prod_ks_pnl + svf_pnl
    print(f"  {label}: 产品跨境(损益户)={prod_ks_pnl} + SVF(损益户)={svf_pnl} = {combo} (截图:{scr}) 差{combo-scr}")

# 跟之前一样... 因为产品=跨境收单全部都是损益户

# 也许要排除出境机酒??
# 等等, 出境机酒的产品类型是"企业外汇-出境", 不是"跨境收单", 所以不在里面

# 让我看看 所属业务=跨境收单 + 融合 + SVF, 但排除WPHK的借道商户
print("\n" + "=" * 90)
print("最终: 也许1月的640差异来自数据时效(截图生成时的数据快照)")
print("=" * 90)

# 结论:
# 跨境收单损益 = 所属业务 in (跨境收单, 融合一期, 融合三期, SVF平台)
# 2月 完美匹配 (-24274 = -24274)
# 1月 差640千 (18384 vs 17744)
# 640千 可能来自:
# - 截图生成时数据快照与我们的CSV有微小差异(如有后续调整)
# - 或者分类规则更复杂(某些记录被排除)

# 但核心映射已经找到!

# 验证推论: 如果跨境收单损益 = 跨境收单+融合一+融合三+SVF
# 那: 税后 = 全量 - 跨境收单损益 = 全量 - (跨境+融合+SVF)
# 即: 税后 = 互联汇款 + 出境机酒 + MSO平台 + 纯汇兑 + 留学 + 留学锁价 + MPI + ...

for label, df, scr_tax in [("1月", df1, 4477), ("2月", df2, 16008)]:
    print(f"\n--- {label} ---")
    biz_ks = ['跨境收单', '融合一期', '融合三期', 'SVF平台']
    tax_biz = df[~df['所属业务'].isin(biz_ks)]
    tax_val = K(tax_biz['损益金额'].sum())
    print(f"  税后(=全量-跨境收单损益): {tax_val} (截图:{scr_tax}) 差{tax_val-scr_tax}")
    
    # 拆解税后的组成
    tax_by_biz = tax_biz.groupby('所属业务')['损益金额'].sum().sort_values(ascending=False)
    print(f"  税后组成:")
    for biz, v in tax_by_biz.items():
        if abs(K(v)) >= 1:
            print(f"    {biz:20s}: {K(v):>7,}")
    print(f"  税后合计: {tax_val}")
    
    # 进一步: 税后 = 业务侧 + 平台侧
    # 业务侧 = 跨境汇款+互联+留学+企业外汇 = ?
    # 平台侧 = ?
    
    # 已知截图:
    # 业务侧小计: 5777(1月), 5184(2月)
    # 平台侧: -1300(1月), 10824(2月)
    
    # 如果 业务侧 = MSO渠道 + MPI渠道 中排除跨境收单/融合/SVF后的部分
    mso_mpi_tax = tax_biz[tax_biz['损益实际归属主体'].isin(['MSO','MPI'])]
    print(f"\n  MSO+MPI(不含跨境/融合/SVF): {K(mso_mpi_tax['损益金额'].sum())} (截图业务侧:{5777 if label=='1月' else 5184})")
    
    # MSO+MPI中按业务看
    for biz in sorted(mso_mpi_tax['所属业务'].unique()):
        sub = mso_mpi_tax[mso_mpi_tax['所属业务'] == biz]
        if abs(K(sub['损益金额'].sum())) >= 1:
            print(f"      {biz}: {K(sub['损益金额'].sum())}")

print("\n" + "=" * 90)
print("🎯🎯🎯 完整映射推导")
print("=" * 90)
print("""
截图结构:
  税后 = 业务侧 + 平台侧
  跨境收单损益 = WXG + FIT侧
  平台侧 = 平台不含FiT + FIT侧

推导:
  跨境收单损益 ≈ 所属业务 in (跨境收单, 融合一期, 融合三期, SVF平台) 的全部
    → 2月: -24274 完美匹配 ✅
    → 1月: 18384 vs 17744 (差640, 约3.6%)
    
  税后 = 全量 - 跨境收单损益
    = 所属业务 in (互联汇款, 出境机酒, MSO平台, 纯汇兑, 留学缴费, 留学锁价, MPI平台, 借道, 机酒锁价...)
    → 1月: 25566-18384=7182 vs 截图4477 (差2705)
    → 2月: -18132-(-24274)=6142 vs 截图16008 (差-9866)
    → 不match... 
    
  说明全量 ≠ 税后 + 跨境收单损益
  也就是说截图覆盖的数据 ≠ CSV全量
""")

# 最终验证
for label, df in [("1月", df1), ("2月", df2)]:
    print(f"\n{label}:")
    total = K(df['损益金额'].sum())
    biz_set = ['跨境收单', '融合一期', '融合三期', 'SVF平台']
    ks_pnl = K(df[df['所属业务'].isin(biz_set)]['损益金额'].sum())
    rest = K(df[~df['所属业务'].isin(biz_set)]['损益金额'].sum())
    print(f"  全量={total}")
    print(f"  跨境收单损益(推导)={ks_pnl}")
    print(f"  其余(推导税后)={rest}")
    print(f"  对比: 跨境收单损益推导={ks_pnl}, 截图跨境收单损益={'17744' if label=='1月' else '-24274'}")
    print(f"  对比: 其余={rest}, 截图税后={'4477' if label=='1月' else '16008'}")
