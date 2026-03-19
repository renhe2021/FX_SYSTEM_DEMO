"""
生成 P9 (Strategy Lab 架构设计) 和 P10 (策略示例：周末预锁价) 的架构图
输出到 slides-v2/assets/media/ 下
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import os
import numpy as np

# === 字体设置 ===
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'STHeiti', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

output_dir = os.path.join(os.path.dirname(__file__), 'slides-v2', 'assets', 'media')
os.makedirs(output_dir, exist_ok=True)

# ============================================================
# 配色方案 (与 slides-v2 保持一致)
# ============================================================
BLUE = '#0052D9'
GREEN = '#2BA471'
PURPLE = '#7B61FF'
ORANGE = '#E37318'
RED = '#E34D59'
DARK = '#1a1a1a'
GRAY = '#797979'
LIGHT_BG = '#F8F9FD'


def draw_rounded_box(ax, x, y, w, h, header_text, header_color, title, items,
                     radius=0.15, bg='#FFFFFF', border_color='#d0d7de'):
    """绘制带圆角的卡片，顶部有彩色小标签"""
    # 主体白色卡片
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle=f"round,pad=0,rounding_size={radius}",
                         facecolor=bg, edgecolor=border_color, linewidth=1.5,
                         zorder=2)
    ax.add_patch(box)
    # 添加轻微阴影效果
    shadow = FancyBboxPatch((x + 0.02, y - 0.02), w, h,
                            boxstyle=f"round,pad=0,rounding_size={radius}",
                            facecolor='#00000008', edgecolor='none',
                            zorder=1)
    ax.add_patch(shadow)

    # 顶部小标签
    tag_w = len(header_text) * 0.18 + 0.3
    tag_h = 0.28
    tag_x = x + 0.15
    tag_y = y + h - 0.15 - tag_h
    tag = FancyBboxPatch((tag_x, tag_y), tag_w, tag_h,
                         boxstyle="round,pad=0,rounding_size=0.06",
                         facecolor=header_color, edgecolor='none', zorder=3)
    ax.add_patch(tag)
    ax.text(tag_x + tag_w / 2, tag_y + tag_h / 2, header_text,
            fontsize=9, fontweight='bold', color='white',
            ha='center', va='center', zorder=4,
            fontfamily='Microsoft YaHei')

    # 标题
    ax.text(x + 0.15, tag_y - 0.15, title,
            fontsize=14, fontweight='bold', color=DARK,
            ha='left', va='top', zorder=3,
            fontfamily='Microsoft YaHei')

    # 列表项
    for i, item in enumerate(items):
        bullet_y = tag_y - 0.52 - i * 0.28
        # 小圆点
        ax.plot(x + 0.25, bullet_y + 0.05, 'o', color=header_color,
                markersize=4, zorder=3)
        ax.text(x + 0.4, bullet_y + 0.05, item,
                fontsize=10, color='#555555', ha='left', va='center', zorder=3,
                fontfamily='Microsoft YaHei')


def draw_pipeline_box(ax, x, y, w, h, header_text, title, subtitle, header_color=GREEN):
    """绘制流水线中的小卡片"""
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle="round,pad=0,rounding_size=0.1",
                         facecolor='#FFFFFF', edgecolor='#d0d7de',
                         linewidth=1.5, zorder=2)
    ax.add_patch(box)

    # 小标签
    tag_w = len(header_text) * 0.15 + 0.25
    tag_h = 0.24
    tag_x = x + (w - tag_w) / 2
    tag_y = y + h - 0.12 - tag_h
    tag = FancyBboxPatch((tag_x, tag_y), tag_w, tag_h,
                         boxstyle="round,pad=0,rounding_size=0.05",
                         facecolor=header_color, edgecolor='none', zorder=3)
    ax.add_patch(tag)
    ax.text(tag_x + tag_w / 2, tag_y + tag_h / 2, header_text,
            fontsize=8, fontweight='bold', color='white',
            ha='center', va='center', zorder=4,
            fontfamily='Microsoft YaHei')

    # 标题
    ax.text(x + w / 2, tag_y - 0.2, title,
            fontsize=12, fontweight='bold', color=DARK,
            ha='center', va='top', zorder=3,
            fontfamily='Microsoft YaHei')

    # 副标题
    ax.text(x + w / 2, tag_y - 0.52, subtitle,
            fontsize=9, color='#666666', ha='center', va='top', zorder=3,
            fontfamily='Microsoft YaHei', linespacing=1.4)


def draw_arrow(ax, x1, y1, x2, y2, color=GREEN, lw=2):
    """绘制箭头"""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                connectionstyle='arc3,rad=0'),
                zorder=5)


# ============================================================
# P9: Strategy Lab — 架构设计（美化版，无白边）
# ============================================================
def _gradient_bar(ax, x, y, w, h, color_left, color_right, radius=0.08, n=100):
    """绘制水平渐变色圆角条"""
    from matplotlib.colors import to_rgba
    c1, c2 = np.array(to_rgba(color_left)), np.array(to_rgba(color_right))
    for i in range(n):
        xi = x + w * i / n
        wi = w / n + 0.01  # slight overlap
        c = c1 + (c2 - c1) * i / n
        ax.add_patch(FancyBboxPatch(
            (xi, y), wi, h,
            boxstyle=f"round,pad=0,rounding_size={radius if (i == 0 or i == n-1) else 0.001}",
            facecolor=c, edgecolor='none', zorder=3, clip_on=True))


def _draw_input_card(ax, x, y, w, h, tag_text, tag_color, tag_color2,
                     title, items, icon_char='●'):
    """绘制上层输入模块卡片（带顶部渐变色带 + 阴影）"""
    from matplotlib.colors import to_rgba
    # 卡片阴影
    shadow = FancyBboxPatch((x + 0.06, y - 0.06), w, h,
                            boxstyle="round,pad=0,rounding_size=0.18",
                            facecolor='#00000015', edgecolor='none', zorder=1)
    ax.add_patch(shadow)
    # 主卡片
    card = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0,rounding_size=0.18",
                          facecolor='#FFFFFF', edgecolor='#E0E4E9', linewidth=1.8,
                          zorder=2)
    ax.add_patch(card)
    # 顶部渐变色带（覆盖在卡片顶部）
    bar_h = 0.13
    c1, c2 = np.array(to_rgba(tag_color)), np.array(to_rgba(tag_color2))
    n_seg = 60
    for i in range(n_seg):
        xi = x + w * i / n_seg
        wi = w / n_seg + 0.02
        c = c1 + (c2 - c1) * i / n_seg
        ax.add_patch(plt.Rectangle((xi, y + h - bar_h), wi, bar_h,
                     facecolor=c, edgecolor='none', zorder=3, clip_on=True))

    # 标签胶囊
    tag_w = len(tag_text) * 0.24 + 0.5
    tag_h = 0.40
    tag_x = x + 0.3
    tag_y_pos = y + h - bar_h - 0.12 - tag_h
    tag = FancyBboxPatch((tag_x, tag_y_pos), tag_w, tag_h,
                         boxstyle="round,pad=0,rounding_size=0.10",
                         facecolor=tag_color, edgecolor='none', zorder=4)
    ax.add_patch(tag)
    ax.text(tag_x + tag_w / 2, tag_y_pos + tag_h / 2, tag_text,
            fontsize=11, fontweight='bold', color='white',
            ha='center', va='center', zorder=5,
            fontfamily='Microsoft YaHei')

    # 标题
    ax.text(x + 0.3, tag_y_pos - 0.15, title,
            fontsize=22, fontweight='bold', color=DARK,
            ha='left', va='top', zorder=4,
            fontfamily='Microsoft YaHei')

    # 列表项（更大的字体和间距）
    for i, item in enumerate(items):
        by = tag_y_pos - 0.72 - i * 0.42
        ax.plot(x + 0.45, by + 0.06, 'o', color=tag_color, markersize=6, zorder=4)
        ax.text(x + 0.72, by + 0.06, item,
                fontsize=14.5, color='#3A3A3A', ha='left', va='center', zorder=4,
                fontfamily='Microsoft YaHei')


def _draw_pipe_card(ax, x, y, w, h, tag_text, title, subtitle, color=GREEN, idx=0):
    """绘制流水线卡片（带编号圆圈 + 顶部色条）"""
    # 阴影
    shadow = FancyBboxPatch((x + 0.04, y - 0.04), w, h,
                            boxstyle="round,pad=0,rounding_size=0.14",
                            facecolor='#00000010', edgecolor='none', zorder=1)
    ax.add_patch(shadow)
    # 主卡片
    card = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0,rounding_size=0.14",
                          facecolor='#FFFFFF', edgecolor='#E0E5EA', linewidth=1.5,
                          zorder=2)
    ax.add_patch(card)
    # 顶部色条
    bar = FancyBboxPatch((x, y + h - 0.10), w, 0.10,
                         boxstyle="square,pad=0",
                         facecolor=color, edgecolor='none', zorder=3, clip_on=True)
    ax.add_patch(bar)

    # 编号圆圈
    cx, cy = x + w / 2, y + h - 0.5
    num_circle = plt.Circle((cx, cy), 0.3, color=color, zorder=4)
    ax.add_patch(num_circle)
    ax.text(cx, cy, str(idx + 1),
            fontsize=15, fontweight='bold', color='white',
            ha='center', va='center', zorder=5,
            fontfamily='Microsoft YaHei')

    # 标题
    ax.text(x + w / 2, cy - 0.48, title,
            fontsize=16, fontweight='bold', color=DARK,
            ha='center', va='top', zorder=4,
            fontfamily='Microsoft YaHei')

    # 副标题
    ax.text(x + w / 2, cy - 0.95, subtitle,
            fontsize=11.5, color='#666666', ha='center', va='top', zorder=4,
            fontfamily='Microsoft YaHei', linespacing=1.5)


def generate_p9():
    fig, ax = plt.subplots(figsize=(15, 7.5), dpi=200)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 7.5)
    ax.axis('off')
    fig.patch.set_alpha(0)
    ax.set_facecolor('none')
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # ---- 上层：两个平行输入模块 ----
    box_w, box_h = 6.2, 3.0

    # 数据获取 (蓝色) — 左侧
    _draw_input_card(ax, 0.3, 4.2, box_w, box_h,
                     'MARKET DATA', BLUE, '#3B7DED',
                     '数据获取',
                     ['Bloomberg API 实时拉取',
                      '本地数据库 + Cron Job 定时同步',
                      '数据清洗 · 缺失值 · 对齐 · 标准化'])

    # 信号生成 (紫色) — 右侧
    _draw_input_card(ax, 8.5, 4.2, box_w, box_h,
                     'SIGNAL', PURPLE, '#9B85FF',
                     '信号生成',
                     ['技术指标 / 统计模型',
                      '自定义因子',
                      '输出买卖信号序列'])

    # ---- 汇合箭头 ----
    merge_x = 7.5
    merge_y = 3.6

    # 左路：数据获取底部中心 → 汇合点
    data_cx = 0.3 + box_w / 2
    draw_arrow(ax, data_cx, 4.2, merge_x - 0.15, merge_y + 0.18, GREEN, 3)
    # 右路：信号生成底部中心 → 汇合点
    signal_cx = 8.5 + box_w / 2
    draw_arrow(ax, signal_cx, 4.2, merge_x + 0.15, merge_y + 0.18, GREEN, 3)

    # 汇合点 — 双圈设计
    merge_outer = plt.Circle((merge_x, merge_y), 0.28, color='#D4F0E2', zorder=5)
    ax.add_patch(merge_outer)
    merge_inner = plt.Circle((merge_x, merge_y), 0.18, color=GREEN, zorder=6)
    ax.add_patch(merge_inner)

    # ---- 下层：线性流水线 4 步 ----
    pipe_w = 3.0
    pipe_h = 2.4
    pipe_y = 0.5
    pipe_gap = 0.5
    total_pipe_w = 4 * pipe_w + 3 * pipe_gap
    pipe_start_x = (15 - total_pipe_w) / 2

    pipes = [
        ('TRADE', '交易构建', '开平仓规则\n仓位管理 · 止损'),
        ('ENGINE', '计算引擎', '回测核心\n网格参数扫描'),
        ('OUTPUT', '结果输出', '净值 · Sharpe\n胜率 · 最大回撤'),
        ('VIZ', '可视化分析', '热力图 · 月度归因\n风险报表'),
    ]

    for i, (tag, title, sub) in enumerate(pipes):
        px = pipe_start_x + i * (pipe_w + pipe_gap)
        _draw_pipe_card(ax, px, pipe_y, pipe_w, pipe_h, tag, title, sub, GREEN, i)
        if i < len(pipes) - 1:
            arr_x1 = px + pipe_w + 0.06
            arr_x2 = px + pipe_w + pipe_gap - 0.06
            arr_y = pipe_y + pipe_h / 2
            ax.annotate('', xy=(arr_x2, arr_y), xytext=(arr_x1, arr_y),
                        arrowprops=dict(arrowstyle='->', color=GREEN, lw=2.5,
                                        mutation_scale=18),
                        zorder=5)

    # 从汇合点到流水线 — L型折线
    first_pipe_cx = pipe_start_x + pipe_w / 2
    pipe_top = pipe_y + pipe_h
    turn_y = pipe_top + 0.25

    ax.plot([merge_x, merge_x], [merge_y - 0.28, turn_y],
            color=GREEN, linewidth=3, zorder=5, solid_capstyle='round')
    ax.plot([merge_x, first_pipe_cx], [turn_y, turn_y],
            color=GREEN, linewidth=3, zorder=5, solid_capstyle='round')
    ax.annotate('', xy=(first_pipe_cx, pipe_top + 0.02),
                xytext=(first_pipe_cx, turn_y),
                arrowprops=dict(arrowstyle='->', color=GREEN, lw=3,
                                mutation_scale=18),
                zorder=5)

    # ---- 底部注释 ----
    ax.text(7.5, 0.15, '通用架构 —— 换策略只需替换  信号生成  和  交易构建  模块，其余全部复用',
            fontsize=12, color='#5A6872', ha='center', va='center',
            fontfamily='Microsoft YaHei', fontstyle='italic')

    out_path = os.path.join(output_dir, 'p10-architecture.png')
    fig.savefig(out_path, dpi=200, bbox_inches='tight', pad_inches=0.02,
                facecolor='none', edgecolor='none')
    plt.close(fig)
    print(f"P10 (architecture) saved: {out_path}")
    return out_path


# ============================================================
# P9: 策略示例 — 周末预锁价（完整策略说明）
# ============================================================
def generate_p9_strategy():
    """新 P9：讲清楚策略本身 — 模型信号 + 交易参数 + 参数爆炸 → 回测寻优"""
    fig, ax = plt.subplots(figsize=(15, 8), dpi=200)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8)
    ax.axis('off')
    fig.patch.set_alpha(0)
    ax.set_facecolor('none')
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # ========== 颜色 ==========
    SIGNAL_BLUE = '#3478F6'
    SIGNAL_BLUE2 = '#5B9BFF'
    TRADE_GREEN = '#2BA471'
    TRADE_GREEN2 = '#5ED4A5'
    EXPLODE_ORANGE = '#F5A623'
    RESULT_PURPLE = '#7C5CFC'

    from matplotlib.colors import to_rgba

    # ========== 顶部故事条 ==========
    # 浅背景条
    story_bg = FancyBboxPatch((0.2, 7.15), 14.6, 0.65,
                               boxstyle="round,pad=0,rounding_size=0.12",
                               facecolor='#EEF3FF', edgecolor='#D0DDFF',
                               linewidth=1.2, zorder=1)
    ax.add_patch(story_bg)
    ax.text(7.5, 7.47, '周五晚间模型预测外币涨跌  →  决定是否提前锁定风险  →  但参数怎么选？',
            fontsize=14, fontweight='bold', color='#333333',
            ha='center', va='center', zorder=2,
            fontfamily='Microsoft YaHei')

    # ================================================================
    # 左侧：模型信号端
    # ================================================================
    left_x, left_y = 0.3, 2.9
    left_w, left_h = 5.8, 3.9

    # 卡片阴影 + 主体
    shadow = FancyBboxPatch((left_x + 0.06, left_y - 0.06), left_w, left_h,
                            boxstyle="round,pad=0,rounding_size=0.18",
                            facecolor='#00000012', edgecolor='none', zorder=1)
    ax.add_patch(shadow)
    card = FancyBboxPatch((left_x, left_y), left_w, left_h,
                          boxstyle="round,pad=0,rounding_size=0.18",
                          facecolor='#FFFFFF', edgecolor='#D8E2EE', linewidth=1.8,
                          zorder=2)
    ax.add_patch(card)

    # 顶部渐变色带
    n_seg = 50
    c1, c2 = np.array(to_rgba(SIGNAL_BLUE)), np.array(to_rgba(SIGNAL_BLUE2))
    for i in range(n_seg):
        xi = left_x + left_w * i / n_seg
        wi = left_w / n_seg + 0.02
        c = c1 + (c2 - c1) * i / n_seg
        ax.add_patch(plt.Rectangle((xi, left_y + left_h - 0.12), wi, 0.12,
                     facecolor=c, edgecolor='none', zorder=3, clip_on=True))

    # 标题区
    ax.text(left_x + left_w / 2, left_y + left_h - 0.45, '模型信号端',
            fontsize=20, fontweight='bold', color=SIGNAL_BLUE,
            ha='center', va='center', zorder=4,
            fontfamily='Microsoft YaHei')

    # 核心问题
    ax.text(left_x + left_w / 2, left_y + left_h - 0.85,
            '核心：预测周五晚外币涨跌方向',
            fontsize=13, color='#555555', ha='center', va='center', zorder=4,
            fontfamily='Microsoft YaHei')

    # 分隔线
    ax.plot([left_x + 0.4, left_x + left_w - 0.4],
            [left_y + left_h - 1.1, left_y + left_h - 1.1],
            color='#E8EDF3', linewidth=1.5, zorder=3)

    # 参数1: 信号强弱
    p1_y = left_y + left_h - 1.65
    p1_box = FancyBboxPatch((left_x + 0.3, p1_y - 0.25), left_w - 0.6, 0.75,
                             boxstyle="round,pad=0,rounding_size=0.10",
                             facecolor='#F0F6FF', edgecolor='#C5D9F5', linewidth=1.2,
                             zorder=3)
    ax.add_patch(p1_box)
    ax.text(left_x + 0.55, p1_y + 0.12, '参数 ①',
            fontsize=11, fontweight='bold', color=SIGNAL_BLUE,
            ha='left', va='center', zorder=4, fontfamily='Microsoft YaHei')
    ax.text(left_x + 1.5, p1_y + 0.12, '信号强弱（置信度阈值）',
            fontsize=13, fontweight='bold', color=DARK,
            ha='left', va='center', zorder=4, fontfamily='Microsoft YaHei')
    ax.text(left_x + 0.55, p1_y - 0.13, '模型输出信号的强度，越强代表模型越有把握',
            fontsize=11, color='#666666', ha='left', va='center', zorder=4,
            fontfamily='Microsoft YaHei')

    # 参数2: 二次确认
    p2_y = p1_y - 1.05
    p2_box = FancyBboxPatch((left_x + 0.3, p2_y - 0.25), left_w - 0.6, 0.75,
                             boxstyle="round,pad=0,rounding_size=0.10",
                             facecolor='#F0F6FF', edgecolor='#C5D9F5', linewidth=1.2,
                             zorder=3)
    ax.add_patch(p2_box)
    ax.text(left_x + 0.55, p2_y + 0.12, '参数 ②',
            fontsize=11, fontweight='bold', color=SIGNAL_BLUE,
            ha='left', va='center', zorder=4, fontfamily='Microsoft YaHei')
    ax.text(left_x + 1.5, p2_y + 0.12, '二次确认（价格验证窗口）',
            fontsize=13, fontweight='bold', color=DARK,
            ha='left', va='center', zorder=4, fontfamily='Microsoft YaHei')
    ax.text(left_x + 0.55, p2_y - 0.13, '信号发出后，观察市场行情再确认是否执行',
            fontsize=11, color='#666666', ha='left', va='center', zorder=4,
            fontfamily='Microsoft YaHei')

    # ================================================================
    # 右侧：交易执行端
    # ================================================================
    right_x, right_y = 6.6, 2.9
    right_w, right_h = 5.8, 3.9

    # 阴影 + 主体
    shadow2 = FancyBboxPatch((right_x + 0.06, right_y - 0.06), right_w, right_h,
                             boxstyle="round,pad=0,rounding_size=0.18",
                             facecolor='#00000012', edgecolor='none', zorder=1)
    ax.add_patch(shadow2)
    card2 = FancyBboxPatch((right_x, right_y), right_w, right_h,
                           boxstyle="round,pad=0,rounding_size=0.18",
                           facecolor='#FFFFFF', edgecolor='#D0E6DA', linewidth=1.8,
                           zorder=2)
    ax.add_patch(card2)

    # 顶部渐变色带
    c3, c4 = np.array(to_rgba(TRADE_GREEN)), np.array(to_rgba(TRADE_GREEN2))
    for i in range(n_seg):
        xi = right_x + right_w * i / n_seg
        wi = right_w / n_seg + 0.02
        c = c3 + (c4 - c3) * i / n_seg
        ax.add_patch(plt.Rectangle((xi, right_y + right_h - 0.12), wi, 0.12,
                     facecolor=c, edgecolor='none', zorder=3, clip_on=True))

    # 标题
    ax.text(right_x + right_w / 2, right_y + right_h - 0.45, '交易执行端',
            fontsize=20, fontweight='bold', color=TRADE_GREEN,
            ha='center', va='center', zorder=4,
            fontfamily='Microsoft YaHei')

    ax.text(right_x + right_w / 2, right_y + right_h - 0.85,
            '核心：5000万美金怎么做？',
            fontsize=13, color='#555555', ha='center', va='center', zorder=4,
            fontfamily='Microsoft YaHei')

    # 分隔线
    ax.plot([right_x + 0.4, right_x + right_w - 0.4],
            [right_y + right_h - 1.1, right_y + right_h - 1.1],
            color='#D8EDE0', linewidth=1.5, zorder=3)

    # 参数列表 — 更紧凑排列
    params = [
        ('头寸规模', '总量多少？5000万全做还是部分？'),
        ('执行方式', '一次性做完，还是分多笔拆单？'),
        ('分配策略', '每次预测怎么分配仓位？'),
        ('止损线', '亏多少必须砍仓？'),
        ('止盈线', '赚多少该落袋为安？'),
    ]

    for i, (name, desc) in enumerate(params):
        py = right_y + right_h - 1.4 - i * 0.52
        # 序号圆点
        ax.plot(right_x + 0.45, py, 'o', color=TRADE_GREEN, markersize=7, zorder=4)
        ax.text(right_x + 0.45, py, str(i + 1),
                fontsize=8, fontweight='bold', color='white',
                ha='center', va='center', zorder=5,
                fontfamily='Microsoft YaHei')
        # 参数名
        ax.text(right_x + 0.75, py, name,
                fontsize=13, fontweight='bold', color=DARK,
                ha='left', va='center', zorder=4,
                fontfamily='Microsoft YaHei')
        # 描述
        ax.text(right_x + 2.0, py, desc,
                fontsize=11, color='#666666',
                ha='left', va='center', zorder=4,
                fontfamily='Microsoft YaHei')

    # ================================================================
    # 右侧小面板：参数组合爆炸
    # ================================================================
    boom_x, boom_y = 12.8, 3.9
    boom_w, boom_h = 2.0, 2.9

    # 阴影 + 主体
    shadow3 = FancyBboxPatch((boom_x + 0.04, boom_y - 0.04), boom_w, boom_h,
                             boxstyle="round,pad=0,rounding_size=0.14",
                             facecolor='#00000010', edgecolor='none', zorder=1)
    ax.add_patch(shadow3)
    card3 = FancyBboxPatch((boom_x, boom_y), boom_w, boom_h,
                           boxstyle="round,pad=0,rounding_size=0.14",
                           facecolor='#FFF8EE', edgecolor='#F5D9A0', linewidth=1.8,
                           zorder=2)
    ax.add_patch(card3)

    # 顶部色条
    ax.add_patch(plt.Rectangle((boom_x, boom_y + boom_h - 0.10), boom_w, 0.10,
                 facecolor=EXPLODE_ORANGE, edgecolor='none', zorder=3, clip_on=True))

    ax.text(boom_x + boom_w / 2, boom_y + boom_h - 0.45, '!',
            fontsize=28, fontweight='bold', color=EXPLODE_ORANGE,
            ha='center', va='center', zorder=4,
            fontfamily='Microsoft YaHei')
    ax.text(boom_x + boom_w / 2, boom_y + boom_h - 0.9, '参数组合',
            fontsize=14, fontweight='bold', color=EXPLODE_ORANGE,
            ha='center', va='center', zorder=4,
            fontfamily='Microsoft YaHei')
    ax.text(boom_x + boom_w / 2, boom_y + boom_h - 1.2, '爆 炸',
            fontsize=14, fontweight='bold', color=EXPLODE_ORANGE,
            ha='center', va='center', zorder=4,
            fontfamily='Microsoft YaHei')

    # 数字
    ax.text(boom_x + boom_w / 2, boom_y + boom_h - 1.8, '10,000+',
            fontsize=22, fontweight='bold', color='#E8850C',
            ha='center', va='center', zorder=4,
            fontfamily='Microsoft YaHei')
    ax.text(boom_x + boom_w / 2, boom_y + boom_h - 2.15, '种组合',
            fontsize=12, color='#999999',
            ha='center', va='center', zorder=4,
            fontfamily='Microsoft YaHei')

    # ================================================================
    # 中间合流箭头 → 底部结论条
    # ================================================================
    # 从左右两个卡片底部中心合流到底部
    left_cx = left_x + left_w / 2
    right_cx = right_x + right_w / 2
    merge_y_pos = 2.5

    # 左箭头向下
    ax.annotate('', xy=(7.5 - 0.8, merge_y_pos + 0.15),
                xytext=(left_cx, left_y),
                arrowprops=dict(arrowstyle='->', color='#AABBCC', lw=2.5,
                                mutation_scale=16),
                zorder=4)
    # 右箭头向下
    ax.annotate('', xy=(7.5 + 0.8, merge_y_pos + 0.15),
                xytext=(right_cx, right_y),
                arrowprops=dict(arrowstyle='->', color='#A0D4B8', lw=2.5,
                                mutation_scale=16),
                zorder=4)
    # 参数爆炸箭头
    ax.annotate('', xy=(boom_x - 0.05, boom_y + boom_h / 2),
                xytext=(right_x + right_w + 0.05, boom_y + boom_h / 2),
                arrowprops=dict(arrowstyle='->', color=EXPLODE_ORANGE, lw=2,
                                mutation_scale=14),
                zorder=4)

    # ================================================================
    # 底部结论条：回测 + 统计验证
    # ================================================================
    bottom_y = 1.4
    bottom_h = 1.05

    # 主结论条
    conclusion_bg = FancyBboxPatch((0.3, bottom_y), 14.4, bottom_h,
                                   boxstyle="round,pad=0,rounding_size=0.14",
                                   facecolor='#F5F0FF', edgecolor='#D4C5FF',
                                   linewidth=1.8, zorder=2)
    ax.add_patch(conclusion_bg)

    # 左侧标记
    verify_circle = plt.Circle((1.3, bottom_y + bottom_h / 2), 0.28,
                                color=RESULT_PURPLE, zorder=4)
    ax.add_patch(verify_circle)
    ax.text(1.3, bottom_y + bottom_h / 2, 'V',
            fontsize=16, fontweight='bold', color='white',
            ha='center', va='center', zorder=5,
            fontfamily='Microsoft YaHei')

    ax.text(2.0, bottom_y + bottom_h / 2 + 0.15,
            '回测 + 统计验证  →  从海量组合中筛选最优参数',
            fontsize=15, fontweight='bold', color=RESULT_PURPLE,
            ha='left', va='center', zorder=4,
            fontfamily='Microsoft YaHei')
    ax.text(2.0, bottom_y + bottom_h / 2 - 0.22,
            '不仅要找到最好的模型和参数组合，还要验证它的收益、Sharpe、胜率、最大回撤等核心指标',
            fontsize=11, color='#666666',
            ha='left', va='center', zorder=4,
            fontfamily='Microsoft YaHei')

    # ================================================================
    # 最底部金句
    # ================================================================
    ax.text(7.5, 0.7,
            '模型 × 参数 × 执行  =  海量组合  →  只有系统化回测才能找到最优解',
            fontsize=13, fontweight='bold', color='#5A6872',
            ha='center', va='center', zorder=4,
            fontfamily='Microsoft YaHei', fontstyle='italic')

    out_path = os.path.join(output_dir, 'p9-strategy-example.png')
    fig.savefig(out_path, dpi=200, bbox_inches='tight', pad_inches=0.02,
                facecolor='none', edgecolor='none')
    plt.close(fig)
    print(f"P9 (strategy) saved: {out_path}")
    return out_path


if __name__ == '__main__':
    p9 = generate_p9_strategy()
    p10 = generate_p9()
    print("Done!")
