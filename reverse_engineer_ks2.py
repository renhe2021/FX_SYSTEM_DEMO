# -*- coding: utf-8 -*-
"""
深入分析:
1. 1月640千差异来源
2. 税后与CSV全量的关系 
3. 截图各行的完整映射
"""
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

# ===================================================================
# 截图数据 (千元)  — 来源: 用户提供的截图
# ===================================================================
# 行           | 26年1月  | 26年2月
# -------------|---------|--------
# 跨境收单损益  | 17,744  | -24,274
# WXG侧损益    | 20,766  | -33,462
# FIT侧损益    | -3,023  |   9,188
# 税后         |  4,477  |  16,008
# 业务侧小计   |  5,777  |   5,184
# 平台侧       | -1,300  |  10,824
# 平台不含FiT  |  1,723  |   1,636
#
# 恒等式 (已验证):
#   税后 = 业务侧 + 平台侧
#   跨境收单损益 = WXG + FIT侧
#   平台侧 = 平台不含FiT + FIT侧

# ===================================================================
# 第一部分: 1月640千差异的逐笔排查
# ===================================================================
print("=" * 90)
print("第一部分: 1月640千差异 — 逐笔排查")
print("=" * 90)
print("  公式: 跨境收单损益(截图) = 产品类型=跨境收单 + SVF平台")
print("  2月完美匹配, 1月差640千")
print()

biz_set = ['跨境收单', '融合一期', '融合三期', 'SVF平台']

# 逐行看1月的每条记录
print("--- 1月: 所属业务 in (跨境收单, 融合一期, 融合三期, SVF平台) 的全部明细 ---")
subset1 = df1[df1['所属业务'].isin(biz_set)].copy()
subset1['千元'] = subset1['损益金额'] / 1000
# 按 所属业务+归属主体+商户类型+币种 聚合
agg1 = subset1.groupby(['所属业务','损益实际归属主体','商户类型','原币种']).agg(
    损益千元=('千元','sum'),
    笔数=('千元','count')
).reset_index()
agg1 = agg1.sort_values(['所属业务','损益千元'], ascending=[True, False])
for biz in biz_set:
    sub = agg1[agg1['所属业务'] == biz]
    if len(sub) > 0:
        biz_total = sub['损益千元'].sum()
        print(f"\n  【{biz}】 合计: {biz_total:.1f}千")
        for _, r in sub.iterrows():
            print(f"    {r['损益实际归属主体']:10s} {r['商户类型']:6s} {r['原币种']:5s} {r['笔数']:3.0f}笔  {r['损益千元']:>10.1f}千")

total1 = subset1['千元'].sum()
print(f"\n  合计: {total1:.1f}千 (四舍五入={round(total1)}千)")
print(f"  截图: 17744千")
print(f"  差: {total1 - 17744:.1f}千")

# ===================================================================
# 对比2月，看看差异是否有规律
# ===================================================================
print("\n\n--- 2月: 同样明细 ---")
subset2 = df2[df2['所属业务'].isin(biz_set)].copy()
subset2['千元'] = subset2['损益金额'] / 1000
agg2 = subset2.groupby(['所属业务','损益实际归属主体','商户类型','原币种']).agg(
    损益千元=('千元','sum'),
    笔数=('千元','count')
).reset_index()
agg2 = agg2.sort_values(['所属业务','损益千元'], ascending=[True, False])
for biz in biz_set:
    sub = agg2[agg2['所属业务'] == biz]
    if len(sub) > 0:
        biz_total = sub['损益千元'].sum()
        print(f"\n  【{biz}】 合计: {biz_total:.1f}千")
        for _, r in sub.iterrows():
            print(f"    {r['损益实际归属主体']:10s} {r['商户类型']:6s} {r['原币种']:5s} {r['笔数']:3.0f}笔  {r['损益千元']:>10.1f}千")

total2 = subset2['千元'].sum()
print(f"\n  合计: {total2:.1f}千 (四舍五入={round(total2)}千)")
print(f"  截图: -24274千")
print(f"  差: {total2 - (-24274):.1f}千")

# ===================================================================
# 第二部分: 找640千 — 排除法
# ===================================================================
print("\n\n" + "=" * 90)
print("第二部分: 640千差异排除法")
print("=" * 90)

# 差640.414千 → 640414元
# 有没有某一条记录恰好是640千?
print("\n  查找1月中接近640千的单条记录 (所属业务在目标集内):")
for _, r in subset1.iterrows():
    v = r['损益金额'] / 1000
    if abs(abs(v) - 640) < 50:
        print(f"    {r['所属业务']:10s} {r['损益实际归属主体']:10s} {r['商户类型']:6s} {r['原币种']:5s}: {v:.1f}千")

# 看看如果从合计中减去某些项能否得到17744
print("\n  穷举: 从18384中减去哪些原子项可以得到17744?")
print(f"  即找原子项使sum≈640千")
atoms1 = subset1.groupby(['所属业务','损益实际归属主体','商户类型','原币种'])['千元'].sum()
atoms_list = [(idx, val) for idx, val in atoms1.items() if abs(val) > 0.5]
print(f"  非零原子项: {len(atoms_list)}个")

from itertools import combinations
found_combos = []
for size in range(1, 4):
    for combo in combinations(range(len(atoms_list)), size):
        s = sum(atoms_list[i][1] for i in combo)
        if abs(s - 640.414) < 5:
            found_combos.append((size, combo, s))

if found_combos:
    print(f"  找到 {len(found_combos)} 个组合 ≈ 640千:")
    for size, combo, s in found_combos[:10]:
        names = [f"{atoms_list[i][0]}" for i in combo]
        print(f"    [{size}项] sum={s:.1f}千: {', '.join(str(n) for n in names)}")
else:
    print("  未找到精确匹配640千的1-3项组合")

# ===================================================================
# 第三部分: 截图覆盖范围分析
# ===================================================================
print("\n\n" + "=" * 90)
print("第三部分: 截图覆盖范围 vs CSV全量")
print("=" * 90)

for label, df, scr_ks, scr_tax in [("1月", df1, 17744, 4477), ("2月", df2, -24274, 16008)]:
    print(f"\n{'='*40} {label} {'='*40}")
    total = K(df['损益金额'].sum())
    
    # 截图合计 = 税后 + 跨境收单损益
    scr_total = scr_tax + scr_ks
    csv_ks = K(df[df['所属业务'].isin(biz_set)]['损益金额'].sum())
    csv_rest = K(df[~df['所属业务'].isin(biz_set)]['损益金额'].sum())
    
    print(f"  CSV全量       = {total}")
    print(f"  截图合计(税后+跨境收单损益) = {scr_total}")
    print(f"  差(CSV全量 - 截图合计) = {total - scr_total}")
    print()
    print(f"  截图跨境收单损益 = {scr_ks}")
    print(f"  CSV跨境收单损益  = {csv_ks}")
    print(f"  截图税后       = {scr_tax}")
    print(f"  CSV其余(=税后?)= {csv_rest}")
    print()
    print(f"  税后差异: CSV其余({csv_rest}) - 截图税后({scr_tax}) = {csv_rest - scr_tax}")
    
    # 截图覆盖范围推测:
    # 如果截图 ≠ CSV全量，那么截图是什么范围?
    # 截图合计(1月) = 4477 + 17744 = 22221
    # CSV全量(1月) = 25566
    # 差 = 25566 - 22221 = 3345
    # 
    # 截图合计(2月) = 16008 + (-24274) = -8266
    # CSV全量(2月) = -18132
    # 差 = -18132 - (-8266) = -9866
    
    # 差异3345(1月)和-9866(2月)很大且不一致...
    # 也许截图不是用"全量-跨境收单损益"算税后?
    # 也许税后有自己的数据范围?

# ===================================================================
# 第四部分: 税后的独立分析
# ===================================================================
print("\n\n" + "=" * 90)
print("第四部分: 税后=业务侧+平台侧 的独立分析")
print("=" * 90)

# 截图:
# 业务侧小计: 1月=5777, 2月=5184
# 平台侧:     1月=-1300, 2月=10824
# 税后:       1月=4477, 2月=16008
# 验证: 5777+(-1300)=4477 ✓, 5184+10824=16008 ✓

# 业务侧包含: 跨境汇款(1173), 互联汇款(532), 留学缴费(641), 企业外汇-境内(3738), 境外(443), 隐藏行
# 平台侧包含: 平台不含FiT(1723) + FIT侧(-3023) = -1300

# CSV中有哪些所属业务不在跨境收单损益范围内?
print("\n  CSV中不在跨境收单损益范围的所属业务:")
for label, df in [("1月", df1), ("2月", df2)]:
    rest = df[~df['所属业务'].isin(biz_set)]
    by_biz = rest.groupby('所属业务')['损益金额'].sum().sort_values(ascending=False)
    print(f"\n  {label}:")
    for biz, v in by_biz.items():
        if abs(K(v)) >= 1:
            print(f"    {biz:20s}: {K(v):>7,}千")
    print(f"    合计: {K(rest['损益金额'].sum())}千  (截图税后: {4477 if label=='1月' else 16008})")

# ===================================================================
# 第五部分: WXG/FIT拆分验证
# ===================================================================
print("\n\n" + "=" * 90)
print("第五部分: WXG/FIT拆分 — 用'其中WX'和'FIT'衍生字段")
print("=" * 90)

for label, df, scr_wxg, scr_fit in [("1月", df1, 20766, -3023), ("2月", df2, -33462, 9188)]:
    print(f"\n{'='*40} {label} {'='*40}")
    
    # 跨境收单损益范围内的WX和FIT
    ks_data = df[df['所属业务'].isin(biz_set)]
    
    wx_ks = K(ks_data['其中WX'].sum())
    fit_ks = K(ks_data['FIT'].sum())
    total_ks = K(ks_data['损益金额'].sum())
    
    print(f"  跨境收单损益范围 (所属业务 in {biz_set}):")
    print(f"    损益金额合计  = {total_ks}千")
    print(f"    其中WX合计   = {wx_ks}千")
    print(f"    FIT合计      = {fit_ks}千")
    print(f"    WX+FIT       = {wx_ks + fit_ks}千 (应={total_ks}千)")
    print(f"    截图 WXG     = {scr_wxg}千  差={wx_ks - scr_wxg}")
    print(f"    截图 FIT     = {scr_fit}千  差={fit_ks - scr_fit}")
    
    # 也许WXG和FIT的拆分口径不同于我们的WX/FIT衍生字段?
    # 按渠道看
    print(f"\n    按渠道拆分WX/FIT:")
    for entity in sorted(ks_data['损益实际归属主体'].unique()):
        sub = ks_data[ks_data['损益实际归属主体'] == entity]
        print(f"      {entity:10s}: 损益={K(sub['损益金额'].sum()):>7,}千  WX={K(sub['其中WX'].sum()):>7,}千  FIT={K(sub['FIT'].sum()):>7,}千")

# ===================================================================
# 第六部分: CSV全量的WX/FIT拆分
# ===================================================================
print("\n\n" + "=" * 90)
print("第六部分: CSV全量的WX/FIT拆分")
print("=" * 90)

for label, df in [("1月", df1), ("2月", df2)]:
    print(f"\n  {label}:")
    print(f"    全量: 损益={K(df['损益金额'].sum())}千  WX={K(df['其中WX'].sum())}千  FIT={K(df['FIT'].sum())}千")
    
    # 跨境收单损益 vs 税后 的 WX/FIT
    ks_data = df[df['所属业务'].isin(biz_set)]
    rest_data = df[~df['所属业务'].isin(biz_set)]
    print(f"    跨境收单: 损益={K(ks_data['损益金额'].sum())}千  WX={K(ks_data['其中WX'].sum())}千  FIT={K(ks_data['FIT'].sum())}千")
    print(f"    税后范围: 损益={K(rest_data['损益金额'].sum())}千  WX={K(rest_data['其中WX'].sum())}千  FIT={K(rest_data['FIT'].sum())}千")

# ===================================================================
# 第七部分: 考虑商户类型=固收户/固收中转户 是否被排除
# ===================================================================
print("\n\n" + "=" * 90)
print("第七部分: 商户类型排除分析")
print("=" * 90)

for label, df, scr_ks, scr_tax in [("1月", df1, 17744, 4477), ("2月", df2, -24274, 16008)]:
    print(f"\n  {label} — 按商户类型看全量:")
    by_type = df.groupby('商户类型')['损益金额'].sum()
    for t, v in by_type.items():
        print(f"    {t}: {K(v):>7,}千")
    
    # 如果排除固收户?
    only_pnl = df[df['商户类型'] == '损益户']
    total_pnl = K(only_pnl['损益金额'].sum())
    ks_pnl = K(only_pnl[only_pnl['所属业务'].isin(biz_set)]['损益金额'].sum())
    rest_pnl = K(only_pnl[~only_pnl['所属业务'].isin(biz_set)]['损益金额'].sum())
    print(f"    仅损益户: 全量={total_pnl}千, 跨境收单={ks_pnl}千, 税后={rest_pnl}千")
    print(f"    截图: 跨境收单={scr_ks}千, 税后={scr_tax}千, 合计={scr_ks+scr_tax}千")
    print(f"    仅损益户全量 vs 截图合计: {total_pnl} vs {scr_ks + scr_tax}, 差{total_pnl - (scr_ks+scr_tax)}")

# ===================================================================
# 第八部分: 也许截图是按"渠道归属"分跨境收单损益和税后?
# ===================================================================
print("\n\n" + "=" * 90)
print("第八部分: 按渠道归属划分的假设")
print("=" * 90)

# 假设: 跨境收单损益 = WPHK归属 的全部
#       税后 = MSO+MPI 归属 中排除某些
for label, df, scr_ks, scr_tax in [("1月", df1, 17744, 4477), ("2月", df2, -24274, 16008)]:
    print(f"\n  {label}:")
    by_entity = df.groupby('损益实际归属主体')['损益金额'].sum().sort_values(ascending=False)
    for e, v in by_entity.items():
        print(f"    {e:15s}: {K(v):>7,}千")
    
    wphk = K(df[df['损益实际归属主体'] == 'CFT-WPHK']['损益金额'].sum())
    cft = K(df[df['损益实际归属主体'] == 'CFT']['损益金额'].sum())
    mso = K(df[df['损益实际归属主体'] == 'MSO']['损益金额'].sum())
    mpi = K(df[df['损益实际归属主体'] == 'MPI']['损益金额'].sum())
    
    # 各种组合
    print(f"\n    WPHK = {wphk}千")
    print(f"    CFT = {cft}千")
    print(f"    MSO = {mso}千")
    print(f"    MPI = {mpi}千")
    print(f"    WPHK+CFT = {wphk+cft}千  (截图跨境收单={scr_ks})")
    print(f"    MSO+MPI = {mso+mpi}千  (截图税后={scr_tax})")
    print(f"    WPHK+CFT+MSO = {wphk+cft+mso}千")
    print(f"    WPHK+MSO = {wphk+mso}千")

print("\n\n" + "=" * 90)
print("总结")
print("=" * 90)
print("""
已确认映射:
  ✅ 跨境收单损益 ≈ 所属业务 in (跨境收单, 融合一期, 融合三期, SVF平台)
     2月完美匹配 (-24274=-24274)
     1月差640千 (18384 vs 17744, ~3.6%)

待解决:
  ❓ 1月640千差异来源
  ❓ 税后(=业务侧+平台侧) 的数据范围 — CSV其余 ≠ 截图税后
  ❓ WXG/FIT拆分是否对应CSV的"其中WX"/"FIT"衍生字段
""")
