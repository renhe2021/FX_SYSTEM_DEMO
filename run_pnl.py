import sys, os, io

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

pnl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pnl-analysis')
sys.path.insert(0, pnl_dir)
os.chdir(pnl_dir)

from app import app, _try_preload

if __name__ == '__main__':
    PORT = 5005
    print('=' * 60)
    print('  PnL Analysis - 损益分析工具')
    print(f'  http://localhost:{PORT}')
    print('=' * 60)
    preloaded = _try_preload()
    if preloaded:
        print('  已预加载本地数据')
    else:
        print('  暂无数据，请通过网页上传')
    print('=' * 60)
    app.run(host='0.0.0.0', port=PORT, debug=False)
