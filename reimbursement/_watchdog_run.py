#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看门狗：在限定时间内运行目标脚本，超时强杀，避免 dws/git push 挂起。"""
import os
import subprocess
import sys
import signal

TIMEOUT = 280
HERE = os.path.dirname(os.path.abspath(__file__))
target = sys.argv[1] if len(sys.argv) > 1 else "update_dashboard.py"

proc = subprocess.Popen(
    ["python3", target],
    cwd=HERE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
start = time.time()
killed = False
# 实时流式转发输出
for line in proc.stdout:
    sys.stdout.write(line)
    sys.stdout.flush()
if proc.wait() is None:
    # 理论上 for 循环会消费到 EOF，这里做兜底
    pass
rc = proc.poll()
elapsed = time.time() - start
if rc is None:
    killed = True
    try:
        proc.kill()
    except Exception:
        pass
    rc = -9
print(f"\n[WATCHDOG] 退出码={rc} 耗时={elapsed:.1f}s 强杀={killed}")
sys.exit(rc if not killed else 1)
