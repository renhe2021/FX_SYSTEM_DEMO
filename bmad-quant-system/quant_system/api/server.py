"""
Flask API服务 - 提供回测和策略管理接口
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from quant_system.storage.backtest_store import BacktestStore, create_backtest_result
from quant_system.storage.strategy_store import StrategyStore, StrategyConfig


def create_app(storage_path: str = "./backtest_data"):
    """创建Flask应用"""
    app = Flask(__name__)
    CORS(app)  # 允许跨域
    
    # 初始化存储
    backtest_store = BacktestStore(storage_path)
    strategy_store = StrategyStore(storage_path)
    
    # 创建默认策略
    strategy_store.create_default_strategies()
    
    # ==================== 策略管理 ====================
    
    @app.route('/api/strategies', methods=['GET'])
    def list_strategies():
        """获取所有策略"""
        active_only = request.args.get('active', 'false').lower() == 'true'
        strategies = strategy_store.list_all(active_only)
        return jsonify({
            'success': True,
            'data': [s.to_dict() for s in strategies]
        })
    
    @app.route('/api/strategies/<strategy_id>', methods=['GET'])
    def get_strategy(strategy_id):
        """获取单个策略"""
        strategy = strategy_store.get(strategy_id)
        if strategy:
            return jsonify({'success': True, 'data': strategy.to_dict()})
        return jsonify({'success': False, 'error': 'Strategy not found'}), 404
    
    @app.route('/api/strategies', methods=['POST'])
    def create_strategy():
        """创建策略"""
        data = request.json
        import uuid
        
        config = StrategyConfig(
            id=str(uuid.uuid4())[:8],
            name=data.get('name', ''),
            strategy_type=data.get('strategy_type', ''),
            description=data.get('description', ''),
            symbol=data.get('symbol', ''),
            parameters=data.get('parameters', {}),
            is_active=data.get('is_active', True)
        )
        
        strategy_id = strategy_store.save(config)
        return jsonify({'success': True, 'data': {'id': strategy_id}})
    
    @app.route('/api/strategies/<strategy_id>', methods=['PUT'])
    def update_strategy(strategy_id):
        """更新策略"""
        data = request.json
        strategy = strategy_store.get(strategy_id)
        
        if not strategy:
            return jsonify({'success': False, 'error': 'Strategy not found'}), 404
        
        strategy.name = data.get('name', strategy.name)
        strategy.description = data.get('description', strategy.description)
        strategy.parameters = data.get('parameters', strategy.parameters)
        strategy.is_active = data.get('is_active', strategy.is_active)
        
        strategy_store.save(strategy)
        return jsonify({'success': True, 'data': strategy.to_dict()})
    
    @app.route('/api/strategies/<strategy_id>', methods=['DELETE'])
    def delete_strategy(strategy_id):
        """删除策略"""
        if strategy_store.delete(strategy_id):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Strategy not found'}), 404
    
    # ==================== 回测管理 ====================
    
    @app.route('/api/backtests', methods=['GET'])
    def list_backtests():
        """获取所有回测结果"""
        strategy_name = request.args.get('strategy')
        symbol = request.args.get('symbol')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        results = backtest_store.list_all(strategy_name, symbol, limit, offset)
        return jsonify({
            'success': True,
            'data': results,
            'total': len(results)
        })
    
    @app.route('/api/backtests/<backtest_id>', methods=['GET'])
    def get_backtest(backtest_id):
        """获取单个回测结果（含详细数据）"""
        result = backtest_store.get(backtest_id)
        if result:
            return jsonify({'success': True, 'data': result.to_dict()})
        return jsonify({'success': False, 'error': 'Backtest not found'}), 404
    
    @app.route('/api/backtests/<backtest_id>/summary', methods=['GET'])
    def get_backtest_summary(backtest_id):
        """获取回测摘要"""
        result = backtest_store.get(backtest_id)
        if result:
            return jsonify({'success': True, 'data': result.summary()})
        return jsonify({'success': False, 'error': 'Backtest not found'}), 404
    
    @app.route('/api/backtests/<backtest_id>', methods=['DELETE'])
    def delete_backtest(backtest_id):
        """删除回测结果"""
        if backtest_store.delete(backtest_id):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Backtest not found'}), 404
    
    @app.route('/api/backtests/statistics', methods=['GET'])
    def get_statistics():
        """获取统计信息"""
        stats = backtest_store.get_statistics()
        return jsonify({'success': True, 'data': stats})
    
    # ==================== 运行回测 ====================
    
    @app.route('/api/backtests/run', methods=['POST'])
    def run_backtest():
        """运行回测"""
        data = request.json
        strategy_id = data.get('strategy_id')
        
        # 获取策略配置
        strategy_config = strategy_store.get(strategy_id)
        if not strategy_config:
            return jsonify({'success': False, 'error': 'Strategy not found'}), 404
        
        try:
            # 导入回测组件
            from quant_system.agent import BacktestEngine
            from quant_system.model import FridayNightStrategy, MACrossStrategy
            from quant_system.base import BloombergDataSource
            from datetime import datetime, timedelta
            
            # 获取数据
            symbol = strategy_config.symbol
            days = data.get('days', 365)
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 尝试从Bloomberg获取数据
            bbg = BloombergDataSource()
            if bbg.connect():
                market_data = bbg.get_historical_data(symbol, start_date, end_date, "1D")
                bbg.disconnect()
            else:
                return jsonify({'success': False, 'error': 'Bloomberg connection failed'}), 500
            
            if market_data.empty:
                return jsonify({'success': False, 'error': 'No data available'}), 500
            
            # 创建回测引擎
            engine = BacktestEngine(
                initial_capital=data.get('initial_capital', 1000000),
                commission_rate=data.get('commission_rate', 0.00005),
                slippage=data.get('slippage', 0.0001)
            )
            
            engine.add_data(symbol.split()[0], market_data)
            
            # 创建策略
            params = strategy_config.parameters
            if strategy_config.strategy_type == 'FridayNightStrategy':
                strategy = FridayNightStrategy(**params)
            elif strategy_config.strategy_type == 'MACrossStrategy':
                strategy = MACrossStrategy(**params)
            else:
                return jsonify({'success': False, 'error': 'Unknown strategy type'}), 400
            
            engine.add_strategy(strategy)
            
            # 运行回测
            results = engine.run()
            
            # 保存结果
            backtest_result = create_backtest_result(
                strategy_name=strategy_config.name,
                symbol=symbol,
                results=results,
                parameters=params
            )
            
            backtest_id = backtest_store.save(backtest_result)
            
            return jsonify({
                'success': True,
                'data': {
                    'id': backtest_id,
                    'summary': backtest_result.summary()
                }
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ==================== 健康检查 ====================
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """健康检查"""
        return jsonify({
            'success': True,
            'status': 'healthy',
            'version': '1.0.0'
        })
    
    return app


def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = True):
    """运行服务器"""
    app = create_app()
    print(f"Starting Quant API Server on http://{host}:{port}")
    print("API Endpoints:")
    print("  GET  /api/strategies        - List all strategies")
    print("  GET  /api/backtests         - List all backtests")
    print("  POST /api/backtests/run     - Run a backtest")
    print("  GET  /api/backtests/<id>    - Get backtest details")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()
