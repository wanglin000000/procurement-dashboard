#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看门狗：在限定时间内运行目标脚本，超时强杀，避免 dws/git push 挂起。"""
import os
import subprocess
import sys
import time
import select

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
fd = proc.stdout.fileno()
start = time.time()
killed = False
rc = None

while True:
    remaining = TIMEOUT - (time.time() - start)
    if remaining <= 0:
        killed = True
        try:
            proc.kill()
        except Exception:
            pass
        break
    rlist, _, _ = select.select([fd], [], [], min(1.0, remaining))
    if rlist:
        chunk = os.read(fd, 4096)
        if not chunk:
            break
        sys.stdout.write(chunk.decode("utf-8", errors="replace"))
        sys.stdout.flush()
    if proc.poll() is not None:
        # 进程已退出，把剩余输出读完
        for line in proc.stdout:
            sys.stdout.write(line)
        break

rc = proc.wait()
elapsed = time.time() - start
print(f"\n[WATCHDOG] 退出码={rc} 耗时={elapsed:.1f}s 强杀={killed}")
sys.exit(rc if not killed else 1)
