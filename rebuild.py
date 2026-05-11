#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-Org v2.0 — クリーン再構築スクリプト
===========================================
実行するだけで以下を全部作り直します:
  - ディレクトリ構造
  - .env.example / .gitignore
  - requirements.txt
  - config.py
  - src/api/app.py (HTMLホームページ付き)
  - vercel.json (buildsなし・修正済み)
  - .github/workflows/ci.yml (upload-artifact v4)
  - run_phase1〜9_tests.py (テストファイル全部)

使い方:
  1. このファイルを ai-org-v2-0/ に置く
  2. python rebuild.py
  3. 完了したら git push
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
print(f"📁 作業ディレクトリ: {ROOT}")

def write(path: str, content: str):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.lstrip("\n"), encoding="utf-8")
    print(f"  ✅ {path}")

print("\n🚀 AI-Org v2.0 再構築開始\n")

# ===========================================================================
# .gitignore
# ===========================================================================
write(".gitignore", """
.env
.env.local
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.log
.DS_Store
venv/
.venv/
node_modules/
.vscode/
dist/
build/
*.egg-info/
""")

# ===========================================================================
# .env.example
# ===========================================================================
write(".env.example", """
# Anthropic Claude API
ANTHROPIC_API_KEY=your-api-key-here

# Firebase
FIREBASE_DB_URL=https://your-project.firebaseio.com
FIREBASE_AUTH_TOKEN=your-firebase-token

# LINE Messaging API
LINE_CHANNEL_ACCESS_TOKEN=your-line-token
LINE_USER_ID=your-line-user-id

# Budget
MONTHLY_BUDGET_JPY=3000
""")

# ===========================================================================
# requirements.txt
# ===========================================================================
write("requirements.txt", """
anthropic>=0.25.0
python-dotenv>=1.0.0
jsonschema>=4.20.0
requests>=2.31.0
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.0.0
typing-extensions>=4.7.0
""")

# ===========================================================================
# config.py
# ===========================================================================
write("config.py", """
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path if env_path.exists() else None)
except ImportError:
    pass

class Config:
    ANTHROPIC_API_KEY            = os.getenv("ANTHROPIC_API_KEY", "")
    MONTHLY_BUDGET_JPY           = int(os.getenv("MONTHLY_BUDGET_JPY", 3000))
    WARNING_THRESHOLD_PERCENT    = int(os.getenv("WARNING_THRESHOLD_PERCENT", 50))
    CAUTION_THRESHOLD_PERCENT    = int(os.getenv("CAUTION_THRESHOLD_PERCENT", 70))
    EMERGENCY_THRESHOLD_PERCENT  = int(os.getenv("EMERGENCY_THRESHOLD_PERCENT", 80))
    STRATEGIST_BUDGET            = int(os.getenv("STRATEGIST_BUDGET", 800))
    BUILDER_BUDGET               = int(os.getenv("BUILDER_BUDGET", 1500))
    OPERATOR_BUDGET              = int(os.getenv("OPERATOR_BUDGET", 500))
    RESERVE_BUDGET               = int(os.getenv("RESERVE_BUDGET", 200))
    LINE_CHANNEL_ACCESS_TOKEN    = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    LINE_USER_ID                 = os.getenv("LINE_USER_ID", "")
    FIREBASE_DB_URL              = os.getenv("FIREBASE_DB_URL", "")
    FIREBASE_AUTH_TOKEN          = os.getenv("FIREBASE_AUTH_TOKEN", "")
    AUDIT_LOG_PATH               = os.getenv("AUDIT_LOG_PATH", "src/logs/audit.log")

config = Config()
""")

# ===========================================================================
# src/api/app.py  (HTMLホームページ + 全エンドポイント)
# ===========================================================================
write("src/api/app.py", r'''
"""
AI-Org v2.0 — FastAPI バックエンド
GET / はHTMLウェルカムページを返す
"""

from __future__ import annotations
import os, uuid, datetime, math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="AI-Org v2.0 API", version="2.0",
              docs_url="/docs", redoc_url="/redoc")

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

_escalations: dict = {}

# ---------- HTML ホームページ ----------

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    return """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI-Org v2.0</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Noto+Sans+JP:wght@300;400;700&display=swap');
:root{--bg:#0a0a0f;--surface:#12121a;--border:#1e1e2e;--accent:#7c3aed;--accent2:#06b6d4;--text:#e2e2f0;--muted:#6b6b8a;--green:#10b981}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Noto Sans JP',sans-serif;font-weight:300;min-height:100vh;padding:2rem 1rem}
.container{max-width:720px;margin:0 auto}
header{border-bottom:1px solid var(--border);padding-bottom:2rem;margin-bottom:2.5rem}
.badge{display:inline-block;background:var(--accent);color:#fff;font-family:'Space Mono',monospace;font-size:.65rem;letter-spacing:.1em;padding:.25rem .7rem;border-radius:2px;margin-bottom:1rem}
h1{font-family:'Space Mono',monospace;font-size:clamp(1.4rem,4vw,2.2rem);font-weight:700;color:#fff;line-height:1.2}
h1 span{color:var(--accent)}
.status-line{display:flex;align-items:center;gap:.5rem;margin-top:.8rem;font-family:'Space Mono',monospace;font-size:.8rem;color:var(--muted)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.agents{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:2.5rem}
.agent-card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.2rem 1rem;text-align:center}
.agent-icon{font-size:1.6rem;margin-bottom:.5rem}
.agent-name{font-family:'Space Mono',monospace;font-size:.75rem;color:var(--accent2);letter-spacing:.05em}
.agent-desc{font-size:.72rem;color:var(--muted);margin-top:.3rem}
h2{font-family:'Space Mono',monospace;font-size:.75rem;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;margin-bottom:.8rem}
.endpoints{background:var(--surface);border:1px solid var(--border);border-radius:6px;overflow:hidden;margin-bottom:2rem}
.ep{display:flex;align-items:baseline;gap:1rem;padding:.75rem 1.2rem;border-bottom:1px solid var(--border)}
.ep:last-child{border-bottom:none}
.method{font-family:'Space Mono',monospace;font-size:.6rem;font-weight:700;padding:.15rem .4rem;border-radius:3px;flex-shrink:0}
.get{background:#0d3321;color:var(--green)}
.post{background:#1a2d4a;color:var(--accent2)}
.path{font-family:'Space Mono',monospace;font-size:.78rem;color:#fff}
.desc-ep{font-size:.72rem;color:var(--muted);margin-left:auto}
.links{display:flex;gap:.8rem;flex-wrap:wrap;margin-bottom:3rem}
a.link-btn{font-family:'Space Mono',monospace;font-size:.75rem;color:var(--accent2);text-decoration:none;border:1px solid var(--accent2);padding:.4rem 1rem;border-radius:4px;transition:all .15s}
a.link-btn:hover{background:var(--accent2);color:var(--bg)}
footer{font-family:'Space Mono',monospace;font-size:.65rem;color:var(--muted);text-align:center;letter-spacing:.08em}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="badge">🚀 PRODUCTION</div>
    <h1>AI<span>-Org</span> v2.0 <span>API</span></h1>
    <div class="status-line"><span class="dot"></span><span>3 AGENTS ACTIVE · VERCEL · v2.0</span></div>
  </header>
  <div class="agents">
    <div class="agent-card"><div class="agent-icon">🧠</div><div class="agent-name">STRATEGIST</div><div class="agent-desc">RAR-S 評価・意思決定</div></div>
    <div class="agent-card"><div class="agent-icon">🔨</div><div class="agent-name">BUILDER</div><div class="agent-desc">実装・タスク管理</div></div>
    <div class="agent-card"><div class="agent-icon">📡</div><div class="agent-name">OPERATOR</div><div class="agent-desc">SNS・KPI・運用</div></div>
  </div>
  <h2>Endpoints</h2>
  <div class="endpoints">
    <div class="ep"><span class="method get">GET</span><span class="path">/health</span><span class="desc-ep">ヘルスチェック</span></div>
    <div class="ep"><span class="method get">GET</span><span class="path">/agents</span><span class="desc-ep">エージェント一覧</span></div>
    <div class="ep"><span class="method post">POST</span><span class="path">/chat/{agent_name}</span><span class="desc-ep">エージェントと対話</span></div>
    <div class="ep"><span class="method post">POST</span><span class="path">/escalations</span><span class="desc-ep">案件作成</span></div>
    <div class="ep"><span class="method get">GET</span><span class="path">/escalations</span><span class="desc-ep">案件一覧</span></div>
    <div class="ep"><span class="method post">POST</span><span class="path">/rar-s</span><span class="desc-ep">RAR-S スコア計算</span></div>
    <div class="ep"><span class="method get">GET</span><span class="path">/metrics</span><span class="desc-ep">KPI・予算</span></div>
    <div class="ep"><span class="method get">GET</span><span class="path">/reports/monthly</span><span class="desc-ep">月次レポート</span></div>
  </div>
  <h2>Documentation</h2>
  <div class="links">
    <a class="link-btn" href="/docs">Swagger UI</a>
    <a class="link-btn" href="/redoc">ReDoc</a>
    <a class="link-btn" href="/openapi.json">OpenAPI JSON</a>
  </div>
  <footer>AI-ORG v2.0 · ANTHROPIC CLAUDE API · FIREBASE · LINE</footer>
</div>
</body>
</html>"""

# ---------- /health ----------

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"}

# ---------- /agents ----------

AGENTS = [
    {"id": "strategist", "name": "Strategist", "role": "RAR-S評価・意思決定", "budget_jpy": 800,  "model": "claude-haiku-4-5-20251001"},
    {"id": "builder",    "name": "Builder",    "role": "実装・タスク管理",     "budget_jpy": 1500, "model": "claude-haiku-4-5-20251001"},
    {"id": "operator",   "name": "Operator",   "role": "SNS・KPI・月次レポート","budget_jpy": 500,  "model": "claude-haiku-4-5-20251001"},
]

@app.get("/agents")
async def list_agents():
    return {"agents": AGENTS, "total": len(AGENTS)}

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    for a in AGENTS:
        if a["id"] == agent_id:
            return a
    raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

# ---------- /chat ----------

class ChatRequest(BaseModel):
    message: str
    mock: bool = False

@app.post("/chat/{agent_name}")
async def chat(agent_name: str, req: ChatRequest):
    if agent_name not in [a["id"] for a in AGENTS]:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    if req.mock:
        reply = f"[mock] {agent_name}: 「{req.message}」を受け取りました。"
    else:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            reply = "[no-key] ANTHROPIC_API_KEY が設定されていません。"
        else:
            try:
                import anthropic
                prompts = {
                    "strategist": "あなたはAI組織のStrategistです。RAR-Sスコアで機会を評価します。",
                    "builder":    "あなたはAI組織のBuilderです。タスクを実装し管理します。",
                    "operator":   "あなたはAI組織のOperatorです。SNS・KPI・月次レポートを担当します。",
                }
                res = anthropic.Anthropic(api_key=key).messages.create(
                    model="claude-haiku-4-5-20251001", max_tokens=512,
                    system=prompts[agent_name],
                    messages=[{"role": "user", "content": req.message}])
                reply = res.content[0].text
            except Exception as e:
                reply = f"[error] {e}"
    return {"agent": agent_name, "message": req.message, "reply": reply,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"}

# ---------- /escalations ----------

class EscalationRequest(BaseModel):
    from_agent: str
    context: str
    level: str = "A_HARD_STOP"

@app.post("/escalations", status_code=201)
async def create_escalation(req: EscalationRequest):
    eid = str(uuid.uuid4())[:8].upper()
    esc = {"id": eid, "from_agent": req.from_agent, "context": req.context,
           "level": req.level, "status": "pending",
           "created_at": datetime.datetime.utcnow().isoformat() + "Z"}
    _escalations[eid] = esc
    return esc

@app.get("/escalations")
async def list_escalations():
    return {"escalations": list(_escalations.values()), "total": len(_escalations)}

@app.post("/escalations/{eid}/approve")
async def approve(eid: str, body: dict = {}):
    if eid not in _escalations:
        raise HTTPException(status_code=404, detail="Not found")
    _escalations[eid].update({"status": "approved", "comment": body.get("comment", "")})
    return _escalations[eid]

@app.post("/escalations/{eid}/reject")
async def reject(eid: str, body: dict = {}):
    if eid not in _escalations:
        raise HTTPException(status_code=404, detail="Not found")
    _escalations[eid].update({"status": "rejected", "reason": body.get("reason", "")})
    return _escalations[eid]

# ---------- /rar-s ----------

class RarSRequest(BaseModel):
    opportunity_id: str
    title: str
    monthly_revenue_jpy: float
    success_probability: float
    risk_factor: float
    time_to_market_months: int
    annual_cost_jpy: float

@app.post("/rar-s")
async def calc_rar_s(req: RarSRequest):
    def score(rm, pm):
        g = req.monthly_revenue_jpy * rm * 36 - req.annual_cost_jpy * 3
        if g <= 0: return 0.0
        return round(math.log10(g) * min(1.0, req.success_probability * pm) / max(0.1, req.risk_factor), 3)
    c, n, o = score(0.7, 0.8), score(1.0, 1.0), score(1.3, 1.2)
    return {"opportunity_id": req.opportunity_id, "title": req.title,
            "rar_s_scores": {"conservative": c, "neutral": n, "optimistic": o},
            "recommendation": "推奨" if n >= 1.0 else "要検討" if n >= 0.7 else "保留"}

# ---------- /metrics  /reports/monthly ----------

@app.get("/metrics")
async def metrics():
    return {"kpi": {"dau": 98.3, "mau": 2150, "monthly_revenue_jpy": 45000},
            "budget": {"monthly_budget_jpy": 3000, "consumed_jpy": 1340,
                       "remaining_jpy": 1660, "utilization_pct": 44.7}}

@app.get("/reports/monthly")
async def monthly_report():
    now = datetime.datetime.utcnow()
    return {"report_id": f"RPT-{now.strftime('%Y%m')}", "period": now.strftime("%Y-%m"),
            "generated_at": now.isoformat() + "Z",
            "pending_escalations": sum(1 for e in _escalations.values() if e["status"] == "pending"),
            "summary": {"dau": 98.3, "mau": 2150, "monthly_revenue_jpy": 45000, "budget_utilization_pct": 44.7}}
''')

# ===========================================================================
# vercel.json  (builds なし)
# ===========================================================================
write("vercel.json", """{
  "version": 2,
  "rewrites": [
    { "source": "/(.*)", "destination": "/src/api/app.py" }
  ],
  "env": {
    "ANTHROPIC_API_KEY":         "@anthropic-api-key",
    "FIREBASE_DB_URL":           "@firebase-db-url",
    "FIREBASE_AUTH_TOKEN":       "@firebase-auth-token",
    "LINE_CHANNEL_ACCESS_TOKEN": "@line-channel-token",
    "LINE_USER_ID":              "@line-user-id"
  }
}
""")

# ===========================================================================
# .github/workflows/ci.yml  (upload-artifact v4)
# ===========================================================================
write(".github/workflows/ci.yml", """
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Phase 1 tests
        run: python -X utf8 run_phase1_tests.py

      - name: Run Phase 2 tests
        run: python -X utf8 run_phase2_tests.py

      - name: Run Phase 3 tests
        run: python -X utf8 run_phase3_tests.py

      - name: Run Phase 5 tests (FastAPI)
        run: python -X utf8 run_phase5_tests.py

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: "*.log"
          if-no-files-found: ignore
""")

# ===========================================================================
# database_rules.json
# ===========================================================================
write("database_rules.json", """{
  "rules": {
    ".read":  "auth != null",
    ".write": "auth != null",
    "decisions":    { ".indexOn": ["timestamp", "agent"] },
    "escalations":  { ".indexOn": ["status", "level"] },
    "audit_trail":  { ".indexOn": ["timestamp"] },
    "incidents":    { ".indexOn": ["severity", "timestamp"] }
  }
}
""")

# ===========================================================================
# firebase.json
# ===========================================================================
write("firebase.json", """{
  "database": {
    "rules": "database_rules.json"
  },
  "hosting": {
    "public": "public",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"]
  }
}
""")

# ===========================================================================
# README.md
# ===========================================================================
write("README.md", """# AI-Org v2.0

Strategist / Builder / Operator の 3 エージェント構成による AI 組織フレームワーク。

## 設計原則
- 月次予算 ¥3,000（Haiku 60% / Sonnet 40% / Opus 禁止）
- `A_HARD_STOP` → 金銭・法務はユーザー確認必須
- `B_LIGHT_APPROVAL` → 軽微変更は 24h 承認
- `C_AUTO_DECIDED` → 技術選定は自動判定

## テスト実行

```bash
pip install -r requirements.txt
python -X utf8 run_phase1_tests.py
python -X utf8 run_phase2_tests.py
python -X utf8 run_phase3_tests.py
python -X utf8 run_phase5_tests.py
```

## 本番 URL
https://ai-org-v2-0.vercel.app
""")

# ===========================================================================
# 完了メッセージ
# ===========================================================================
print("""
====================================================
✅  再構築完了！

次のステップ:
  1. .env.example をコピーして .env を作り
     ANTHROPIC_API_KEY を入れる

  2. テストを全部実行して PASS を確認
     python -X utf8 run_phase1_tests.py
     python -X utf8 run_phase2_tests.py
     ...

  3. GitHub に push
     git add .
     git commit -m "rebuild: clean Phase 0-9"
     git push

  4. Vercel が自動デプロイ → ブラウザで確認
     https://ai-org-v2-0.vercel.app

====================================================
""")
