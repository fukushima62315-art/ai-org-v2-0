"""
src/api/app.py
AI-Org v2.0 FastAPI バックエンド — React フロントエンド向け REST API

エンドポイント:
  GET  /health                    ヘルスチェック
  GET  /agents                    エージェント一覧
  POST /chat/{agent}              エージェントとチャット
  POST /escalations               エスカレーション作成
  GET  /escalations               エスカレーション一覧
  POST /escalations/{id}/approve  承認
  POST /escalations/{id}/reject   却下
  POST /rar-s                     RAR-S スコア計算
  GET  /metrics                   KPI・予算メトリクス
  GET  /reports/monthly           月次レポート
"""

import math
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI-Org v2.0 API",
    description="Strategist / Builder / Operator エージェント管理 REST API",
    version="2.0.0",
)

# React 開発サーバー向け CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# インメモリ状態
# ============================================================

escalations_db: Dict[str, Dict] = {}
chat_history:   List[Dict]      = []

AGENTS = {
    "strategist": {
        "id":         "strategist",
        "name":       "Strategist",
        "role":       "市場戦略・企画・コンプライアンス",
        "budget_jpy": 800,
        "model":      "claude-haiku-4-5-20251001",
    },
    "builder": {
        "id":         "builder",
        "name":       "Builder",
        "role":       "開発・実装・QA",
        "budget_jpy": 1500,
        "model":      "claude-haiku-4-5-20251001",
    },
    "operator": {
        "id":         "operator",
        "name":       "Operator",
        "role":       "SNS運用・財務・ユーザー獲得",
        "budget_jpy": 500,
        "model":      "claude-haiku-4-5-20251001",
    },
}

MOCK_REPLIES = {
    "strategist": (
        "Strategist です。市場分析とコンプライアンス判定を担当します。"
        "金銭・法務リスクは必ずユーザー確認（階層A）が必要です。"
    ),
    "builder": (
        "Builder です。実装とテストを担当します。"
        "有料 SaaS 導入前は必ず Strategist に相談します。"
    ),
    "operator": (
        "Operator です。SNS 運用と KPI 監視を担当します。"
        "有償広告はユーザー承認（階層A）が必要です。"
    ),
}

# ============================================================
# エンドポイント
# ============================================================

@app.get("/")
def root():
    return {
        "message": "AI-Org v2.0 API へようこそ",
        "version": "2.0",
        "endpoints": {
            "/health": "ヘルスチェック",
            "/agents": "エージェント一覧",
            "/agents/{agent_id}": "特定エージェント情報",
            "/chat/{agent_name}": "エージェントとチャット",
            "/escalations": "エスカレーション管理",
            "/rar-s": "RAR-S スコア計算",
            "/metrics": "KPI・予算メトリクス",
            "/reports/monthly": "月次レポート",
            "/openapi.json": "API ドキュメント",
        },
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }

@app.get("/health")
def health():
    return {
        "status":    "ok",
        "version":   "2.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/agents")
def list_agents():
    return {"agents": list(AGENTS.values()), "total": len(AGENTS)}


@app.get("/agents/{agent_id}")
def get_agent(agent_id: str):
    if agent_id not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return AGENTS[agent_id]


@app.post("/chat/{agent_name}")
def chat(agent_name: str, body: Dict[str, Any] = Body(...)):
    if agent_name not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    message = body.get("message", "")
    mock    = body.get("mock", True)   # mock=False で実 API 呼び出し

    if mock or not message:
        reply = MOCK_REPLIES[agent_name]
    else:
        # 実 Claude API 呼び出し（Phase 4 ClaudeAPIClient を使用）
        try:
            import os, sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from run_phase4_tests import ClaudeAPIClient, STRATEGIST_SYSTEM, BUILDER_SYSTEM, OPERATOR_SYSTEM
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).parent.parent.parent / ".env")

            prompts = {
                "strategist": STRATEGIST_SYSTEM,
                "builder":    BUILDER_SYSTEM,
                "operator":   OPERATOR_SYSTEM,
            }
            client = ClaudeAPIClient(os.getenv("ANTHROPIC_API_KEY", ""))
            reply, _ = client.call(agent_name, prompts[agent_name], message,
                                   max_tokens=200)
        except Exception as e:
            reply = f"[API Error: {e}] " + MOCK_REPLIES[agent_name]

    record = {
        "id":        f"MSG-{uuid.uuid4().hex[:8].upper()}",
        "agent":     agent_name,
        "message":   message,
        "reply":     reply,
        "mock":      mock,
        "timestamp": datetime.now().isoformat(),
    }
    chat_history.append(record)
    return record


@app.post("/escalations", status_code=201)
def create_escalation(body: Dict[str, Any] = Body(...)):
    eid = f"ESC-{uuid.uuid4().hex[:8].upper()}"
    escalation = {
        "id":         eid,
        "from_agent": body.get("from_agent", "unknown"),
        "context":    body.get("context", ""),
        "level":      body.get("level", "A_HARD_STOP"),
        "status":     "pending",
        "created_at": datetime.now().isoformat(),
    }
    escalations_db[eid] = escalation
    return escalation


@app.get("/escalations")
def list_escalations(status: Optional[str] = None):
    items = list(escalations_db.values())
    if status:
        items = [e for e in items if e["status"] == status]
    return {"escalations": items, "total": len(items)}


@app.post("/escalations/{esc_id}/approve")
def approve_escalation(esc_id: str, body: Dict[str, Any] = Body(default={})):
    if esc_id not in escalations_db:
        raise HTTPException(status_code=404, detail="Escalation not found")
    escalations_db[esc_id].update({
        "status":      "approved",
        "comment":     body.get("comment", ""),
        "resolved_at": datetime.now().isoformat(),
    })
    return escalations_db[esc_id]


@app.post("/escalations/{esc_id}/reject")
def reject_escalation(esc_id: str, body: Dict[str, Any] = Body(default={})):
    if esc_id not in escalations_db:
        raise HTTPException(status_code=404, detail="Escalation not found")
    escalations_db[esc_id].update({
        "status":        "rejected",
        "reject_reason": body.get("reason", ""),
        "resolved_at":   datetime.now().isoformat(),
    })
    return escalations_db[esc_id]


@app.post("/rar-s")
def calculate_rar_s(body: Dict[str, Any] = Body(...)):
    monthly_rev  = float(body.get("monthly_revenue_jpy", 100_000))
    prob         = float(body.get("success_probability", 0.5))
    risk         = float(body.get("risk_factor", 1.0))
    months       = int(body.get("time_to_market_months", 6))
    annual_cost  = float(body.get("annual_cost_jpy", 0))

    REF = 1_200_000

    def score(rev, p, r, m):
        ev  = rev * 12 * p
        sp  = max(0.5, m / 6)
        den = REF * max(0.1, r) * sp
        return round(max(0.3, min(1.5, math.log10(max(ev, 1) / den) + 1.0)), 3)

    scenarios = {
        "conservative": score(monthly_rev * 0.5, prob * 0.7, risk * 1.3, months),
        "neutral":      score(monthly_rev,        prob,       risk,        months),
        "optimistic":   score(monthly_rev * 1.5,  prob * 1.2, risk * 0.8, months),
    }

    return {
        "opportunity_id":    body.get("opportunity_id",
                                      f"OPP-{uuid.uuid4().hex[:6].upper()}"),
        "title":             body.get("title", "無題"),
        "rar_s_scores":      scenarios,
        "money_required":    annual_cost > 0,
        "needs_user_approval": annual_cost > 0,
        "calculated_at":     datetime.now().isoformat(),
    }


@app.get("/metrics")
def get_metrics():
    pending = sum(1 for e in escalations_db.values() if e["status"] == "pending")
    return {
        "period": datetime.now().strftime("%Y-%m"),
        "kpi": {
            "avg_dau":           98.3,
            "mau":               2150,
            "retention_rate_pct": 4.6,
            "total_revenue_jpy": 45000,
        },
        "budget": {
            "monthly_budget_jpy": 3000,
            "consumed_jpy":       1340,
            "remaining_jpy":      1660,
            "utilization_pct":    44.7,
        },
        "escalations": {
            "pending":  pending,
            "total":    len(escalations_db),
        },
        "agents": {a: {"calls": 0} for a in AGENTS},
    }


@app.get("/reports/monthly")
def monthly_report():
    pending = sum(1 for e in escalations_db.values() if e["status"] == "pending")
    return {
        "report_id":  f"MONTHLY-{datetime.now().strftime('%Y-%m')}-"
                      f"{uuid.uuid4().hex[:6].upper()}",
        "month":      datetime.now().strftime("%Y-%m"),
        "summary": {
            "revenue_jpy":  45000,
            "costs_jpy":    1340,
            "cashflow_jpy": 43660,
            "new_users":    215,
        },
        "top_opportunities":     [],
        "pending_escalations":   pending,
        "generated_at":          datetime.now().isoformat(),
    }
