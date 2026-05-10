#!/usr/bin/env python3
"""
Phase 5 自動実行スクリプト
React フロントエンド統合 — FastAPI バックエンド REST API テスト

テスト内容:
  - FastAPI アプリ起動・ヘルスチェック
  - /agents エンドポイント（エージェント一覧）
  - /chat/{agent} エンドポイント（チャット）
  - /escalations エンドポイント（エスカレーション CRUD）
  - /rar-s エンドポイント（RAR-S 計算）
  - /metrics エンドポイント（KPI・予算）
  - /reports/monthly エンドポイント（月次レポート）
  - CORS ヘッダー・OpenAPI ドキュメント
"""

import sys
import time
import json
import threading
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8765"

# ============================================================================
# サーバー起動（バックグラウンドスレッド）
# ============================================================================

def start_server():
    import uvicorn
    sys.path.insert(0, str(Path(__file__).parent))
    from src.api.app import app
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="error")

def wait_for_server(timeout: int = 10) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


# ============================================================================
# テスト実行
# ============================================================================

def run_tests():
    passed = 0
    failed = 0
    errors = []

    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}" + (f"\n     {detail}" if detail else ""))
            failed += 1
            errors.append(name)

    print("=" * 80)
    print("🚀 Phase 5 統合テスト実行（FastAPI バックエンド）")
    print(f"   ベース URL: {BASE_URL}")
    print("=" * 80)

    # ------------------------------------------------------------------
    # サーバー起動
    # ------------------------------------------------------------------
    print("\n⚙️  FastAPI サーバーを起動中...")
    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()
    ready = wait_for_server()
    if not ready:
        print("❌ サーバーが起動しませんでした。テストを中断します。")
        sys.exit(1)
    print("  ✅ サーバー起動完了\n")

    # ------------------------------------------------------------------
    # テスト 1-4: ヘルスチェック・基本
    # ------------------------------------------------------------------
    print("📋 テスト 1-4: ヘルスチェック・基本")

    r = requests.get(f"{BASE_URL}/health")
    check("テスト 1: GET /health → 200", r.status_code == 200,
          f"status={r.status_code}")

    body = r.json()
    check("テスト 2: status = 'ok'", body.get("status") == "ok",
          f"got {body}")
    check("テスト 3: version フィールドあり", "version" in body)
    check("テスト 4: timestamp フィールドあり", "timestamp" in body)

    # ------------------------------------------------------------------
    # テスト 5-9: /agents エンドポイント
    # ------------------------------------------------------------------
    print("\n📋 テスト 5-9: /agents エンドポイント")

    r = requests.get(f"{BASE_URL}/agents")
    check("テスト 5: GET /agents → 200", r.status_code == 200)

    body = r.json()
    check("テスト 6: agents リストあり", "agents" in body)
    check("テスト 7: エージェント 3 件",
          body.get("total") == 3, f"got {body.get('total')}")
    check("テスト 8: 各エージェントに budget_jpy あり",
          all("budget_jpy" in a for a in body["agents"]))

    r2 = requests.get(f"{BASE_URL}/agents/builder")
    check("テスト 9: GET /agents/builder → 200 + role あり",
          r2.status_code == 200 and "role" in r2.json(),
          f"status={r2.status_code}")

    # ------------------------------------------------------------------
    # テスト 10-14: /chat エンドポイント
    # ------------------------------------------------------------------
    print("\n📋 テスト 10-14: /chat エンドポイント")

    payload = {"message": "あなたの役割は何ですか？", "mock": True}

    r = requests.post(f"{BASE_URL}/chat/strategist", json=payload)
    check("テスト 10: POST /chat/strategist → 200",
          r.status_code == 200, f"status={r.status_code}")
    check("テスト 11: reply フィールドあり",
          "reply" in r.json(), f"keys={list(r.json().keys())}")

    r = requests.post(f"{BASE_URL}/chat/builder", json=payload)
    check("テスト 12: POST /chat/builder → 200", r.status_code == 200)

    r = requests.post(f"{BASE_URL}/chat/operator", json=payload)
    check("テスト 13: POST /chat/operator → 200", r.status_code == 200)

    r = requests.post(f"{BASE_URL}/chat/unknown_agent", json=payload)
    check("テスト 14: 存在しないエージェント → 404",
          r.status_code == 404, f"status={r.status_code}")

    # ------------------------------------------------------------------
    # テスト 15-21: /escalations エンドポイント（CRUD）
    # ------------------------------------------------------------------
    print("\n📋 テスト 15-21: /escalations エンドポイント (CRUD)")

    # 作成
    esc_payload = {
        "from_agent": "Builder",
        "context":    "Stripe 導入に月 3,000 円が発生する",
        "level":      "A_HARD_STOP",
    }
    r = requests.post(f"{BASE_URL}/escalations", json=esc_payload)
    check("テスト 15: POST /escalations → 201",
          r.status_code == 201, f"status={r.status_code}")

    esc = r.json()
    esc_id = esc.get("id", "")
    check("テスト 16: id フィールドあり", bool(esc_id))
    check("テスト 17: status = 'pending'",
          esc.get("status") == "pending", f"got {esc.get('status')}")

    # 一覧
    r = requests.get(f"{BASE_URL}/escalations")
    check("テスト 18: GET /escalations → 200 + リストあり",
          r.status_code == 200 and "escalations" in r.json())

    # 承認
    r = requests.post(f"{BASE_URL}/escalations/{esc_id}/approve",
                      json={"comment": "承認します"})
    check("テスト 19: POST /escalations/{id}/approve → 200",
          r.status_code == 200, f"status={r.status_code}")
    check("テスト 20: status = 'approved'",
          r.json().get("status") == "approved", f"got {r.json().get('status')}")

    # 却下（新規作成して却下）
    r2 = requests.post(f"{BASE_URL}/escalations", json={
        "from_agent": "Operator", "context": "インフルエンサー費用 10 万円", "level": "A_HARD_STOP"
    })
    esc_id2 = r2.json().get("id")
    r3 = requests.post(f"{BASE_URL}/escalations/{esc_id2}/reject",
                       json={"reason": "予算超過のため却下"})
    check("テスト 21: POST /escalations/{id}/reject → status='rejected'",
          r3.json().get("status") == "rejected", f"got {r3.json().get('status')}")

    # ------------------------------------------------------------------
    # テスト 22-25: /rar-s エンドポイント
    # ------------------------------------------------------------------
    print("\n📋 テスト 22-25: /rar-s エンドポイント")

    rar_payload = {
        "opportunity_id":      "OPP-TEST-001",
        "title":               "英会話アプリ月額プラン",
        "monthly_revenue_jpy": 200_000,
        "success_probability": 0.6,
        "risk_factor":         0.8,
        "time_to_market_months": 4,
        "annual_cost_jpy":     500_000,
    }
    r = requests.post(f"{BASE_URL}/rar-s", json=rar_payload)
    check("テスト 22: POST /rar-s → 200", r.status_code == 200,
          f"status={r.status_code}")

    rar = r.json()
    check("テスト 23: rar_s_scores フィールドあり", "rar_s_scores" in rar)
    scores = rar.get("rar_s_scores", {})
    check("テスト 24: neutral スコア範囲 [0.3, 1.5]",
          0.3 <= scores.get("neutral", -1) <= 1.5,
          f"got {scores.get('neutral')}")
    check("テスト 25: optimistic >= neutral >= conservative",
          scores.get("optimistic", 0) >= scores.get("neutral", 0)
          >= scores.get("conservative", 0),
          f"scores={scores}")

    # ------------------------------------------------------------------
    # テスト 26-28: /metrics と /reports/monthly
    # ------------------------------------------------------------------
    print("\n📋 テスト 26-28: /metrics・/reports/monthly")

    r = requests.get(f"{BASE_URL}/metrics")
    check("テスト 26: GET /metrics → 200 + kpi/budget あり",
          r.status_code == 200
          and "kpi" in r.json()
          and "budget" in r.json())

    r = requests.get(f"{BASE_URL}/reports/monthly")
    check("テスト 27: GET /reports/monthly → 200 + report_id あり",
          r.status_code == 200 and "report_id" in r.json(),
          f"keys={list(r.json().keys())}")
    check("テスト 28: pending_escalations が数値",
          isinstance(r.json().get("pending_escalations"), int),
          f"got {r.json().get('pending_escalations')}")

    # ------------------------------------------------------------------
    # テスト 29-30: OpenAPI ドキュメント・CORS
    # ------------------------------------------------------------------
    print("\n📋 テスト 29-30: OpenAPI・CORS")

    r = requests.get(f"{BASE_URL}/openapi.json")
    check("テスト 29: GET /openapi.json → 200 (API ドキュメント)",
          r.status_code == 200 and "paths" in r.json(),
          f"status={r.status_code}")

    r = requests.options(
        f"{BASE_URL}/agents",
        headers={"Origin": "http://localhost:3000",
                 "Access-Control-Request-Method": "GET"},
    )
    check("テスト 30: CORS プリフライト → 200",
          r.status_code == 200,
          f"status={r.status_code}")

    # ------------------------------------------------------------------
    # サマリー
    # ------------------------------------------------------------------
    total = passed + failed
    print()
    print("=" * 80)
    print("📊 テスト結果サマリー")
    print("=" * 80)
    print(f"✅ 成功: {passed}/{total}")
    print(f"❌ 失敗: {failed}/{total}")
    print(f"📈 成功率: {passed / total * 100:.1f}%")
    print("=" * 80)

    if failed == 0:
        print()
        print("🎉 Phase 5 完全実装完了！すべてのテストに PASS しました。")
        print()
        print("React フロントエンドからアクセス可能なエンドポイント:")
        for path in ["/health", "/agents", "/chat/{agent}", "/escalations",
                     "/rar-s", "/metrics", "/reports/monthly"]:
            print(f"  {BASE_URL}{path}")
        print()
        print("次ステップ: Phase 6 - Firebase / LINE 通知統合")
    else:
        print()
        print(f"⚠️  {failed} 件のテストが失敗しました。")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    run_tests()
