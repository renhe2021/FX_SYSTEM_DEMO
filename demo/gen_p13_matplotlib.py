#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第13页方法论图 - matplotlib 版本"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib
import os

# 中文字体配置
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
matplotlib.rcParams['axes.unicode_minus'] = False

def draw_methodology():
    fig, ax = plt.subplots(1, 1, figsize=(19.2, 9.0), dpi=100)
    fig.patch.set_facecolor('white')
    ax.set_xlim(0, 19.2)
    ax.set_ylim(0, 9.0)
    ax.axis('off')
    ax.set_facecolor('white')

    # ========== 颜色定义 ==========
    GREEN = '#2BA471'
    ORANGE = '#E37318'
    BLUE = '#0052D9'
    GRAY = '#797979'
    DARK = '#1a1a1a'
    LIGHT_ORANGE = '#FFF8F0'
    LIGHT_BLUE = '#F0F8FF'
    LIGHT_GREEN = '#F0FFF4'
    
    # ========== 三张卡片 ==========
    cards = [
        {
            'x': 0.8, 'y': 2.8, 'w': 5.0, 'h': 4.8,
            'border_color': ORANGE, 'fill': LIGHT_ORANGE,
            'num': '①', 'num_color': ORANGE,
            'title': '先把一个场景做透',
            'line1': '从一个具体痛点出发',
            'line2': '跑通一个最小闭环',
            'line2_bold': True,
            'example': '周末预锁价策略\n→ 从数据到回测到出结果',
        },
        {
            'x': 7.1, 'y': 2.8, 'w': 5.0, 'h': 4.8,
            'border_color': BLUE, 'fill': LIGHT_BLUE,
            'num': '②', 'num_color': BLUE,
            'title': '拆出可复用的零件',
            'line1': '哪些模块换个参数就能用？',
            'line2': '',
            'line2_bold': False,
            'example': '',
            'modules': ['数据获取', '信号生成', '回测引擎', '结果输出'],
        },
        {
            'x': 13.4, 'y': 2.8, 'w': 5.0, 'h': 4.8,
            'border_color': GREEN, 'fill': LIGHT_GREEN,
            'num': '③', 'num_color': GREEN,
            'title': '抽象成框架',
            'line1': '把「策略」变成接口',
            'line2': '新场景只需实现接口',
            'line2_bold': True,
            'example': '换一个策略 → 只改信号逻辑\n→ 引擎、可视化全部复用',
        },
    ]
    
    for card in cards:
        x, y, w, h = card['x'], card['y'], card['w'], card['h']
        
        # 卡片背景
        rect = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0,rounding_size=0.15",
            facecolor=card['fill'], edgecolor='#E0E0E0', linewidth=1.2
        )
        ax.add_patch(rect)
        
        # 顶部色条
        top_bar = FancyBboxPatch(
            (x, y + h - 0.08), w, 0.08,
            boxstyle="square,pad=0",
            facecolor=card['border_color'], edgecolor='none'
        )
        ax.add_patch(top_bar)
        
        cx = x + w / 2
        
        # 序号圆圈
        circle = plt.Circle((cx, y + h - 0.65), 0.35, 
                            facecolor=card['num_color'] + '18', 
                            edgecolor=card['num_color'], linewidth=1.5)
        ax.add_patch(circle)
        ax.text(cx, y + h - 0.65, card['num'], fontsize=22, fontweight='bold',
                color=card['num_color'], ha='center', va='center')
        
        # 标题
        ax.text(cx, y + h - 1.4, card['title'], fontsize=22, fontweight='bold',
                color=DARK, ha='center', va='center')
        
        # 正文第一行
        ax.text(cx, y + h - 2.0, card['line1'], fontsize=16, 
                color=GRAY, ha='center', va='center')
        
        # 正文第二行（加粗）
        if card['line2']:
            ax.text(cx, y + h - 2.5, card['line2'], fontsize=16,
                    fontweight='bold' if card['line2_bold'] else 'normal',
                    color=GREEN if card['line2_bold'] else GRAY,
                    ha='center', va='center')
        
        # 模块标签（卡片2专用）
        if 'modules' in card:
            mods = card['modules']
            mod_y = y + 1.4
            for i, mod in enumerate(mods):
                mx = cx - 1.4 + (i % 2) * 2.8
                my = mod_y + (1 - i // 2) * 0.65
                pill = FancyBboxPatch(
                    (mx - 1.1, my - 0.22), 2.2, 0.44,
                    boxstyle="round,pad=0,rounding_size=0.1",
                    facecolor=BLUE + '15', edgecolor=BLUE + '60', linewidth=1
                )
                ax.add_patch(pill)
                ax.text(mx, my, mod, fontsize=14, color=BLUE, 
                        ha='center', va='center', fontweight='600')
        
        # 底部示例文字
        if card.get('example'):
            example_y = y + 0.65
            example_bg = FancyBboxPatch(
                (x + 0.3, y + 0.2), w - 0.6, 0.9,
                boxstyle="round,pad=0,rounding_size=0.08",
                facecolor='#00000008', edgecolor='none'
            )
            ax.add_patch(example_bg)
            ax.text(cx, example_y, card['example'], fontsize=12, 
                    color='#999999', ha='center', va='center',
                    fontstyle='italic', linespacing=1.3)
    
    # ========== 箭头连接 ==========
    arrow_style = dict(arrowstyle='->', color=GREEN, lw=2.5, 
                        connectionstyle='arc3,rad=0')
    
    # 卡片1 → 卡片2
    ax.annotate('', xy=(7.1, 5.2), xytext=(5.8, 5.2),
                arrowprops=arrow_style)
    
    # 卡片2 → 卡片3  
    ax.annotate('', xy=(13.4, 5.2), xytext=(12.1, 5.2),
                arrowprops=arrow_style)
    
    # ========== 底部公式条 ==========
    formula_y = 1.2
    formula_bg = FancyBboxPatch(
        (0.8, formula_y - 0.55), 17.6, 1.1,
        boxstyle="round,pad=0,rounding_size=0.12",
        facecolor='#F0FFF4', edgecolor='#C8E6D5', linewidth=1.5
    )
    ax.add_patch(formula_bg)
    
    # 彩色标签
    tags = [
        ('具体问题', '#E34D59', '#FFF0F0'),
        ('最小闭环', ORANGE, '#FFF8F0'),
        ('拆模块', GREEN, '#F0FFF4'),
        ('抽框架', BLUE, '#F0F0FF'),
    ]
    
    tag_x = 1.5
    for i, (text, color, bg) in enumerate(tags):
        tw = len(text) * 0.38 + 0.6
        pill = FancyBboxPatch(
            (tag_x, formula_y - 0.22), tw, 0.44,
            boxstyle="round,pad=0,rounding_size=0.08",
            facecolor=bg, edgecolor=color + '60', linewidth=1
        )
        ax.add_patch(pill)
        ax.text(tag_x + tw / 2, formula_y, text, fontsize=15, fontweight='600',
                color=color, ha='center', va='center')
        tag_x += tw + 0.15
        
        # 小箭头
        if i < 3:
            ax.annotate('', xy=(tag_x + 0.35, formula_y),
                        xytext=(tag_x, formula_y),
                        arrowprops=dict(arrowstyle='->', color='#999', lw=1.5))
            tag_x += 0.55
    
    # 等号 + 总结文字
    ax.text(tag_x + 0.5, formula_y, '=', fontsize=20, color=GRAY,
            ha='center', va='center')
    
    ax.text(tag_x + 1.0, formula_y, '通用性', fontsize=18, fontweight='bold',
            color=GREEN, ha='left', va='center')
    ax.text(tag_x + 2.5, formula_y, '不是设计出来的，是从实践中', fontsize=16,
            color='#555', ha='left', va='center')
    ax.text(tag_x + 6.3, formula_y, '长', fontsize=18, fontweight='bold',
            color=GREEN, ha='left', va='center')
    ax.text(tag_x + 6.8, formula_y, '出来的', fontsize=16,
            color='#555', ha='left', va='center')
    
    plt.tight_layout(pad=0.2)
    
    output_path = os.path.join(os.path.dirname(__file__), 
                               'slides-v2', 'assets', 'media', 'p13-methodology-mpl.png')
    plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='white',
                edgecolor='none', pad_inches=0.1)
    plt.close()
    print(f"Done: {output_path}")
    return output_path

if __name__ == '__main__':
    draw_methodology()
