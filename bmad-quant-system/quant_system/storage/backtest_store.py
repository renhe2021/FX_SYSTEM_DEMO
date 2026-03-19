"""
回测结果存储 - 支持JSON和SQLite
"""
import json
import sqlite3
import os
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
import pandas as pd
import uuid


@dataclass
class BacktestResult:
    """回测结果数据结构"""
    id: str
    strategy_name: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    profit_factor: float
    total_pnl: float
    total_commission: float
    created_at: str
    
    # 详细数据（可选）
    equity_curve: List[Dict] = field(default_factory=list)
    trades: List[Dict] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BacktestResult':
        return cls(**data)
    
    def summary(self) -> dict:
        """返回摘要信息（不含大数据）"""
        return {
            'id': self.id,
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_capital': self.initial_capital,
            'final_equity': self.final_equity,
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'total_trades': self.total_trades,
            'profit_factor': self.profit_factor,
            'total_pnl': self.total_pnl,
            'created_at': self.created_at
        }


class BacktestStore:
    """回测结果存储管理器"""
    
    def __init__(self, storage_path: str = "./backtest_data"):
        self.storage_path = storage_path
        self.db_path = os.path.join(storage_path, "backtests.db")
        self.json_path = os.path.join(storage_path, "results")
        
        # 创建目录
        os.makedirs(self.storage_path, exist_ok=True)
        os.makedirs(self.json_path, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtests (
                id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                initial_capital REAL,
                final_equity REAL,
                total_return REAL,
                annual_return REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                win_rate REAL,
                total_trades INTEGER,
                profit_factor REAL,
                total_pnl REAL,
                total_commission REAL,
                parameters TEXT,
                created_at TEXT,
                json_file TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_strategy ON backtests(strategy_name)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol ON backtests(symbol)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created ON backtests(created_at)
        ''')
        
        conn.commit()
        conn.close()
    
    def save(self, result: BacktestResult) -> str:
        """保存回测结果"""
        # 保存详细数据到JSON
        json_file = f"{result.id}.json"
        json_path = os.path.join(self.json_path, json_file)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 保存摘要到SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO backtests 
            (id, strategy_name, symbol, start_date, end_date, initial_capital,
             final_equity, total_return, annual_return, sharpe_ratio, max_drawdown,
             win_rate, total_trades, profit_factor, total_pnl, total_commission,
             parameters, created_at, json_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.id, result.strategy_name, result.symbol,
            result.start_date, result.end_date, result.initial_capital,
            result.final_equity, result.total_return, result.annual_return,
            result.sharpe_ratio, result.max_drawdown, result.win_rate,
            result.total_trades, result.profit_factor, result.total_pnl,
            result.total_commission, json.dumps(result.parameters),
            result.created_at, json_file
        ))
        
        conn.commit()
        conn.close()
        
        return result.id
    
    def get(self, backtest_id: str) -> Optional[BacktestResult]:
        """获取回测结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT json_file FROM backtests WHERE id = ?', (backtest_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        json_path = os.path.join(self.json_path, row[0])
        if not os.path.exists(json_path):
            return None
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return BacktestResult.from_dict(data)
    
    def list_all(self, strategy_name: str = None, symbol: str = None,
                 limit: int = 100, offset: int = 0) -> List[dict]:
        """列出所有回测结果摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM backtests WHERE 1=1'
        params = []
        
        if strategy_name:
            query += ' AND strategy_name = ?'
            params.append(strategy_name)
        if symbol:
            query += ' AND symbol = ?'
            params.append(symbol)
        
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        results = []
        for row in rows:
            result = dict(zip(columns, row))
            result.pop('json_file', None)
            if result.get('parameters'):
                result['parameters'] = json.loads(result['parameters'])
            results.append(result)
        
        return results
    
    def delete(self, backtest_id: str) -> bool:
        """删除回测结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT json_file FROM backtests WHERE id = ?', (backtest_id,))
        row = cursor.fetchone()
        
        if row:
            json_path = os.path.join(self.json_path, row[0])
            if os.path.exists(json_path):
                os.remove(json_path)
            
            cursor.execute('DELETE FROM backtests WHERE id = ?', (backtest_id,))
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM backtests')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT DISTINCT strategy_name FROM backtests')
        strategies = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('SELECT DISTINCT symbol FROM backtests')
        symbols = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT strategy_name, 
                   AVG(total_return) as avg_return,
                   AVG(sharpe_ratio) as avg_sharpe,
                   COUNT(*) as count
            FROM backtests 
            GROUP BY strategy_name
        ''')
        strategy_stats = []
        for row in cursor.fetchall():
            strategy_stats.append({
                'strategy_name': row[0],
                'avg_return': row[1],
                'avg_sharpe': row[2],
                'count': row[3]
            })
        
        conn.close()
        
        return {
            'total_backtests': total,
            'strategies': strategies,
            'symbols': symbols,
            'strategy_stats': strategy_stats
        }


def create_backtest_result(
    strategy_name: str,
    symbol: str,
    results: Dict[str, Any],
    parameters: Dict[str, Any] = None
) -> BacktestResult:
    """从回测引擎结果创建BacktestResult"""
    summary = results.get('summary', {})
    equity_curve = results.get('equity_curve', pd.DataFrame())
    trades = results.get('trades', pd.DataFrame())
    
    # 解析百分比字符串
    def parse_pct(val):
        if isinstance(val, str) and '%' in val:
            return float(val.replace('%', '')) / 100
        return float(val) if val else 0
    
    return BacktestResult(
        id=str(uuid.uuid4())[:8],
        strategy_name=strategy_name,
        symbol=symbol,
        start_date=str(equity_curve.index[0].date()) if not equity_curve.empty else '',
        end_date=str(equity_curve.index[-1].date()) if not equity_curve.empty else '',
        initial_capital=summary.get('initial_capital', 0),
        final_equity=summary.get('final_equity', 0),
        total_return=parse_pct(summary.get('total_return', 0)),
        annual_return=parse_pct(summary.get('annual_return', 0)),
        sharpe_ratio=float(summary.get('sharpe_ratio', 0)),
        max_drawdown=parse_pct(summary.get('max_drawdown', 0)),
        win_rate=parse_pct(summary.get('win_rate', 0)),
        total_trades=int(summary.get('total_trades', 0)),
        profit_factor=float(summary.get('profit_factor', 0)) if summary.get('profit_factor') else 0,
        total_pnl=float(summary.get('total_pnl', 0)),
        total_commission=float(summary.get('total_commission', 0)),
        created_at=datetime.now().isoformat(),
        equity_curve=equity_curve.reset_index().to_dict('records') if not equity_curve.empty else [],
        trades=trades.to_dict('records') if not trades.empty else [],
        parameters=parameters or {}
    )
