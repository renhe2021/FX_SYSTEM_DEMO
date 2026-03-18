"""策略实验室 Web 应用"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from strategies import FridayNightStrategy, MACrossStrategy
from analyzer import StrategyAnalyzer


def create_app():
    """创建Flask应用"""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    CORS(app)
    
    # 数据目录
    data_dir = Path(__file__).parent / 'data'
    data_dir.mkdir(exist_ok=True)
    
    # 策略注册
    STRATEGIES = {
        'FridayNightStrategy': FridayNightStrategy,
        'MACrossStrategy': MACrossStrategy
    }
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/api/strategies', methods=['GET'])
    def list_strategies():
        """获取所有策略"""
        strategies = []
        for name, cls in STRATEGIES.items():
            strategies.append({
                'name': cls.name,
                'version': cls.version,
                'description': cls.description,
                'parameters': cls.get_param_schema()
            })
        return jsonify({'success': True, 'data': strategies})
    
    @app.route('/api/data/list', methods=['GET'])
    def list_data_files():
        """列出可用数据文件"""
        files = []
        for f in data_dir.glob('*.csv'):
            try:
                df = pd.read_csv(f, nrows=5)
                files.append({
                    'name': f.name,
                    'size': f.stat().st_size,
                    'columns': list(df.columns)
                })
            except:
                files.append({'name': f.name, 'error': '无法读取'})
        return jsonify({'success': True, 'data': files})
    
    @app.route('/api/data/upload', methods=['POST'])
    def upload_data():
        """上传数据文件"""
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'}), 400
        
        if file and file.filename.endswith('.csv'):
            filepath = data_dir / file.filename
            file.save(str(filepath))
            return jsonify({'success': True, 'data': {'filename': file.filename}})
        
        return jsonify({'success': False, 'error': '仅支持CSV文件'}), 400
    
    @app.route('/api/data/<filename>', methods=['GET'])
    def get_data_preview(filename):
        """预览数据"""
        filepath = data_dir / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': '文件不存在'}), 404
        
        try:
            df = pd.read_csv(filepath)
            
            # 尝试解析时间列
            time_cols = ['timestamp', 'date', 'time', 'datetime']
            for col in time_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
                    break
            
            return jsonify({
                'success': True,
                'data': {
                    'columns': list(df.columns),
                    'rows': len(df),
                    'preview': df.head(20).to_dict('records'),
                    'dtypes': {k: str(v) for k, v in df.dtypes.items()}
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/analyze', methods=['POST'])
    def analyze_strategy():
        """运行策略分析"""
        data = request.json
        strategy_name = data.get('strategy')
        params = data.get('parameters', {})
        data_file = data.get('data_file')
        
        if not strategy_name or strategy_name not in STRATEGIES:
            return jsonify({'success': False, 'error': '未知策略'}), 400
        
        if not data_file:
            return jsonify({'success': False, 'error': '未指定数据文件'}), 400
        
        filepath = data_dir / data_file
        if not filepath.exists():
            return jsonify({'success': False, 'error': '数据文件不存在'}), 404
        
        try:
            # 加载数据
            df = pd.read_csv(filepath)
            
            # 解析时间
            time_cols = ['timestamp', 'date', 'time', 'datetime']
            for col in time_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
                    df.set_index(col, inplace=True)
                    break
            
            # 创建策略
            strategy_cls = STRATEGIES[strategy_name]
            strategy = strategy_cls(**params)
            
            # 运行分析
            result = strategy.analyze(df)
            
            # 生成完整报告
            analyzer = StrategyAnalyzer(df)
            report = analyzer.generate_full_report(result)
            
            return jsonify({
                'success': True,
                'data': report
            })
            
        except Exception as e:
            import traceback
            return jsonify({
                'success': False, 
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    @app.route('/api/chart/price', methods=['POST'])
    def get_price_chart():
        """获取价格图表数据"""
        data = request.json
        data_file = data.get('data_file')
        
        if not data_file:
            return jsonify({'success': False, 'error': '未指定数据文件'}), 400
        
        filepath = data_dir / data_file
        if not filepath.exists():
            return jsonify({'success': False, 'error': '数据文件不存在'}), 404
        
        try:
            df = pd.read_csv(filepath)
            
            # 解析时间
            time_cols = ['timestamp', 'date', 'time', 'datetime']
            for col in time_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
                    df.set_index(col, inplace=True)
                    break
            
            analyzer = StrategyAnalyzer(df)
            chart_data = analyzer.price_chart_data()
            
            return jsonify({'success': True, 'data': chart_data})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return app


def run_app(host='0.0.0.0', port=8888, debug=True):
    """运行应用"""
    app = create_app()
    print(f"\n{'='*60}")
    print(f"Strategy Lab - 策略实验室")
    print(f"{'='*60}")
    print(f"访问地址: http://localhost:{port}")
    print(f"{'='*60}\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_app()
