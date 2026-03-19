"""
Financial Calendar Dashboard 启动脚本
用法: python run.py
"""
import subprocess
import sys
import os
import signal
import time

PORT = 5173
PORTS_TO_KILL = [5173, 5174, 5175]  # kill any old dev servers
DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard")


def kill_port(port):
    """杀掉占用指定端口的所有进程"""
    try:
        result = subprocess.run(
            f'netstat -ano | findstr :{port}',
            shell=True, capture_output=True, text=True
        )
        pids = set()
        for line in result.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 5 and f':{port}' in parts[1]:
                pid = parts[-1]
                if pid.isdigit() and int(pid) > 0:
                    pids.add(pid)

        for pid in pids:
            print(f"  killing PID {pid} on port {port}...")
            subprocess.run(f'taskkill /F /PID {pid}', shell=True,
                           capture_output=True)
        
        if pids:
            print(f"  killed {len(pids)} process(es)")
            time.sleep(1)
        else:
            print(f"  port {port} is free")
    except Exception as e:
        print(f"  warning: {e}")


def ensure_deps():
    """确保 node_modules 已安装"""
    nm = os.path.join(DASHBOARD_DIR, "node_modules")
    if not os.path.isdir(nm):
        print("[2/3] Installing dependencies (first time only)...")
        subprocess.run("npm install", shell=True, cwd=DASHBOARD_DIR)
    else:
        print("[2/3] Dependencies OK")


def main():
    print("=" * 50)
    print("  Financial Calendar Dashboard Launcher")
    print("=" * 50)
    print()

    # 1. Kill old processes on all known ports
    print(f"[1/3] Clearing old dev servers...")
    for p in PORTS_TO_KILL:
        kill_port(p)

    # 2. Check deps
    ensure_deps()

    # 3. Start dev server
    print(f"[3/3] Starting dev server on http://localhost:{PORT}")
    print()
    print("-" * 50)
    print("  Press Ctrl+C to stop")
    print("-" * 50)
    print()

    try:
        proc = subprocess.Popen(
            f"npx vite --port {PORT}",
            shell=True,
            cwd=DASHBOARD_DIR,
        )
        proc.wait()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Done.")


if __name__ == "__main__":
    main()
