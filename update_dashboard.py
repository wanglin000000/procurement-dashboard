#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
采购系统问题看板 - 自动更新脚本
读取钉钉在线表格最新数据 -> 重写 index.html(INLINE_DATA) 与 data/procurement_issues.json -> git 推送

依赖：
  - dws CLI（WorkBuddy 钉钉连接器），路径见 DWS_BIN
  - git（凭证已存入 ~/.git-credentials，无需交互）

用法：
  python3 update_dashboard.py
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, date

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(REPO_DIR, "index.html")
DATA_JSON = os.path.join(REPO_DIR, "data", "procurement_issues.json")

DWS_BIN = "/Users/lin.wang1/.workbuddy/binaries/node/cli-connector-packages/bin/dws"
NODE_URL = "https://alidocs.dingtalk.com/i/nodes/R1zknDm0WRkG419vT0xkAZ2lVBQEx5rG"
SHEET_ID = "kgqie6hm"

# 表头(中文) -> 字段名 映射
HEADER_MAP = {
    "问题ID": "id",
    "单号": "ticketNo",
    "问题描述": "description",
    "问题提出时间": "createTime",
    "问题状态": "status",
    "问题解决时间": "resolveTime",
    "解决方案": "solution",
    "紧急程度": "urgency",
    "处理人": "handler",
    "问题类型": "type",
}


def fetch_sheet():
    """调用 dws 读取钉钉表格，返回解析后的 issues 列表；失败返回 None"""
    if not os.path.exists(DWS_BIN):
        print(f"[WARN] dws 不存在: {DWS_BIN}")
        return None
    cmd = [
        DWS_BIN, "sheet", "range", "read",
        "--node", NODE_URL,
        "--sheet-id", SHEET_ID,
        "--range", "A1:J200",
        "--format", "json",
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception as e:
        print(f"[WARN] dws 调用失败: {e}")
        return None
    if out.returncode != 0:
        print(f"[WARN] dws 返回非零: {out.stderr[:300]}")
        return None
    raw = out.stdout.strip()
    if not raw:
        print("[WARN] dws 无输出")
        return None
    try:
        data = json.loads(raw)
    except Exception as e:
        print(f"[WARN] JSON 解析失败: {e}")
        return None

    cells = data.get("cells")
    if not cells or len(cells) < 2:
        print("[WARN] 表格为空或仅有表头")
        return None

    header_cells = cells[0]
    headers = [c.get("value", "") if isinstance(c, dict) else str(c) for c in header_cells]
    col_index = {}
    for i, h in enumerate(headers):
        if h in HEADER_MAP:
            col_index[HEADER_MAP[h]] = i

    issues = []
    for row in cells[1:]:
        vals = [c.get("value", "") if isinstance(c, dict) else str(c) for c in row]
        if not any(v.strip() for v in vals):
            continue
        issue = {}
        for field, idx in col_index.items():
            issue[field] = vals[idx].strip() if idx < len(vals) else ""
        if issue.get("id") or issue.get("ticketNo"):
            issues.append(issue)

    print(f"[INFO] 解析到 {len(issues)} 条问题")
    return issues


def update_index_html(issues):
    with open(INDEX_HTML, encoding="utf-8") as f:
        html = f.read()
    n = len(issues)
    build = date.today().strftime("%y%m%d")

    inline = {
        "issues": issues,
        "fetchTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    inline_js = "const INLINE_DATA = " + json.dumps(inline, ensure_ascii=False, indent=2) + ";\n"

    # 替换 INLINE_DATA 块（从 const INLINE_DATA = { 到独立的 };）
    new_html, cnt = re.subn(
        r"const INLINE_DATA = \{[\s\S]*?\n\};",
        lambda m: inline_js.rstrip("\n"),
        html,
        count=1,
    )
    if cnt == 0:
        print("[ERROR] 未找到 INLINE_DATA 块，index.html 未修改")
        return False

    # 更新版本标签
    new_html = re.sub(
        r"Build \d+ \| 数据:\d+条",
        f"Build {build} | 数据:{n}条",
        new_html,
    )

    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"[INFO] index.html 已更新 (Build {build}, {n} 条)")
    return True


def update_data_json(issues):
    os.makedirs(os.path.dirname(DATA_JSON), exist_ok=True)
    payload = {
        "issues": issues,
        "fetchTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[INFO] data/procurement_issues.json 已更新 ({len(issues)} 条)")


def git_commit_push():
    os.chdir(REPO_DIR)
    # 重置 remote 为无 token 形式（凭证由 ~/.git-credentials 提供）
    subprocess.run(
        ["git", "remote", "set-url", "origin", "https://github.com/wanglin000000/procurement-dashboard.git"],
        capture_output=True,
    )
    subprocess.run(["git", "config", "user.email", "wanglin@workbuddy.local"], capture_output=True)
    subprocess.run(["git", "config", "user.name", "WorkBuddy Bot"], capture_output=True)
    subprocess.run(["git", "add", "-A"], capture_output=True)
    # 检查是否有变更
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
    if diff.returncode == 0:
        print("[INFO] 无数据变更，跳过提交")
        return True
    msg = f"Auto update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    subprocess.run(["git", "commit", "-m", msg], capture_output=True)
    push = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
    if push.returncode != 0:
        print(f"[ERROR] git push 失败: {push.stderr[:300]}")
        return False
    print("[INFO] 已推送到 GitHub (GitHub Pages 将自动更新)")
    return True


def main():
    print(f"=== 采购看板自动更新 {datetime.now().isoformat()} ===")
    issues = fetch_sheet()
    if not issues:
        print("[ERROR] 未能获取最新数据，本次更新中止（保留上次数据）")
        sys.exit(1)
    if not update_index_html(issues):
        sys.exit(1)
    update_data_json(issues)
    if not git_commit_push():
        sys.exit(1)
    print("=== 更新完成 ===")


if __name__ == "__main__":
    main()
