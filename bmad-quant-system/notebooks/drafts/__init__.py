"""
草稿绘图管理模块

每个临时可视化需求作为独立的 Jupyter Notebook 管理。

结构:
    drafts/
    ├── __init__.py              # 本文件，提供管理工具
    ├── data/                    # 共享数据目录
    │   └── ...
    ├── draft_001_xxx.ipynb      # 草稿 Notebook
    ├── draft_002_xxx.ipynb
    └── archive/                 # 归档目录

使用方法:
    from notebooks.drafts import create_draft, list_drafts
    
    # 创建新草稿
    create_draft("分析USDCNH价差")
    
    # 列出所有草稿
    list_drafts()
"""
import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

# 草稿目录
DRAFTS_DIR = Path(__file__).parent
SHARED_DATA_DIR = DRAFTS_DIR / "data"


def _get_next_id() -> int:
    """获取下一个草稿ID"""
    existing = list(DRAFTS_DIR.glob("draft_*.ipynb"))
    if not existing:
        return 1
    
    ids = []
    for f in existing:
        match = re.match(r"draft_(\d+)_", f.name)
        if match:
            ids.append(int(match.group(1)))
    
    return max(ids) + 1 if ids else 1


def _sanitize_name(name: str) -> str:
    """清理名称，生成合法文件名"""
    name = re.sub(r'[^\w\u4e00-\u9fff]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    return name[:30]


def _create_notebook(title: str, description: str = "") -> dict:
    """创建 Notebook JSON 结构"""
    
    setup_code = '''import sys
from pathlib import Path

# 路径设置
NOTEBOOK_DIR = Path.cwd()
ROOT = NOTEBOOK_DIR.parent.parent
sys.path.insert(0, str(ROOT))

# 数据目录
SHARED_DATA_DIR = NOTEBOOK_DIR / "data"      # 草稿共享数据
ROOT_DATA_DIR = ROOT / "data"                 # 项目根数据
OUTPUT_DIR = NOTEBOOK_DIR / "output"          # 输出目录
OUTPUT_DIR.mkdir(exist_ok=True)

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# 导入项目绘图工具
from bmad.analysis.plotly_viz import PlotlyPlotter, quick_equity, quick_returns, quick_kline

print(f"共享数据目录: {SHARED_DATA_DIR}")
print(f"项目数据目录: {ROOT_DATA_DIR}")
print(f"输出目录: {OUTPUT_DIR}")'''

    data_code = '''# 加载数据
# df = pd.read_excel(SHARED_DATA_DIR / "your_data.xlsx")
# df = pd.read_csv(ROOT_DATA_DIR / "your_data.csv")

# 示例：查看共享数据目录
list(SHARED_DATA_DIR.glob("*"))'''

    viz_code = '''# 可视化代码
# fig = px.line(df, x='date', y='value', title='My Chart')
# fig.show()'''

    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    f"# {title}\n",
                    "\n",
                    f"**创建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
                    "\n",
                    f"**描述**: {description or '临时可视化分析'}\n"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## 1. 环境设置"]
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": setup_code.split('\n'),
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## 2. 数据加载"]
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": data_code.split('\n'),
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## 3. 数据处理"]
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": ["# 数据清洗和处理"],
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## 4. 可视化"]
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": viz_code.split('\n'),
                "execution_count": None,
                "outputs": []
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.11.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    return notebook


def create_draft(title: str, description: str = "") -> str:
    """创建新的草稿 Notebook
    
    Args:
        title: 草稿标题/名称
        description: 可选描述
        
    Returns:
        创建的文件路径
    """
    draft_id = _get_next_id()
    safe_name = _sanitize_name(title)
    filename = f"draft_{draft_id:03d}_{safe_name}.ipynb"
    filepath = DRAFTS_DIR / filename
    
    # 确保共享数据目录和输出目录存在
    SHARED_DATA_DIR.mkdir(exist_ok=True)
    (DRAFTS_DIR / "output").mkdir(exist_ok=True)
    
    # 创建 notebook
    notebook = _create_notebook(title, description)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 创建草稿: {filepath}")
    print(f"   共享数据目录: {SHARED_DATA_DIR}")
    return str(filepath)


def list_drafts() -> List[Dict]:
    """列出所有草稿"""
    drafts = []
    
    for f in sorted(DRAFTS_DIR.glob("draft_*.ipynb")):
        match = re.match(r"draft_(\d+)_(.+)\.ipynb", f.name)
        if match:
            draft_id = int(match.group(1))
            name = match.group(2)
            
            # 读取 notebook 获取标题
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    nb = json.load(file)
                    first_cell = nb['cells'][0]['source']
                    title_line = first_cell[0] if first_cell else name
                    title = title_line.replace('# ', '').strip()
                    
                    # 获取创建时间
                    created = "未知"
                    for line in first_cell:
                        if '创建时间' in line:
                            created = line.split('**: ')[-1].strip()
                            break
            except:
                title = name
                created = "未知"
            
            drafts.append({
                'id': draft_id,
                'name': name,
                'title': title,
                'created': created,
                'path': str(f)
            })
    
    return drafts


def show_drafts():
    """打印草稿列表"""
    drafts = list_drafts()
    
    if not drafts:
        print("📭 暂无草稿")
        return
    
    print("\n📋 草稿列表:")
    print("-" * 60)
    for d in drafts:
        print(f"  [{d['id']:03d}] {d['title']}")
        print(f"        创建: {d['created']}")
        print(f"        路径: {d['path']}")
    print("-" * 60)
    print(f"共 {len(drafts)} 个草稿\n")


def get_draft(draft_id: int) -> Optional[Path]:
    """获取指定ID的草稿路径"""
    for f in DRAFTS_DIR.glob(f"draft_{draft_id:03d}_*.ipynb"):
        return f
    return None


def delete_draft(draft_id: int, confirm: bool = True) -> bool:
    """删除指定草稿"""
    draft_path = get_draft(draft_id)
    
    if not draft_path:
        print(f"❌ 未找到草稿 #{draft_id:03d}")
        return False
    
    if confirm:
        response = input(f"确认删除 {draft_path.name}? (y/N): ")
        if response.lower() != 'y':
            print("已取消")
            return False
    
    draft_path.unlink()
    print(f"🗑️ 已删除: {draft_path.name}")
    return True


def archive_draft(draft_id: int) -> bool:
    """归档草稿"""
    import shutil
    
    draft_path = get_draft(draft_id)
    
    if not draft_path:
        print(f"❌ 未找到草稿 #{draft_id:03d}")
        return False
    
    archive_dir = DRAFTS_DIR / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    new_path = archive_dir / draft_path.name
    shutil.move(str(draft_path), str(new_path))
    print(f"📦 已归档: {draft_path.name} -> archive/")
    return True


def get_shared_data_dir() -> Path:
    """获取共享数据目录"""
    SHARED_DATA_DIR.mkdir(exist_ok=True)
    return SHARED_DATA_DIR


# 导出
__all__ = [
    'create_draft',
    'list_drafts',
    'show_drafts',
    'get_draft',
    'delete_draft',
    'archive_draft',
    'get_shared_data_dir',
    'DRAFTS_DIR',
    'SHARED_DATA_DIR',
]
