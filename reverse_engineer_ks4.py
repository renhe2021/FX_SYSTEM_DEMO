# -*- coding: utf-8 -*-
"""
双月同时穷举验证:
目标: 找到一组(渠道×业务)原子项,
      使得 1月合计≈4477千 AND 2月合计≈16008千
"""
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

def K(v): return round(v / 1000)

# ===================================================================
# 构建原子项 (渠道×业务)
# ===================================================================
atoms1 = df1.groupby(['损益实际归属主体','所属业务'])['损益金额'].sum()
atoms2 = df2.groupby(['损益实际归属主体','所属业务'])['损益金额'].sum()

# 合并所有key
all_keys = sorted(set(atoms1.index) | set(atoms2.index))
atom_pairs = []
for key in all_keys:
    v1 = K(atoms1.get(key, 0))
    v2 = K(atoms2.get(key, 0))
    if abs(v1) >= 1 or abs(v2) >= 1:
        atom_pairs.append((key, v1, v2))

print(f"原子项(渠道×业务), 非零: {len(atom_pairs)}个")
print(f"{'渠道':10s} {'业务':12s} {'1月千':>8s} {'2月千':>8s}")
print("-" * 50)
for key, v1, v2 in atom_pairs:
    print(f"{key[0]:10s} {key[1]:12s} {v1:>8,} {v2:>8,}")

# 目标: 
# 税后:        1月=4477, 2月=16008
# 跨境收单损益: 1月=17744, 2月=-24274

# ===================================================================
# 双月穷举: 找1月≈4477 AND 2月≈16008 的组合
# ===================================================================
print("\n" + "=" * 90)
print("双月穷举: 找1月≈4477 AND 2月≈16008 的组合")
print(f"  允许误差: ±50千")
print("=" * 90)

target1, target2 = 4477, 16008
tol = 50

found = []
n = len(atom_pairs)
for size in range(1, n+1):
    for combo in combinations(range(n), size):
        s1 = sum(atom_pairs[i][1] for i in combo)
        s2 = sum(atom_pairs[i][2] for i in combo)
        if abs(s1 - target1) <= tol and abs(s2 - target2) <= tol:
            found.append((size, combo, s1, s2))
    if found:
        print(f"  在{size}项组合中找到{len(found)}个匹配!")
        break

if found:
    found.sort(key=lambda x: abs(x[2]-target1) + abs(x[3]-target2))
    for size, combo, s1, s2 in found[:20]:
        names = [f"{atom_pairs[i][0][0]}×{atom_pairs[i][0][1]}" for i in combo]
        print(f"\n  [{size}项] 1月={s1}(差{s1-target1}) 2月={s2}(差{s2-target2})")
        for i in combo:
            print(f"    {atom_pairs[i][0][0]:10s}×{atom_pairs[i][0][1]:12s}: {atom_pairs[i][1]:>7,} / {atom_pairs[i][2]:>7,}")
else:
    print("  未找到匹配! 扩大到±200千...")
    tol = 200
    for size in range(1, n+1):
        for combo in combinations(range(n), size):
            s1 = sum(atom_pairs[i][1] for i in combo)
            s2 = sum(atom_pairs[i][2] for i in combo)
            if abs(s1 - target1) <= tol and abs(s2 - target2) <= tol:
                found.append((size, combo, s1, s2))
        if found:
            print(f"  在{size}项组合中找到{len(found)}个匹配!")
            break
    
    if found:
        found.sort(key=lambda x: abs(x[2]-target1) + abs(x[3]-target2))
        for size, combo, s1, s2 in found[:20]:
            print(f"\n  [{size}项] 1月={s1}(差{s1-target1}) 2月={s2}(差{s2-target2})")
            for i in combo:
                print(f"    {atom_pairs[i][0][0]:10s}×{atom_pairs[i][0][1]:12s}: {atom_pairs[i][1]:>7,} / {atom_pairs[i][2]:>7,}")
    else:
        print("  仍未找到! 继续搜索更多项...")
        for size in range(1, min(n+1, 10)):
            cnt = 0
            for combo in combinations(range(n), size):
                s1 = sum(atom_pairs[i][1] for i in combo)
                s2 = sum(atom_pairs[i][2] for i in combo)
                if abs(s1 - target1) <= 500 and abs(s2 - target2) <= 500:
                    found.append((size, combo, s1, s2))
                    cnt += 1
            if cnt > 0:
                print(f"  {size}项: 找到{cnt}个(±500千)")
        
        if found:
            found.sort(key=lambda x: abs(x[2]-target1) + abs(x[3]-target2))
            print(f"\n  最佳匹配(按总差排序):")
            for size, combo, s1, s2 in found[:20]:
                print(f"\n  [{size}项] 1月={s1}(差{s1-target1}) 2月={s2}(差{s2-target2}) 总差={abs(s1-target1)+abs(s2-target2)}")
                for i in combo:
                    print(f"    {atom_pairs[i][0][0]:10s}×{atom_pairs[i][0][1]:12s}: {atom_pairs[i][1]:>7,} / {atom_pairs[i][2]:>7,}")

# ===================================================================
# 同样穷举跨境收单损益: 1月=17744, 2月=-24274
# ===================================================================
print("\n\n" + "=" * 90)
print("双月穷举: 找1月≈17744 AND 2月≈-24274 的组合")
print("=" * 90)

target1_ks, target2_ks = 17744, -24274
found_ks = []
for size in range(1, n+1):
    for combo in combinations(range(n), size):
        s1 = sum(atom_pairs[i][1] for i in combo)
        s2 = sum(atom_pairs[i][2] for i in combo)
        if abs(s1 - target1_ks) <= 50 and abs(s2 - target2_ks) <= 50:
            found_ks.append((size, combo, s1, s2))
    if found_ks:
        print(f"  在{size}项组合中找到{len(found_ks)}个匹配!")
        break

if found_ks:
    found_ks.sort(key=lambda x: abs(x[2]-target1_ks) + abs(x[3]-target2_ks))
    for size, combo, s1, s2 in found_ks[:10]:
        print(f"\n  [{size}项] 1月={s1}(差{s1-target1_ks}) 2月={s2}(差{s2-target2_ks})")
        for i in combo:
            print(f"    {atom_pairs[i][0][0]:10s}×{atom_pairs[i][0][1]:12s}: {atom_pairs[i][1]:>7,} / {atom_pairs[i][2]:>7,}")
else:
    print("  ±50千未找到, 扩大到±700千 (涵盖1月640差异)...")
    for size in range(1, n+1):
        for combo in combinations(range(n), size):
            s1 = sum(atom_pairs[i][1] for i in combo)
            s2 = sum(atom_pairs[i][2] for i in combo)
            if abs(s1 - target1_ks) <= 700 and abs(s2 - target2_ks) <= 50:
                found_ks.append((size, combo, s1, s2))
        if found_ks:
            print(f"  在{size}项组合中找到{len(found_ks)}个匹配!")
            break
    
    if found_ks:
        found_ks.sort(key=lambda x: abs(x[2]-target1_ks) + abs(x[3]-target2_ks))
        for size, combo, s1, s2 in found_ks[:10]:
            print(f"\n  [{size}项] 1月={s1}(差{s1-target1_ks}) 2月={s2}(差{s2-target2_ks})")
            for i in combo:
                print(f"    {atom_pairs[i][0][0]:10s}×{atom_pairs[i][0][1]:12s}: {atom_pairs[i][1]:>7,} / {atom_pairs[i][2]:>7,}")

# ===================================================================
# 业务侧小计: 1月=5777, 2月=5184
# ===================================================================
print("\n\n" + "=" * 90)
print("双月穷举: 业务侧小计 1月≈5777 AND 2月≈5184")
print("=" * 90)

target1_biz, target2_biz = 5777, 5184
found_biz = []
for size in range(1, n+1):
    for combo in combinations(range(n), size):
        s1 = sum(atom_pairs[i][1] for i in combo)
        s2 = sum(atom_pairs[i][2] for i in combo)
        if abs(s1 - target1_biz) <= 50 and abs(s2 - target2_biz) <= 50:
            found_biz.append((size, combo, s1, s2))
    if found_biz:
        print(f"  在{size}项组合中找到{len(found_biz)}个匹配!")
        break

if found_biz:
    found_biz.sort(key=lambda x: abs(x[2]-target1_biz) + abs(x[3]-target2_biz))
    for size, combo, s1, s2 in found_biz[:20]:
        print(f"\n  [{size}项] 1月={s1}(差{s1-target1_biz}) 2月={s2}(差{s2-target2_biz})")
        for i in combo:
            print(f"    {atom_pairs[i][0][0]:10s}×{atom_pairs[i][0][1]:12s}: {atom_pairs[i][1]:>7,} / {atom_pairs[i][2]:>7,}")
else:
    print("  ±50千未找到, 扩大到±200千...")
    for size in range(1, n+1):
        for combo in combinations(range(n), size):
            s1 = sum(atom_pairs[i][1] for i in combo)
            s2 = sum(atom_pairs[i][2] for i in combo)
            if abs(s1 - target1_biz) <= 200 and abs(s2 - target2_biz) <= 200:
                found_biz.append((size, combo, s1, s2))
        if found_biz:
            print(f"  在{size}项组合中找到{len(found_biz)}个匹配!")
            break
    
    if found_biz:
        found_biz.sort(key=lambda x: abs(x[2]-target1_biz) + abs(x[3]-target2_biz))
        for size, combo, s1, s2 in found_biz[:20]:
            print(f"\n  [{size}项] 1月={s1}(差{s1-target1_biz}) 2月={s2}(差{s2-target2_biz})")
            for i in combo:
                print(f"    {atom_pairs[i][0][0]:10s}×{atom_pairs[i][0][1]:12s}: {atom_pairs[i][1]:>7,} / {atom_pairs[i][2]:>7,}")

# ===================================================================
# 平台侧: 1月=-1300, 2月=10824
# ===================================================================
print("\n\n" + "=" * 90)
print("双月穷举: 平台侧 1月≈-1300 AND 2月≈10824")
print("=" * 90)

target1_plat, target2_plat = -1300, 10824
found_plat = []
for size in range(1, n+1):
    for combo in combinations(range(n), size):
        s1 = sum(atom_pairs[i][1] for i in combo)
        s2 = sum(atom_pairs[i][2] for i in combo)
        if abs(s1 - target1_plat) <= 50 and abs(s2 - target2_plat) <= 50:
            found_plat.append((size, combo, s1, s2))
    if found_plat:
        print(f"  在{size}项组合中找到{len(found_plat)}个匹配!")
        break

if found_plat:
    found_plat.sort(key=lambda x: abs(x[2]-target1_plat) + abs(x[3]-target2_plat))
    for size, combo, s1, s2 in found_plat[:20]:
        print(f"\n  [{size}项] 1月={s1}(差{s1-target1_plat}) 2月={s2}(差{s2-target2_plat})")
        for i in combo:
            print(f"    {atom_pairs[i][0][0]:10s}×{atom_pairs[i][0][1]:12s}: {atom_pairs[i][1]:>7,} / {atom_pairs[i][2]:>7,}")
else:
    print("  ±50千未找到, 扩大到±500千...")
    for size in range(1, n+1):
        for combo in combinations(range(n), size):
            s1 = sum(atom_pairs[i][1] for i in combo)
            s2 = sum(atom_pairs[i][2] for i in combo)
            if abs(s1 - target1_plat) <= 500 and abs(s2 - target2_plat) <= 500:
                found_plat.append((size, combo, s1, s2))
        if found_plat:
            print(f"  在{size}项组合中找到{len(found_plat)}个匹配!")
            break
    
    if found_plat:
        found_plat.sort(key=lambda x: abs(x[2]-target1_plat) + abs(x[3]-target2_plat))
        for size, combo, s1, s2 in found_plat[:20]:
            print(f"\n  [{size}项] 1月={s1}(差{s1-target1_plat}) 2月={s2}(差{s2-target2_plat})")
            for i in combo:
                print(f"    {atom_pairs[i][0][0]:10s}×{atom_pairs[i][0][1]:12s}: {atom_pairs[i][1]:>7,} / {atom_pairs[i][2]:>7,}")

print("\n\n" + "=" * 90)
print("综合结论")
print("=" * 90)
