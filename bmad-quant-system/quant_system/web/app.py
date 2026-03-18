"""Web UI应用 - 策略配置和回测管理"""
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import os
import sys
import json
import yaml
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quant_system.model.strategies import StrategyRegistry
from quant_system.config import ConfigManager
from quant_system.config.config_schema import DataSourceType, Frequency


def create_app(config_dir: str = None, output_dir: str = None):
    """创建Flask应用"""
    
    # 使用绝对路径
    project_root = Path(__file__).parent.parent.parent.resolve()
    if config_dir is None:
        config_dir = str(project_root / "configs")
    if output_dir is None:
        output_dir = str(project_root / "output")
    
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    CORS(app)
    
    # 禁用模板缓存（开发模式）
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True
    
    # 确保目录存在
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[DEBUG] Template dir: {template_dir}")
    print(f"[DEBUG] Config dir: {config_dir}")
    print(f"[DEBUG] Output dir: {output_dir}")
    
    # ==================== 页面路由 ====================
    
    @app.route('/')
    def index():
        """主页"""
        return render_template('index.html')
    
    # ==================== 策略API ====================
    
    @app.route('/api/strategies', methods=['GET'])
    def list_strategies():
        """获取所有策略"""
        strategies = StrategyRegistry.list_all()
        return jsonify({'success': True, 'data': strategies})
    
    @app.route('/api/strategies/<name>', methods=['GET'])
    def get_strategy(name):
        """获取单个策略详情"""
        strategy_class = StrategyRegistry.get(name)
        if strategy_class:
            return jsonify({'success': True, 'data': strategy_class.get_info()})
        return jsonify({'success': False, 'error': 'Strategy not found'}), 404
    
    # ==================== 配置API ====================
    
    @app.route('/api/configs', methods=['GET'])
    def list_configs():
        """获取所有配置文件"""
        configs = []
        config_path = Path(config_dir)
        print(f"[API] list_configs called, config_dir={config_dir}")
        print(f"[API] config_path exists: {config_path.exists()}")
        yaml_files = list(config_path.glob('*.yaml'))
        print(f"[API] Found yaml files: {yaml_files}")
        
        for f in yaml_files:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                    configs.append({
                        'filename': f.name,
                        'name': data.get('name', f.stem),
                        'strategy': data.get('strategy', {}).get('name', ''),
                        'data_source': data.get('data_source', {}).get('type', ''),
                        'symbol': data.get('data_source', {}).get('symbol', ''),
                        'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                    })
            except Exception as e:
                configs.append({
                    'filename': f.name,
                    'name': f.stem,
                    'error': str(e)
                })
        
        return jsonify({'success': True, 'data': configs})
    
    @app.route('/api/configs/<filename>', methods=['GET'])
    def get_config(filename):
        """获取配置文件内容"""
        filepath = Path(config_dir) / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'Config not found'}), 404
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/configs', methods=['POST'])
    def create_config():
        """创建新配置"""
        data = request.json
        filename = data.get('filename', f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
        
        if not filename.endswith('.yaml'):
            filename += '.yaml'
        
        filepath = Path(config_dir) / filename
        
        config_data = data.get('config', {})
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            return jsonify({'success': True, 'data': {'filename': filename}})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/configs/<filename>', methods=['PUT'])
    def update_config(filename):
        """更新配置文件"""
        filepath = Path(config_dir) / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'Config not found'}), 404
        
        data = request.json
        config_data = data.get('config', {})
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/configs/<filename>', methods=['DELETE'])
    def delete_config(filename):
        """删除配置文件"""
        filepath = Path(config_dir) / filename
        if filepath.exists():
            filepath.unlink()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Config not found'}), 404
    
    # ==================== 数据源选项 ====================
    
    @app.route('/api/options/data-sources', methods=['GET'])
    def get_data_source_options():
        """获取数据源选项"""
        return jsonify({
            'success': True,
            'data': [
                {'value': 'bloomberg', 'label': 'Bloomberg Terminal', 'description': '从Bloomberg API获取实时数据'},
                {'value': 'local_csv', 'label': '本地CSV文件', 'description': '从本地CSV文件读取数据'},
                {'value': 'local_excel', 'label': '本地Excel文件', 'description': '从本地Excel文件读取数据'},
                {'value': 'sql', 'label': 'SQL数据库', 'description': '从SQL数据库读取数据'}
            ]
        })
    
    @app.route('/api/options/frequencies', methods=['GET'])
    def get_frequency_options():
        """获取数据频率选项"""
        return jsonify({
            'success': True,
            'data': [
                {'value': '1m', 'label': '1分钟'},
                {'value': '5m', 'label': '5分钟'},
                {'value': '15m', 'label': '15分钟'},
                {'value': '30m', 'label': '30分钟'},
                {'value': '1h', 'label': '1小时'},
                {'value': '1d', 'label': '日线'},
                {'value': '1w', 'label': '周线'}
            ]
        })
    
    # ==================== 回测API ====================
    
    @app.route('/api/backtest/run', methods=['POST'])
    def run_backtest():
        """运行回测"""
        print("\n" + "="*60)
        print("[API] /api/backtest/run 被调用")
        print("="*60)
        
        logs = []  # 收集日志
        
        data = request.json
        config_filename = data.get('config')
        
        print(f"[API] 请求数据: {data}")
        print(f"[API] 配置文件: {config_filename}")
        
        logs.append(f"收到回测请求: {config_filename}")
        
        if not config_filename:
            logs.append("✗ 错误: 未指定配置文件")
            return jsonify({'success': False, 'error': 'Config filename required', 'logs': logs}), 400
        
        filepath = Path(config_dir) / config_filename
        logs.append(f"配置文件路径: {filepath}")
        
        if not filepath.exists():
            logs.append(f"✗ 错误: 配置文件不存在: {filepath}")
            return jsonify({'success': False, 'error': f'Config not found: {filepath}', 'logs': logs}), 404
        
        try:
            # Step 1: 加载配置
            logs.append(f"\n[1/5] 加载配置: {config_filename}")
            from quant_system.config import ConfigManager
            from quant_system.config.data_loader import DataLoader
            
            manager = ConfigManager(str(filepath))
            config = manager.config
            logs.append(f"  ✓ 配置加载成功: {config.name}")
            logs.append(f"  - 数据源: {config.data_source.type.value}")
            logs.append(f"  - 文件路径: {config.data_source.local_file.path}")
            logs.append(f"  - 策略: {config.strategy.type}")
            
            # Step 2: 加载数据
            logs.append(f"\n[2/5] 加载数据...")
            logs.append(f"  - 类型: {config.data_source.type.value}")
            logs.append(f"  - 路径: {config.data_source.local_file.path}")
            
            loader = DataLoader(config.data_source)
            market_data = loader.load()
            logs.append(f"  ✓ 数据加载成功: {len(market_data)} 行")
            logs.append(f"  - 日期范围: {market_data.index[0]} ~ {market_data.index[-1]}")
            logs.append(f"  - 列: {list(market_data.columns)}")
            
            # Step 3: 创建策略
            logs.append(f"\n[3/5] 创建策略...")
            logs.append(f"  - 策略类型: {config.strategy.type}")
            logs.append(f"  - 参数: {config.strategy.parameters}")
            
            strategy = StrategyRegistry.create(
                config.strategy.type,
                **config.strategy.parameters
            )
            
            if not strategy:
                logs.append(f"  ✗ 策略创建失败: {config.strategy.type} 未找到")
                logs.append(f"  - 可用策略: {StrategyRegistry.get_names()}")
                return jsonify({
                    'success': False, 
                    'error': f'Strategy {config.strategy.type} not found',
                    'logs': logs
                }), 400
            
            logs.append(f"  ✓ 策略创建成功: {strategy.name}")
            logs.append(f"  - 实际参数: {strategy.params}")
            
            # Step 4: 生成信号
            logs.append(f"\n[4/5] 生成交易信号...")
            signals = strategy.generate_signals(market_data)
            logs.append(f"  ✓ 信号生成完成: {len(signals)} 个信号")
            
            if signals:
                buy_signals = [s for s in signals if s.action == 'BUY']
                sell_signals = [s for s in signals if s.action == 'SELL']
                logs.append(f"  - 买入信号: {len(buy_signals)}")
                logs.append(f"  - 卖出信号: {len(sell_signals)}")
                
                # 显示前几个信号
                for i, sig in enumerate(signals[:4]):
                    logs.append(f"  - 信号{i+1}: {sig.action} @ {sig.timestamp} | 价格: {sig.price:.4f}")
            else:
                logs.append(f"  ⚠ 没有生成任何信号！")
                
                # 调试信息
                df = market_data.copy()
                df['dayofweek'] = df.index.dayofweek
                df['hour'] = df.index.hour
                
                entry_day = strategy.params.get('entry_day', 4)
                entry_hour = strategy.params.get('entry_hour', 21)
                
                friday_data = df[df['dayofweek'] == entry_day]
                logs.append(f"  - 调试: 周{entry_day+1}数据量: {len(friday_data)}")
                
                if not friday_data.empty:
                    hour_data = friday_data[friday_data['hour'] == entry_hour]
                    logs.append(f"  - 调试: {entry_hour}点数据量: {len(hour_data)}")
            
            # Step 5: 运行回测
            logs.append(f"\n[5/5] 运行回测...")
            results = simple_backtest(
                signals, 
                market_data,
                config.backtest.initial_capital,
                config.backtest.commission_rate,
                config.backtest.slippage,
                config.risk.stop_loss_pct,
                config.risk.take_profit_pct
            )
            
            logs.append(f"  ✓ 回测完成")
            logs.append(f"  - 交易数: {results['summary']['total_trades']}")
            logs.append(f"  - 总收益: {results['summary']['total_return']:.2f}%")
            logs.append(f"  - 胜率: {results['summary']['win_rate']:.1f}%")
            
            # 保存结果
            result_id = save_backtest_result(results, config, output_dir)
            logs.append(f"\n✓ 结果已保存: {result_id}")
            
            response_data = {
                'success': True,
                'data': {
                    'result_id': result_id,
                    'summary': results['summary'],
                    'trades_count': len(results['trades']),
                    'trades': results['trades'][:10]  # 返回前10笔交易
                },
                'logs': logs
            }
            
            print(f"\n[API] 返回成功响应")
            print(f"[API] logs数量: {len(logs)}")
            print(f"[API] 前3条日志: {logs[:3]}")
            
            return jsonify(response_data)
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            tb = traceback.format_exc()
            logs.append(f"\n✗ 错误: {error_msg}")
            logs.append(f"\n堆栈跟踪:")
            for line in tb.split('\n'):
                logs.append(f"  {line}")
            
            print(f"\n[API] 返回错误响应")
            print(f"[API] 错误: {error_msg}")
            print(f"[API] logs数量: {len(logs)}")
            
            return jsonify({
                'success': False, 
                'error': error_msg,
                'traceback': tb,
                'logs': logs
            }), 500
    
    @app.route('/api/backtest/results', methods=['GET'])
    def list_backtest_results():
        """获取回测结果列表"""
        results = []
        results_dir = Path(output_dir) / 'backtests'
        
        if results_dir.exists():
            for f in results_dir.glob('*.json'):
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        results.append({
                            'id': f.stem,
                            'strategy': data.get('strategy_name', ''),
                            'symbol': data.get('symbol', ''),
                            'total_return': data.get('summary', {}).get('total_return', 0),
                            'sharpe_ratio': data.get('summary', {}).get('sharpe_ratio', 0),
                            'created_at': data.get('created_at', '')
                        })
                except:
                    pass
        
        return jsonify({'success': True, 'data': results})
    
    @app.route('/api/backtest/results/<result_id>', methods=['GET'])
    def get_backtest_result(result_id):
        """获取回测结果详情"""
        filepath = Path(output_dir) / 'backtests' / f'{result_id}.json'
        
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'Result not found'}), 404
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return app


def simple_backtest(signals, data, initial_capital, commission_rate, slippage, stop_loss_pct, take_profit_pct):
    """简单回测引擎"""
    import numpy as np
    
    capital = initial_capital
    trades = []
    equity_curve = [initial_capital]
    
    # 配对信号（买入-卖出）
    i = 0
    while i < len(signals) - 1:
        entry_signal = signals[i]
        exit_signal = signals[i + 1]
        
        if entry_signal.action == "BUY" and exit_signal.action == "SELL":
            entry_price = entry_signal.price
            exit_price = exit_signal.price
            quantity = entry_signal.quantity
            
            # 计算盈亏
            gross_pnl = quantity * (exit_price - entry_price) / entry_price
            commission = quantity * commission_rate * 2
            slip = quantity * slippage * 2
            net_pnl = gross_pnl - commission - slip
            
            capital += net_pnl
            equity_curve.append(capital)
            
            trades.append({
                'entry_time': str(entry_signal.timestamp),
                'exit_time': str(exit_signal.timestamp),
                'entry_price': float(entry_price),
                'exit_price': float(exit_price),
                'quantity': float(quantity),
                'gross_pnl': round(float(gross_pnl), 2),
                'net_pnl': round(float(net_pnl), 2),
                'return_pct': round(float((exit_price - entry_price) / entry_price * 100), 4)
            })
            
            i += 2
        else:
            i += 1
    
    # 计算统计
    if trades:
        returns = [t['return_pct'] for t in trades]
        pnls = [t['net_pnl'] for t in trades]
        wins = [t for t in trades if t['net_pnl'] > 0]
        losses = [t for t in trades if t['net_pnl'] <= 0]
        
        # 最大回撤
        peak = equity_curve[0]
        max_dd = 0
        for e in equity_curve:
            if e > peak:
                peak = e
            dd = (peak - e) / peak
            if dd > max_dd:
                max_dd = dd
        
        # 夏普比率
        avg_return = np.mean(returns) if returns else 0
        std_return = np.std(returns) if len(returns) > 1 else 1
        sharpe = float((avg_return / std_return) * np.sqrt(52)) if std_return > 0 else 0
        
        summary = {
            'initial_capital': float(initial_capital),
            'final_capital': round(float(capital), 2),
            'total_return': round(float((capital / initial_capital - 1) * 100), 4),
            'total_pnl': round(float(sum(pnls)), 2),
            'total_trades': len(trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': round(float(len(wins) / len(trades) * 100), 2) if trades else 0,
            'avg_win': round(float(sum(t['net_pnl'] for t in wins) / len(wins)), 2) if wins else 0,
            'avg_loss': round(float(sum(t['net_pnl'] for t in losses) / len(losses)), 2) if losses else 0,
            'sharpe_ratio': round(float(sharpe), 2),
            'max_drawdown': round(float(max_dd * 100), 2)
        }
    else:
        summary = {
            'initial_capital': float(initial_capital),
            'final_capital': float(initial_capital),
            'total_return': 0.0,
            'total_pnl': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0
        }
    
    return {
        'summary': summary,
        'trades': trades,
        'equity_curve': [float(e) for e in equity_curve]
    }


def save_backtest_result(results, config, output_dir):
    """保存回测结果"""
    import uuid
    
    results_dir = Path(output_dir) / 'backtests'
    results_dir.mkdir(parents=True, exist_ok=True)
    
    result_id = datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + str(uuid.uuid4())[:8]
    
    data = {
        'id': result_id,
        'strategy_name': config.strategy.name,
        'strategy_type': config.strategy.type,
        'symbol': config.data_source.symbol,
        'data_source': config.data_source.type.value,
        'created_at': datetime.now().isoformat(),
        'config': {
            'backtest': {
                'initial_capital': config.backtest.initial_capital,
                'commission_rate': config.backtest.commission_rate,
                'slippage': config.backtest.slippage
            },
            'strategy_parameters': config.strategy.parameters
        },
        'summary': results['summary'],
        'trades': results['trades'],
        'equity_curve': results['equity_curve']
    }
    
    filepath = results_dir / f'{result_id}.json'
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return result_id


def run_app(host: str = '0.0.0.0', port: int = 8080, debug: bool = True):
    """运行应用"""
    # 获取项目根目录（bmad-quant-system）
    project_root = Path(__file__).parent.parent.parent.resolve()
    config_dir = str(project_root / "configs")
    output_dir = str(project_root / "output")
    
    print(f"[STARTUP] Project root: {project_root}")
    print(f"[STARTUP] Config dir: {config_dir}")
    print(f"[STARTUP] Config dir exists: {Path(config_dir).exists()}")
    if Path(config_dir).exists():
        yaml_files = list(Path(config_dir).glob('*.yaml'))
        print(f"[STARTUP] YAML files found: {[f.name for f in yaml_files]}")
    
    app = create_app(config_dir=config_dir, output_dir=output_dir)
    print(f"\n{'='*60}")
    print(f"BMAD Quant System - Web UI")
    print(f"{'='*60}")
    print(f"Running on: http://localhost:{port}")
    print(f"API Docs: http://localhost:{port}/api/strategies")
    print(f"{'='*60}\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_app()
