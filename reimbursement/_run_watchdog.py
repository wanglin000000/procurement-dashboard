#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看门狗：带超时与子进程强杀地运行 update_dashboard.py，避免 dws/git 卡死导致自动化挂起。"""
import os
import subprocess
import sys
import time

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update_dashboard.py")
TIMEOUT = 280  # 秒


def main():
    start = time.time()
    proc = subprocess.Popen([sys.executable, SCRIPT],
                            stdout=sys.stdout, stderr=sys.stderr)
    try:
        rc = proc.wait(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        print(f"\n[WATCHDOG] 超时 {TIMEOUT}s，强杀主进程及其子进程(dws/git)")
        try:
            proc.kill()
            # 额外清理可能残留的 dws / git-remote-https 子进程
            os.system("pkill -f 'dws sheet' >/dev/null 2>&1 || true")
            os.system("pkill -f 'git-remote-https' >/dev/null 2>&1 || true")
        except Exception as e:
            print(f"[WATCHDOG] 清理异常: {e}")
        print(f"[WATCHDOG] 运行结果: 超时强杀 (已运行 {int(time.time()-start)}s)")
        sys.exit(2)
    print(f"[WATCHDOG] 运行结果: 退出码 {rc} (耗时 {int(time.time()-start)}s)")
    sys.exit(rc)


if __name__ == "__main__":
    main()
