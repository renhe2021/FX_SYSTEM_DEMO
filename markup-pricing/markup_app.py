# -*- coding: utf-8 -*-
"""
FX Markup Pricing Dashboard V4
================================
支持多主体 (全量/MSO/SVF) 的加价分析工具。
Markup 由用户输入。
"""

import sys, os, glob
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_file
from markup_engine import MarkupEngine
from data_loader import FXDataLoader
from volatility_engine import fetch_all_volatilities, compute_vol_weighted_markups

try:
    from scipy.optimize import minimize
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

app = Flask(__name__, static_folder='.', static_url_path='')

# 三个引擎实例
engines = {
    'summary': MarkupEngine('summary'),
    'mso': MarkupEngine('mso'),
    'svf': MarkupEngine('svf'),
}
loader = None
vol_cache = None  # 波动率缓存


def get_engine(name=None) -> MarkupEngine:
    if name and name in engines:
        return engines[name]
    return engines['summary']


def init_engines():
    """初始化所有引擎"""
    global loader
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    files = sorted(glob.glob(os.path.join(data_dir, '*.xlsx')))
    files = [f for f in files if not os.path.basename(f).startswith('_')]
    if not files:
        print("WARNING: No xlsx files found in data/")
        return
    latest = files[-1]
    print(f"Loading data: {os.path.basename(latest)}")
    loader = FXDataLoader(latest).load()

    # 全量
    records = loader.to_flat_records('summary')
    engines['summary'].load_from_data(records, default_markup=0.0)
    print(f"  [summary] {len(records)} cells, volume: {engines['summary'].month_total:,.0f}")

    # MSO
    mso_records = loader.to_flat_records('mso')
    engines['mso'].load_from_data(mso_records, default_markup=0.0)
    print(f"  [mso] {len(mso_records)} cells, volume: {engines['mso'].month_total:,.0f}")

    # SVF
    svf_records = loader.to_flat_records('svf')
    engines['svf'].load_from_data(svf_records, default_markup=0.0)
    print(f"  [svf] {len(svf_records)} cells, volume: {engines['svf'].month_total:,.0f}")


init_engines()


# ─── Pages ───

@app.route('/')
def index():
    return send_file('markup_dashboard.html')


# ─── API: Data Info ───

@app.route('/api/info')
def get_info():
    entity = request.args.get('entity', 'summary')
    eng = get_engine(entity)
    return jsonify({
        'success': True,
        'entity': entity,
        'month': loader.month_label if loader else 'N/A',
        'businesses': eng.businesses,
        'ccys': eng.ccys,
        'month_total': eng.month_total,
        'cell_count': len([c for c in eng.cells.values() if c.volume > 0]),
        'available_entities': ['summary', 'mso', 'svf'],
        'entity_labels': {'summary': '全量 (MSO+SVF)', 'mso': 'MSO', 'svf': 'SVF'},
    })


# ─── API: Calc All ───

@app.route('/api/calc', methods=['POST'])
def calc_all():
    data = request.json or {}
    entity = data.get('entity', 'summary')
    eng = get_engine(entity)
    result = eng.calc_all()
    result['entity'] = entity
    return jsonify({'success': True, **result})


# ─── API: Matrices ───

@app.route('/api/matrices')
def get_matrices():
    entity = request.args.get('entity', 'summary')
    eng = get_engine(entity)
    return jsonify({
        'success': True,
        'entity': entity,
        'volume': eng.get_volume_matrix(),
        'markup': eng.get_markup_matrix(),
        'revenue': eng.get_revenue_matrix(),
    })


# ─── API: CCY Volumes (用于按币种设加价) ───

@app.route('/api/ccy_volumes')
def get_ccy_volumes():
    entity = request.args.get('entity', 'summary')
    eng = get_engine(entity)
    return jsonify({
        'success': True,
        'entity': entity,
        'ccys': eng.get_ccy_volumes(),
    })


# ─── API: Update Markups ───

@app.route('/api/update_markup', methods=['POST'])
def update_markup():
    data = request.json or {}
    entity = data.get('entity', 'summary')
    eng = get_engine(entity)

    if 'cell' in data:
        c = data['cell']
        eng.update_markup(c['business'], c['ccy'], float(c['markup_bps']))

    if 'batch' in data:
        eng.batch_update_markups(data['batch'])

    if 'uniform' in data:
        eng.set_uniform_markup(float(data['uniform']))

    if 'biz' in data:
        eng.set_biz_markup(data['biz']['business'], float(data['biz']['markup_bps']))

    if 'ccy' in data:
        eng.set_ccy_markup(data['ccy']['ccy'], float(data['ccy']['markup_bps']))

    # 批量按币种设置: {"ccy_markups": {"USD": 3.0, "EUR": 5.0, ...}}
    if 'ccy_markups' in data:
        for ccy, bps in data['ccy_markups'].items():
            eng.set_ccy_markup(ccy, float(bps))

    result = eng.calc_all()
    result['entity'] = entity
    return jsonify({'success': True, **result})


# ─── API: Uniform Scan ───

@app.route('/api/scan_uniform', methods=['POST'])
def scan_uniform():
    data = request.json or {}
    entity = data.get('entity', 'summary')
    eng = get_engine(entity)
    min_bps = float(data.get('min_bps', 0))
    max_bps = float(data.get('max_bps', 20))
    step = float(data.get('step', 0.5))
    results = eng.scan_uniform(min_bps, max_bps, step)
    return jsonify({'success': True, 'entity': entity, 'scan': results})


# ─── API: Reset ───

@app.route('/api/reset', methods=['POST'])
def reset():
    data = request.json or {}
    entity = data.get('entity', 'summary')
    if loader:
        source = entity if entity in ('mso', 'svf') else 'summary'
        records = loader.to_flat_records(source)
        engines[entity].load_from_data(records, default_markup=0.0)
    result = engines[entity].calc_all()
    result['entity'] = entity
    return jsonify({'success': True, **result})


# ─── API: Vol-Weighted Markup Suggestion ───

@app.route('/api/vol_data')
def get_vol_data():
    """拉取波动率数据 — 每次实时从BBG拉取4个月10分钟数据（仅拉取，不计算加价）"""
    global vol_cache
    vol_cache = fetch_all_volatilities(interval=10, days_back=120)
    # 返回拉取时间
    vol_cache['_fetch_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({'success': True, 'vol_data': vol_cache})


@app.route('/api/vol_suggest', methods=['POST'])
def vol_suggest():
    """基于已拉取的波动率数据计算建议 markup（不重新拉取）"""
    global vol_cache
    data = request.json or {}
    entity = data.get('entity', 'summary')
    target_bps = float(data.get('target_bps', 0.5))

    eng = get_engine(entity)

    # 不再自动拉取！必须先手动拉取
    if vol_cache is None:
        return jsonify({'success': False, 'error': '请先点击「拉取波动率数据」按钮获取市场数据'})

    # 获取交易量
    volumes = {}
    for ccy_info in eng.get_ccy_volumes():
        volumes[ccy_info['ccy']] = ccy_info['volume']

    # 计算建议
    result = compute_vol_weighted_markups(volumes, vol_cache, target_avg_bps=target_bps)
    result['entity'] = entity
    result['fetch_time'] = vol_cache.get('_fetch_time', '未知')
    return jsonify({'success': True, **result})


@app.route('/api/apply_vol_suggest', methods=['POST'])
def apply_vol_suggest():
    """应用波动率加权建议到引擎"""
    global vol_cache
    data = request.json or {}
    entity = data.get('entity', 'summary')
    target_bps = float(data.get('target_bps', 0.5))

    eng = get_engine(entity)

    # 如果还没拉过数据，先拉
    if vol_cache is None:
        vol_cache = fetch_all_volatilities(interval=10, days_back=120)

    volumes = {}
    for ccy_info in eng.get_ccy_volumes():
        volumes[ccy_info['ccy']] = ccy_info['volume']

    suggestion = compute_vol_weighted_markups(volumes, vol_cache, target_avg_bps=target_bps)

    # 应用到引擎
    for ccy, info in suggestion['ccys'].items():
        eng.set_ccy_markup(ccy, info['suggested_markup_bps'])

    result = eng.calc_all()
    result['entity'] = entity
    result['vol_suggestion'] = suggestion
    return jsonify({'success': True, **result})


# ─── API: 反算 — 目标收入反推加价方案 ───

def _stealth_optimize(ccy_list, volumes, total_volume, target_monthly_rev, max_bps,
                      randomness=0.0, pinned=None):
    """
    隐蔽式加价优化器：
    - 约束: Σ(volume_i × bps_i) × 1e-4 = target_monthly_rev
    - 约束: 每个币种 0 ≤ bps_i ≤ max_bps
    - 目标: 最小化大币种加价，即让大币种（USD/HKD/MOP）尽可能少加，
            小币种吸收更多加价，但不超过上限。
    - pinned: dict {ccy: fixed_bps} — 锁定某些币种的加价，优化器不调整
    - randomness: 0~1, 在优化结果上添加随机扰动 (占 max_bps 的比例)
    使用 scipy SLSQP 优化器。如果 scipy 不可用则用解析解。
    """
    import numpy as np

    big_ccys = {'USD', 'HKD', 'MOP'}
    n = len(ccy_list)
    vols = np.array([c['volume'] for c in ccy_list])
    is_big = np.array([1.0 if c['ccy'] in big_ccys else 0.0 for c in ccy_list])

    if pinned is None:
        pinned = {}

    # 计算被锁定币种消耗的 revenue
    pinned_revenue = 0.0
    pinned_mask = np.zeros(n, dtype=bool)
    pinned_bps = np.zeros(n)
    for i, c in enumerate(ccy_list):
        if c['ccy'] in pinned:
            pinned_mask[i] = True
            pinned_bps[i] = float(pinned[c['ccy']])
            pinned_revenue += c['volume'] * pinned_bps[i] * 1e-4

    # 剩余需要优化的目标
    remaining_target = target_monthly_rev - pinned_revenue
    target_bps_volume = remaining_target / 1e-4  # = Σ(vol_i × bps_i) for free ccys

    # 自由币种的索引
    free_idx = [i for i in range(n) if not pinned_mask[i]]
    n_free = len(free_idx)

    if n_free == 0 or remaining_target <= 0:
        # 全部被锁定或已满足目标
        result_bps = pinned_bps.copy()
        if remaining_target > 0 and n_free == 0:
            pass  # 无法分配
        return {ccy_list[i]['ccy']: round(float(result_bps[i]), 4) for i in range(n)}

    free_vols = vols[free_idx]
    free_is_big = is_big[free_idx]

    if HAS_SCIPY:
        def objective(x):
            return np.sum(free_vols * x * free_is_big)

        def eq_constraint(x):
            return np.sum(free_vols * x) - target_bps_volume

        x0 = np.full(n_free, target_bps_volume / np.sum(free_vols))
        x0 = np.clip(x0, 0, max_bps)

        bounds = [(0, max_bps) for _ in range(n_free)]
        constraints = [{'type': 'eq', 'fun': eq_constraint}]

        result = minimize(objective, x0, method='SLSQP',
                          bounds=bounds, constraints=constraints,
                          options={'maxiter': 1000, 'ftol': 1e-12})

        if result.success:
            free_bps = result.x
        else:
            free_bps = _stealth_analytical_free(free_idx, vols, free_is_big, target_bps_volume, max_bps, n_free)
    else:
        free_bps = _stealth_analytical_free(free_idx, vols, free_is_big, target_bps_volume, max_bps, n_free)

    free_bps = np.clip(free_bps, 0, max_bps)

    # 添加随机扰动
    if randomness > 0 and n_free > 1:
        noise_scale = randomness * max_bps * 0.15  # 控制噪声幅度
        np.random.seed(None)  # 真随机
        noise = np.random.uniform(-noise_scale, noise_scale, n_free)
        perturbed = free_bps + noise
        perturbed = np.clip(perturbed, 0, max_bps)
        # 修正: 保持总收入不变 — 按交易量加权调整
        actual_bps_vol = np.sum(free_vols * perturbed)
        if actual_bps_vol > 0:
            correction = target_bps_volume / actual_bps_vol
            perturbed = perturbed * correction
            perturbed = np.clip(perturbed, 0, max_bps)
            # 二次修正（clamp 可能破坏总量）
            shortfall = target_bps_volume - np.sum(free_vols * perturbed)
            if abs(shortfall) > 1:
                # 在未触及上限的币种上均匀分摊
                adjustable = [j for j in range(n_free) if perturbed[j] < max_bps * 0.99]
                if adjustable:
                    adj_vol = np.sum(free_vols[adjustable])
                    if adj_vol > 0:
                        perturbed[adjustable] += shortfall / adj_vol
                        perturbed = np.clip(perturbed, 0, max_bps)
        free_bps = perturbed

    # 组装结果
    result_bps = pinned_bps.copy()
    for j, fi in enumerate(free_idx):
        result_bps[fi] = free_bps[j]

    return {ccy_list[i]['ccy']: round(float(result_bps[i]), 4) for i in range(n)}


def _stealth_analytical_free(free_idx, vols, free_is_big, target_bps_volume, max_bps, n_free):
    """解析回退: 小币种先填满到 max_bps，大币种分摊剩余 (仅处理自由币种)"""
    import numpy as np

    bps_arr = np.zeros(n_free)
    remaining = target_bps_volume
    free_vols = vols[free_idx]

    # 第一轮: 小币种从小交易量到大交易量，依次填到 max_bps
    small_indices = [j for j in range(n_free) if free_is_big[j] == 0]
    small_indices.sort(key=lambda j: free_vols[j])
    for j in small_indices:
        fill = min(max_bps, remaining / free_vols[j]) if free_vols[j] > 0 else 0
        bps_arr[j] = max(0, fill)
        remaining -= free_vols[j] * bps_arr[j]

    # 第二轮: 大币种分摊剩余
    big_indices = [j for j in range(n_free) if free_is_big[j] == 1]
    big_vol = sum(free_vols[j] for j in big_indices)
    if big_vol > 0 and remaining > 0:
        big_bps = min(max_bps, remaining / big_vol)
        for j in big_indices:
            bps_arr[j] = max(0, big_bps)

    return bps_arr

@app.route('/api/reverse_calc', methods=['POST'])
def reverse_calc():
    """
    给定目标月增收金额 + 选中的方案列表，反算出加价方案
    selected_plans: ['uniform','vol_weight','big_only','small_only','tiered']
    """
    global vol_cache
    data = request.json or {}
    entity = data.get('entity', 'summary')
    target_monthly_rev = float(data.get('target_monthly_rev', 3_000_000))
    selected = data.get('selected_plans', ['uniform', 'big_only', 'small_only', 'tiered'])
    stealth_max_bps = float(data.get('stealth_max_bps', 20))
    stealth_randomness = float(data.get('stealth_randomness', 0))
    stealth_pinned = data.get('stealth_pinned', {})  # {"EUR": 5.0, "GBP": 3.0, ...}

    eng = get_engine(entity)

    ccy_list = eng.get_ccy_volumes()
    volumes = {c['ccy']: c['volume'] for c in ccy_list}
    total_volume = sum(volumes.values())

    if total_volume == 0:
        return jsonify({'success': False, 'error': 'No volume data'})

    uniform_bps = target_monthly_rev / (total_volume * 1e-4)
    plans = []

    # ═══ 方案 A: 统一加价 ═══
    if 'uniform' in selected:
        plan_a = {
            'id': 'uniform', 'name': '统一加价',
            'desc': '所有币种统一加同一个 BPS',
            'avg_bps': round(uniform_bps, 2),
            'monthly_rev': round(target_monthly_rev, 0),
            'annual_rev': round(target_monthly_rev * 12, 0),
            'ccys': {}
        }
        for c in ccy_list:
            rev = c['volume'] * uniform_bps * 1e-4
            plan_a['ccys'][c['ccy']] = {
                'ccy': c['ccy'], 'volume': c['volume'],
                'volume_pct': round(c['volume'] / total_volume * 100, 2),
                'markup_bps': round(uniform_bps, 2),
                'monthly_revenue': round(rev, 0),
            }
        plans.append(plan_a)

    # ═══ 方案 B: 波动率加权 ═══
    if 'vol_weight' in selected:
        if vol_cache is None:
            plans.append({
                'id': 'vol_weight', 'name': '波动率加权',
                'desc': '⚠️ 需要先到「波动率加权」Tab 拉取 BBG 数据后才能使用此方案',
                'avg_bps': 0, 'monthly_rev': 0, 'annual_rev': 0,
                'ccys': {}, 'needs_vol_data': True,
            })
        else:
            vol_result = compute_vol_weighted_markups(volumes, vol_cache, target_avg_bps=uniform_bps)
            plan_b = {
                'id': 'vol_weight', 'name': '波动率加权',
                'desc': '按波动率比例分配，高波动多加、低波动少加，加权平均 = 统一方案的 BPS',
                'avg_bps': round(vol_result['summary']['actual_weighted_avg_bps'], 2),
                'monthly_rev': round(vol_result['summary']['total_monthly_revenue'], 0),
                'annual_rev': round(vol_result['summary']['total_annual_revenue'], 0),
                'ccys': {}
            }
            for ccy, info in vol_result['ccys'].items():
                plan_b['ccys'][ccy] = {
                    'ccy': ccy, 'volume': info['volume'],
                    'volume_pct': info['volume_pct'],
                    'markup_bps': info['suggested_markup_bps'],
                    'monthly_revenue': round(info['monthly_revenue'], 0),
                    'vol_pct': info.get('realized_vol_pct', 0),
                }
            plans.append(plan_b)

    # ═══ 方案 C: 只加大币种 ═══
    if 'big_only' in selected:
        big_ccys = ['USD', 'HKD', 'EUR', 'MOP']
        big_volume = sum(volumes.get(c, 0) for c in big_ccys)
        big_bps = target_monthly_rev / (big_volume * 1e-4) if big_volume > 0 else 0
        plan_c = {
            'id': 'big_only', 'name': '只加大币种',
            'desc': f'仅对 {",".join(big_ccys)} 加价，其余不加',
            'avg_bps': round(uniform_bps, 2),
            'big_bps': round(big_bps, 2),
            'monthly_rev': round(target_monthly_rev, 0),
            'annual_rev': round(target_monthly_rev * 12, 0),
            'ccys': {}
        }
        for c in ccy_list:
            is_big = c['ccy'] in big_ccys
            bps = big_bps if is_big else 0
            rev = c['volume'] * bps * 1e-4
            plan_c['ccys'][c['ccy']] = {
                'ccy': c['ccy'], 'volume': c['volume'],
                'volume_pct': round(c['volume'] / total_volume * 100, 2),
                'markup_bps': round(bps, 2),
                'monthly_revenue': round(rev, 0),
                'is_big': is_big,
            }
        plans.append(plan_c)

    # ═══ 方案 D: 只加小币种 ═══
    if 'small_only' in selected:
        small_only_ccys = [c['ccy'] for c in ccy_list if c['ccy'] not in ['USD', 'HKD', 'MOP']]
        small_only_volume = sum(volumes.get(c, 0) for c in small_only_ccys)
        small_bps = target_monthly_rev / (small_only_volume * 1e-4) if small_only_volume > 0 else 0
        plan_d = {
            'id': 'small_only', 'name': '只加小币种',
            'desc': 'USD/HKD/MOP 不加，其余币种统一加价',
            'avg_bps': round(uniform_bps, 2),
            'small_bps': round(small_bps, 2),
            'monthly_rev': round(target_monthly_rev, 0),
            'annual_rev': round(target_monthly_rev * 12, 0),
            'ccys': {}
        }
        for c in ccy_list:
            is_small = c['ccy'] in small_only_ccys
            bps = small_bps if is_small else 0
            rev = c['volume'] * bps * 1e-4
            plan_d['ccys'][c['ccy']] = {
                'ccy': c['ccy'], 'volume': c['volume'],
                'volume_pct': round(c['volume'] / total_volume * 100, 2),
                'markup_bps': round(bps, 2),
                'monthly_revenue': round(rev, 0),
                'is_small': is_small,
            }
        plans.append(plan_d)

    # ═══ 方案 E: 阶梯式 ═══
    if 'tiered' in selected:
        stable_ccys = ['USD', 'HKD', 'MOP']
        stable_vol = sum(volumes.get(c, 0) for c in stable_ccys)
        volatile_vol = total_volume - stable_vol
        multiplier = 3
        base_bps = target_monthly_rev / ((stable_vol + multiplier * volatile_vol) * 1e-4) if (stable_vol + multiplier * volatile_vol) > 0 else 0
        plan_e = {
            'id': 'tiered', 'name': '阶梯式加价',
            'desc': f'稳定币种 (USD/HKD/MOP) 加 {round(base_bps,2)} BPS，其余加 {round(base_bps*multiplier,2)} BPS (3倍)',
            'avg_bps': round(uniform_bps, 2),
            'base_bps': round(base_bps, 2),
            'high_bps': round(base_bps * multiplier, 2),
            'monthly_rev': 0, 'annual_rev': 0,
            'ccys': {}
        }
        total_e_rev = 0
        for c in ccy_list:
            is_stable = c['ccy'] in stable_ccys
            bps = base_bps if is_stable else base_bps * multiplier
            rev = c['volume'] * bps * 1e-4
            total_e_rev += rev
            plan_e['ccys'][c['ccy']] = {
                'ccy': c['ccy'], 'volume': c['volume'],
                'volume_pct': round(c['volume'] / total_volume * 100, 2),
                'markup_bps': round(bps, 2),
                'monthly_revenue': round(rev, 0),
                'tier': 'stable' if is_stable else 'volatile',
            }
        plan_e['monthly_rev'] = round(total_e_rev, 0)
        plan_e['annual_rev'] = round(total_e_rev * 12, 0)
        plans.append(plan_e)

    # ═══ 方案 F: 隐蔽式加价 ═══
    if 'stealth' in selected:
        # 清理 pinned: 只保留有效的
        clean_pinned = {}
        for k, v in stealth_pinned.items():
            try:
                bv = float(v)
                if bv >= 0 and k in volumes:
                    clean_pinned[k] = bv
            except (ValueError, TypeError):
                pass

        stealth_bps_map = _stealth_optimize(ccy_list, volumes, total_volume,
                                            target_monthly_rev, stealth_max_bps,
                                            randomness=stealth_randomness,
                                            pinned=clean_pinned)
        big_ccys_set = {'USD', 'HKD', 'MOP'}
        big_avg = 0
        big_vol_sum = sum(volumes.get(c, 0) for c in big_ccys_set)
        small_avg = 0
        small_vol_sum = total_volume - big_vol_sum

        total_f_rev = 0
        pin_desc = f'，锁定 {",".join(clean_pinned.keys())}' if clean_pinned else ''
        rand_desc = f'，随机度 {stealth_randomness:.0%}' if stealth_randomness > 0 else ''
        plan_f = {
            'id': 'stealth', 'name': '隐蔽式加价',
            'desc': f'大币种少加、小币种多加 (上限 {stealth_max_bps} BPS){pin_desc}{rand_desc}',
            'avg_bps': round(uniform_bps, 2),
            'max_bps_cap': stealth_max_bps,
            'randomness': stealth_randomness,
            'pinned': clean_pinned,
            'monthly_rev': 0, 'annual_rev': 0,
            'ccys': {}
        }
        for c in ccy_list:
            bps = stealth_bps_map.get(c['ccy'], 0)
            rev = c['volume'] * bps * 1e-4
            total_f_rev += rev
            is_big = c['ccy'] in big_ccys_set
            if is_big:
                big_avg += c['volume'] * bps
            else:
                small_avg += c['volume'] * bps
            plan_f['ccys'][c['ccy']] = {
                'ccy': c['ccy'], 'volume': c['volume'],
                'volume_pct': round(c['volume'] / total_volume * 100, 2),
                'markup_bps': round(bps, 2),
                'monthly_revenue': round(rev, 0),
                'group': 'big' if is_big else 'small',
                'pinned': c['ccy'] in clean_pinned,
            }
        plan_f['monthly_rev'] = round(total_f_rev, 0)
        plan_f['annual_rev'] = round(total_f_rev * 12, 0)
        plan_f['big_avg_bps'] = round(big_avg / big_vol_sum, 2) if big_vol_sum > 0 else 0
        plan_f['small_avg_bps'] = round(small_avg / small_vol_sum, 2) if small_vol_sum > 0 else 0
        plans.append(plan_f)

    if not plans:
        return jsonify({'success': False, 'error': '请至少选择一种加价方案'})

    return jsonify({
        'success': True,
        'entity': entity,
        'target_monthly_rev': target_monthly_rev,
        'target_annual_rev': target_monthly_rev * 12,
        'total_volume': total_volume,
        'plans': plans,
        'vol_data_available': vol_cache is not None,
    })


@app.route('/api/apply_plan', methods=['POST'])
def apply_plan():
    """应用某个反算方案到引擎"""
    data = request.json or {}
    entity = data.get('entity', 'summary')
    ccy_markups = data.get('ccy_markups', {})

    eng = get_engine(entity)
    for ccy, bps in ccy_markups.items():
        eng.set_ccy_markup(ccy, float(bps))

    result = eng.calc_all()
    result['entity'] = entity
    return jsonify({'success': True, **result})


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8891
    print(f"\n{'='*60}")
    print(f"FX Markup Pricing Dashboard V4")
    print(f"  http://127.0.0.1:{port}")
    print(f"{'='*60}\n")
    app.run(host='0.0.0.0', port=port, debug=True)
