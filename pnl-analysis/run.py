# -*- coding: utf-8 -*-
"""启动脚本"""
from app import app, _load_data

if __name__ == "__main__":
    print("=" * 60)
    print("  📊 PnL Analysis Dashboard")
    print("  http://localhost:5003")
    print("=" * 60)

    data = _load_data()
    print(f"\n📂 Loaded {len(data)} period(s):")
    for label, date_str, df in data:
        print(f"   {label}: {len(df)} records")

    app.run(host="0.0.0.0", port=5003, debug=True)
