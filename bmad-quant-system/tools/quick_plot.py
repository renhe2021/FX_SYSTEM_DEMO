"""快速绘图工具

提供常用的绘图函数，无需复杂配置
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Union


def quick_plot(data: Union[pd.Series, pd.DataFrame], 
               title: str = None,
               figsize: tuple = (12, 6),
               **kwargs):
    """快速绘制时间序列
    
    Args:
        data: Series或DataFrame
        title: 标题
        figsize: 图形大小
    """
    try:
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=figsize)
        data.plot(ax=ax, **kwargs)
        
        if title:
            ax.set_title(title)
        
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
        
    except ImportError:
        print("请安装 matplotlib: pip install matplotlib")


def plot_ohlc(data: pd.DataFrame,
              title: str = 'OHLC Chart',
              figsize: tuple = (14, 8),
              volume: bool = True):
    """绘制K线图
    
    Args:
        data: 包含open, high, low, close列的DataFrame
        title: 标题
        figsize: 图形大小
        volume: 是否显示成交量
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        
        df = data.copy()
        df.columns = df.columns.str.lower()
        
        if volume and 'volume' in df.columns:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, 
                                           gridspec_kw={'height_ratios': [3, 1]},
                                           sharex=True)
        else:
            fig, ax1 = plt.subplots(figsize=figsize)
            ax2 = None
        
        # 绘制K线
        up = df[df['close'] >= df['open']]
        down = df[df['close'] < df['open']]
        
        # 上涨K线
        ax1.bar(up.index, up['close'] - up['open'], bottom=up['open'], 
                color='red', width=0.8, alpha=0.8)
        ax1.vlines(up.index, up['low'], up['high'], color='red', linewidth=0.5)
        
        # 下跌K线
        ax1.bar(down.index, down['close'] - down['open'], bottom=down['open'],
                color='green', width=0.8, alpha=0.8)
        ax1.vlines(down.index, down['low'], down['high'], color='green', linewidth=0.5)
        
        ax1.set_title(title)
        ax1.set_ylabel('Price')
        ax1.grid(True, alpha=0.3)
        
        # 成交量
        if ax2 is not None:
            colors = ['red' if c >= o else 'green' 
                      for c, o in zip(df['close'], df['open'])]
            ax2.bar(df.index, df['volume'], color=colors, alpha=0.5)
            ax2.set_ylabel('Volume')
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
    except ImportError:
        print("请安装 matplotlib: pip install matplotlib")


def plot_returns(returns: pd.Series,
                 title: str = 'Returns Distribution',
                 figsize: tuple = (14, 5)):
    """绘制收益率分析图
    
    Args:
        returns: 收益率序列
        title: 标题
        figsize: 图形大小
    """
    try:
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(1, 3, figsize=figsize)
        
        # 收益率时间序列
        axes[0].plot(returns.index, returns.values, alpha=0.7)
        axes[0].axhline(y=0, color='r', linestyle='--', alpha=0.5)
        axes[0].set_title('Returns Over Time')
        axes[0].set_ylabel('Return')
        axes[0].grid(True, alpha=0.3)
        
        # 收益率分布
        axes[1].hist(returns.dropna(), bins=50, edgecolor='black', alpha=0.7)
        axes[1].axvline(x=returns.mean(), color='r', linestyle='--', 
                        label=f'Mean: {returns.mean():.4f}')
        axes[1].set_title('Returns Distribution')
        axes[1].set_xlabel('Return')
        axes[1].legend()
        
        # 累计收益
        cum_returns = (1 + returns).cumprod()
        axes[2].plot(cum_returns.index, cum_returns.values)
        axes[2].set_title('Cumulative Returns')
        axes[2].set_ylabel('Cumulative Return')
        axes[2].grid(True, alpha=0.3)
        
        plt.suptitle(title)
        plt.tight_layout()
        plt.show()
        
    except ImportError:
        print("请安装 matplotlib: pip install matplotlib")


def plot_drawdown(equity_curve: pd.Series,
                  title: str = 'Drawdown Analysis',
                  figsize: tuple = (14, 8)):
    """绘制回撤分析图
    
    Args:
        equity_curve: 权益曲线
        title: 标题
        figsize: 图形大小
    """
    try:
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)
        
        # 权益曲线
        axes[0].plot(equity_curve.index, equity_curve.values, label='Equity')
        cummax = equity_curve.cummax()
        axes[0].plot(equity_curve.index, cummax.values, '--', 
                     label='Peak', alpha=0.7)
        axes[0].set_title('Equity Curve')
        axes[0].set_ylabel('Equity')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # 回撤
        drawdown = (equity_curve - cummax) / cummax * 100
        axes[1].fill_between(drawdown.index, drawdown.values, 0, 
                             color='red', alpha=0.3)
        axes[1].plot(drawdown.index, drawdown.values, color='red')
        axes[1].set_title('Drawdown')
        axes[1].set_ylabel('Drawdown (%)')
        axes[1].grid(True, alpha=0.3)
        
        # 标注最大回撤
        max_dd_idx = drawdown.idxmin()
        max_dd = drawdown.min()
        axes[1].annotate(f'Max DD: {max_dd:.2f}%',
                         xy=(max_dd_idx, max_dd),
                         xytext=(max_dd_idx, max_dd - 5),
                         arrowprops=dict(arrowstyle='->', color='black'),
                         fontsize=10)
        
        plt.suptitle(title)
        plt.tight_layout()
        plt.show()
        
    except ImportError:
        print("请安装 matplotlib: pip install matplotlib")


def plot_correlation(data: pd.DataFrame,
                     title: str = 'Correlation Matrix',
                     figsize: tuple = (10, 8)):
    """绘制相关性矩阵
    
    Args:
        data: DataFrame
        title: 标题
        figsize: 图形大小
    """
    try:
        import matplotlib.pyplot as plt
        
        corr = data.corr()
        
        fig, ax = plt.subplots(figsize=figsize)
        im = ax.imshow(corr, cmap='RdYlGn', aspect='auto', 
                       vmin=-1, vmax=1)
        
        # 添加标签
        ax.set_xticks(range(len(corr.columns)))
        ax.set_yticks(range(len(corr.columns)))
        ax.set_xticklabels(corr.columns, rotation=45, ha='right')
        ax.set_yticklabels(corr.columns)
        
        # 添加数值
        for i in range(len(corr)):
            for j in range(len(corr)):
                text = ax.text(j, i, f'{corr.iloc[i, j]:.2f}',
                               ha='center', va='center', fontsize=8)
        
        plt.colorbar(im)
        ax.set_title(title)
        plt.tight_layout()
        plt.show()
        
    except ImportError:
        print("请安装 matplotlib: pip install matplotlib")
