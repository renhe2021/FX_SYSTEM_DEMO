# -*- coding: utf-8 -*-
"""Reverse engineer v5: 穷举搜索精确匹配"""
import sys, os, io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pnl-analysis'))

import pandas as pd
import numpy as np
from itertools import combinations
from data_loader import load_csv, calc_derived_fields

data_dir = os.path.join(os.path.dirname(__file__), 'ddd', '20260310151934', 'data')
df1 = calc_derived_fields(load_csv(os.path.join(data_dir, 'PROFIT_LOSS_DETAIL_20260131.csv')))
df2 = calc_derived_fields(load_csv(os.path.join(data_dir, 'PROFIT_LOSS_DETAIL_20260228.csv')))

def to_k(v):
    return round(v / 1000)

# 截图 (千元)
S = {
    '跨境收单': (1173, 703), '汇款互联': (532, 534), '留学缴费': (503, 169),
    '企业外汇-境内购汇': (3738, 4063), '企业外汇-境外账户': (443, 226),
    '企业外汇-基础通道': (423, 192), '企业外汇小计': (4603, 4481),
    '业务侧小计': (5777, 5184), '平台侧汇兑损益': (-1300, 10824),
    '税后汇兑损益': (4477, 16008), '跨境收单损益': (17744, -24274),
    'WXG侧损益': (22250, -33462), 'FIT侧损益': (-1521, 9188),
    '平台(不含跨境FIT)': (1723, 1636),
}

print("=" * 90)
print("已确认：截图单位=千元, 互联汇款/纯汇兑 完美匹配")
print("=" * 90)

print("""
已知映射:
  ✓ 汇款互联 = 所属业务=互联汇款 (全部)
  ✓ 企业外汇-基础通道 = 所属业务=纯汇兑 (全部)
  ✓ 税后 = 业务侧 + 平台侧
  ✓ 2月: 平台(不含跨境FIT) + FIT侧 = 平台侧
  ✓ 2月: WXG + FIT = 跨境收单损益

待解:
  ? 跨境收单 = ?
  ? 留学缴费 = ?  (1月差130, 2月差4)
  ? 企业外汇-境内购汇 = ?
  ? 企业外汇-境外账户 = ?
  ? 业务侧有隐藏行(1月=-1034, 2月=-703)
  ? 平台侧 = ?
  ? 跨境收单损益 = ?
  ? WXG侧 = ?
  ? FIT侧 = ?
""")

# =======================================================
# 构建所有原子单元（业务×渠道×商户类型）
# =======================================================
print("=" * 90)
print("穷举搜索: 1月数据")
print("=" * 90)

atoms1 = df1.groupby(['损益实际归属主体', '所属业务', '商户类型'])['损益金额'].sum().reset_index()
atoms1['千元'] = atoms1['损益金额'].apply(to_k)
atoms1 = atoms1[atoms1['千元'].abs() >= 1].reset_index(drop=True)

print(f"\n原子单元 ({len(atoms1)}个, |千元|>=1):")
for i, r in atoms1.iterrows():
    lbl = f"{r['损益实际归属主体']}/{r['所属业务']}/{r['商户类型']}"
    print(f"  [{i:2d}] {lbl:45s} = {r['千元']:>8,}")

# 搜索目标
targets = {
    '跨境收单': S['跨境收单'][0],           # 1173
    '留学缴费': S['留学缴费'][0],           # 503
    '企业外汇-境内购汇': S['企业外汇-境内购汇'][0],  # 3738
    '企业外汇-境外账户': S['企业外汇-境外账户'][0],  # 443
    '业务侧小计': S['业务侧小计'][0],        # 5777
    '平台侧': S['平台侧汇兑损益'][0],        # -1300
    '跨境收单损益': S['跨境收单损益'][0],      # 17744
    'WXG侧': S['WXG侧损益'][0],            # 22250
    'FIT侧': S['FIT侧损益'][0],            # -1521
}

vals = list(atoms1['千元'])
n = len(vals)

for target_name, target_val in targets.items():
    print(f"\n--- 搜索 {target_name} = {target_val} (允许误差±5) ---")
    found = []
    tol = 5
    
    # 1项
    for i in range(n):
        if abs(vals[i] - target_val) <= tol:
            found.append(([i], vals[i]))
    
    # 2项
    for i in range(n):
        for j in range(i+1, n):
            s = vals[i] + vals[j]
            if abs(s - target_val) <= tol:
                found.append(([i,j], s))
    
    # 3项
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                s = vals[i] + vals[j] + vals[k]
                if abs(s - target_val) <= tol:
                    found.append(([i,j,k], s))
    
    # 4项 (只对业务侧/平台侧/大目标搜)
    if abs(target_val) > 3000:
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    for l in range(k+1, n):
                        s = vals[i] + vals[j] + vals[k] + vals[l]
                        if abs(s - target_val) <= tol:
                            found.append(([i,j,k,l], s))
    
    # 5项 (只对最大的目标)
    if abs(target_val) > 5000:
        for combo in combinations(range(n), 5):
            s = sum(vals[idx] for idx in combo)
            if abs(s - target_val) <= tol:
                found.append((list(combo), s))
    
    # 6项
    if abs(target_val) > 5000:
        for combo in combinations(range(n), 6):
            s = sum(vals[idx] for idx in combo)
            if abs(s - target_val) <= tol:
                found.append((list(combo), s))
    
    if found:
        # 按项数排序
        found.sort(key=lambda x: len(x[0]))
        for indices, total in found[:10]:
            parts = []
            for idx in indices:
                r = atoms1.loc[idx]
                parts.append(f"{r['损益实际归属主体']}/{r['所属业务']}/{r['商户类型']}({r['千元']})")
            print(f"  [{len(indices)}项] {' + '.join(parts)} = {total}")
    else:
        print(f"  (无匹配)")

# =======================================================
# 同样对2月验证
# =======================================================
print("\n" + "=" * 90)
print("验证: 1月找到的组合规则在2月是否也成立")
print("=" * 90)

# 基于上面的搜索结果，手动验证最可能的规则
for label, df, m_idx in [("1月", df1, 0), ("2月", df2, 1)]:
    print(f"\n{'='*40} {label} {'='*40}")
    
    # 假设规则(待搜索结果确认后填入):
    # 先列出所有按(渠道×业务×商户)的千元值
    atoms = df.groupby(['损益实际归属主体', '所属业务', '商户类型']).agg(
        损益千元=('损益金额', lambda x: to_k(x.sum())),
    ).reset_index()
    
    # 构建查询函数
    def get_val(entity=None, biz=None, mtype=None):
        mask = pd.Series(True, index=df.index)
        if entity: mask &= df['损益实际归属主体'] == entity
        if biz: mask &= df['所属业务'] == biz
        if mtype: mask &= df['商户类型'] == mtype
        return to_k(df[mask]['损益金额'].sum())
    
    # 已确认
    print(f"  互联汇款: {get_val(biz='互联汇款')} (截图:{S['汇款互联'][m_idx]})")
    print(f"  纯汇兑: {get_val(biz='纯汇兑')} (截图:{S['企业外汇-基础通道'][m_idx]})")
    
    # 留学: 2月差4, 也许截图不含留学锁价, 或者有不同的四舍五入?
    # 或者留学截图只看 MSO渠道(不含WPHK)?
    lx_mso = get_val(entity='MSO', biz='留学缴费')
    lx_all = get_val(biz='留学缴费')
    lx_lock = get_val(biz='留学锁价商户')
    print(f"  留学(MSO): {lx_mso} 留学(全): {lx_all} 锁价: {lx_lock} 留学-锁价={lx_all+lx_lock}")
    # 1月留学缴费只有MSO, 没有其他渠道, 所以不是渠道问题

    # 也许留学截图 = 留学缴费 - 出境相关? 不太合理
    # 或者CSV中有些数据截图不算?
    
    # 试: 按产品类型看留学
    lx_prod = df[df['产品类型'] == '留学缴费']
    lx_prod_pnl = df[(df['产品类型'] == '留学缴费') & (df['商户类型'] == '损益户')]
    print(f"  产品=留学(全): {to_k(lx_prod['损益金额'].sum())} 产品=留学(损益户): {to_k(lx_prod_pnl['损益金额'].sum())}")
    
    # 按渠道分
    for entity in ['MSO', 'CFT-WPHK', 'CFT', 'MPI']:
        sub = df[(df['产品类型'] == '留学缴费') & (df['损益实际归属主体'] == entity)]
        if len(sub) > 0:
            print(f"    {entity}: {to_k(sub['损益金额'].sum())}")

print("\n" + "=" * 90)
print("更精细分析: 按产品类型×渠道×商户类型 构建原子")
print("=" * 90)

# 也许分类是按产品类型而不是所属业务?
atoms_prod1 = df1.groupby(['损益实际归属主体', '产品类型', '商户类型'])['损益金额'].sum().reset_index()
atoms_prod1['千元'] = atoms_prod1['损益金额'].apply(to_k)
atoms_prod1 = atoms_prod1[atoms_prod1['千元'].abs() >= 1].reset_index(drop=True)

print(f"\n1月 按产品类型的原子单元 ({len(atoms_prod1)}个):")
for i, r in atoms_prod1.iterrows():
    lbl = f"{r['损益实际归属主体']}/{r['产品类型']}/{r['商户类型']}"
    print(f"  [{i:2d}] {lbl:45s} = {r['千元']:>8,}")

# 搜索境内购汇
target_gw = S['企业外汇-境内购汇'][0]  # 3738
print(f"\n搜索 境内购汇={target_gw} (按产品类型原子, ±5):")
vals_p = list(atoms_prod1['千元'])
np2 = len(vals_p)

for size in range(1, 4):
    for combo in combinations(range(np2), size):
        s = sum(vals_p[idx] for idx in combo)
        if abs(s - target_gw) <= 5:
            parts = [f"{atoms_prod1.loc[idx,'损益实际归属主体']}/{atoms_prod1.loc[idx,'产品类型']}/{atoms_prod1.loc[idx,'商户类型']}({vals_p[idx]})" for idx in combo]
            print(f"  [{size}项] {' + '.join(parts)} = {s}")

# 搜索境外账户
target_jw = S['企业外汇-境外账户'][0]  # 443
print(f"\n搜索 境外账户={target_jw} (按产品类型原子, ±5):")
for size in range(1, 4):
    for combo in combinations(range(np2), size):
        s = sum(vals_p[idx] for idx in combo)
        if abs(s - target_jw) <= 5:
            parts = [f"{atoms_prod1.loc[idx,'损益实际归属主体']}/{atoms_prod1.loc[idx,'产品类型']}/{atoms_prod1.loc[idx,'商户类型']}({vals_p[idx]})" for idx in combo]
            print(f"  [{size}项] {' + '.join(parts)} = {s}")

# 搜索跨境收单(截图)
target_ks = S['跨境收单'][0]  # 1173
print(f"\n搜索 跨境收单={target_ks} (按产品类型原子, ±5):")
for size in range(1, 5):
    for combo in combinations(range(np2), size):
        s = sum(vals_p[idx] for idx in combo)
        if abs(s - target_ks) <= 5:
            parts = [f"{atoms_prod1.loc[idx,'损益实际归属主体']}/{atoms_prod1.loc[idx,'产品类型']}/{atoms_prod1.loc[idx,'商户类型']}({vals_p[idx]})" for idx in combo]
            print(f"  [{size}项] {' + '.join(parts)} = {s}")

# 搜索留学
target_lx = S['留学缴费'][0]  # 503
print(f"\n搜索 留学缴费={target_lx} (按产品类型原子, ±5):")
for size in range(1, 4):
    for combo in combinations(range(np2), size):
        s = sum(vals_p[idx] for idx in combo)
        if abs(s - target_lx) <= 5:
            parts = [f"{atoms_prod1.loc[idx,'损益实际归属主体']}/{atoms_prod1.loc[idx,'产品类型']}/{atoms_prod1.loc[idx,'商户类型']}({vals_p[idx]})" for idx in combo]
            print(f"  [{size}项] {' + '.join(parts)} = {s}")

# 搜索平台侧
target_pt = S['平台侧汇兑损益'][0]  # -1300
print(f"\n搜索 平台侧={target_pt} (按产品类型原子, ±5):")
for size in range(1, 5):
    for combo in combinations(range(np2), size):
        s = sum(vals_p[idx] for idx in combo)
        if abs(s - target_pt) <= 5:
            parts = [f"{atoms_prod1.loc[idx,'损益实际归属主体']}/{atoms_prod1.loc[idx,'产品类型']}/{atoms_prod1.loc[idx,'商户类型']}({vals_p[idx]})" for idx in combo]
            print(f"  [{size}项] {' + '.join(parts)} = {s}")
