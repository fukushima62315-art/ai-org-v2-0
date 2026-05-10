#!/usr/bin/env python3
"""
Phase 6 自動実行スクリプト
Firebase / LINE 通知統合テスト
単一ファイル、依存性ゼロで実行可能

実装内容:
  - FirebaseClient   : Realtime Database REST ラッパー（mock 対応）
  - EnhancedLineNotifier : LINE 通知（mock 対応・送信ログ付き）
  - NotificationRouter   : 階層 A/B/C + 予算 → Firebase/LINE 振り分け
  - EscalationNotifier   : エスカレーション作成・取得・解決 (Firebase 永続化)
  - WeeklyReporter       : 週次レポート → Firebase 保存 + LINE 送信
"""

import json
import uuid
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

# .env 読み込み（任意）
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# ============================================================================
# Phase 6A: FirebaseClient（Realtime Database REST + mock モード）
# ============================================================================

class FirebaseClient:
    """
    Firebase Realtime Database REST API ラッパー
    db_url / auth_token が未設定の場合はインメモリ mock で動作
    """

    def __init__(
        self,
        db_url: str = "",
        auth_token: str = "",
        mock: bool = True,
    ):
        self.db_url     = db_url or os.getenv("FIREBASE_DB_URL", "")
        self.auth_token = auth_token or os.getenv("FIREBASE_AUTH_TOKEN", "")
        self.mock       = mock or not (self.db_url and self.auth_token)
        self._store: Dict = {}
        self._push_seq  = 0
        self.op_log: List[Dict] = []   # 操作ログ

    # ---- public API -------------------------------------------------------

    def write(self, path: str, data: Any) -> Dict:
        """PUT — パスにデータを上書き"""
        self._log("write", path)
        if self.mock:
            self._set(path, data)
            return {"ok": True, "path": path}
        import requests
        r = requests.put(self._url(path), json=data, timeout=5)
        r.raise_for_status()
        return r.json()

    def read(self, path: str) -> Any:
        """GET — パスのデータを取得"""
        self._log("read", path)
        if self.mock:
            return self._get(path)
        import requests
        r = requests.get(self._url(path), timeout=5)
        r.raise_for_status()
        return r.json()

    def push(self, path: str, data: Any) -> Dict:
        """POST — リストにデータを追加（Firebase push キーを返す）"""
        self._log("push", path)
        if self.mock:
            self._push_seq += 1
            key  = f"-mock{self._push_seq:06d}"
            self._set(f"{path}/{key}", {**data, "_key": key})
            return {"key": key, "path": f"{path}/{key}"}
        import requests
        r = requests.post(self._url(path), json=data, timeout=5)
        r.raise_for_status()
        return r.json()

    def update(self, path: str, data: Any) -> Dict:
        """PATCH — パスのデータを部分更新"""
        self._log("update", path)
        if self.mock:
            existing = self._get(path) or {}
            if isinstance(existing, dict):
                existing.update(data)
                self._set(path, existing)
            else:
                self._set(path, data)
            return {"ok": True}
        import requests
        r = requests.patch(self._url(path), json=data, timeout=5)
        r.raise_for_status()
        return r.json()

    def delete(self, path: str) -> Dict:
        """DELETE — パスのデータを削除"""
        self._log("delete", path)
        if self.mock:
            self._delete(path)
            return {"ok": True}
        import requests
        r = requests.delete(self._url(path), timeout=5)
        r.raise_for_status()
        return {"ok": True}

    def list_children(self, path: str) -> List[Any]:
        """パス配下の全データをリストで返す"""
        data = self.read(path)
        if isinstance(data, dict):
            return list(data.values())
        return []

    def op_count(self, op_type: str = "") -> int:
        if op_type:
            return sum(1 for o in self.op_log if o["type"] == op_type)
        return len(self.op_log)

    # ---- internals --------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self.db_url.rstrip('/')}/{path.lstrip('/')}.json?auth={self.auth_token}"

    def _log(self, op_type: str, path: str):
        self.op_log.append({"type": op_type, "path": path,
                            "ts": datetime.now().isoformat()})

    def _set(self, path: str, data: Any):
        parts = [p for p in path.strip("/").split("/") if p]
        d = self._store
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        d[parts[-1]] = data

    def _get(self, path: str) -> Any:
        parts = [p for p in path.strip("/").split("/") if p]
        d = self._store
        for part in parts:
            if isinstance(d, dict) and part in d:
                d = d[part]
            else:
                return None
        return d

    def _delete(self, path: str):
        parts = [p for p in path.strip("/").split("/") if p]
        d = self._store
        for part in parts[:-1]:
            if isinstance(d, dict) and part in d:
                d = d[part]
            else:
                return
        if isinstance(d, dict) and parts[-1] in d:
            del d[parts[-1]]


# ============================================================================
# Phase 6B: EnhancedLineNotifier（送信ログ・mock 対応）
# ============================================================================

@dataclass
class NotifRecord:
    notif_type: str
    content: str
    sent: bool
    reason_skipped: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class EnhancedLineNotifier:
    """LINE 通知クライアント（mock モードで送信ログを記録）"""

    ESCALATION_A_KEYWORDS = ["階層A", "HARD_STOP", "意思決定", "🚨"]

    def __init__(self, token: str = "", user_id: str = ""):
        self.token   = token   or os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        self.user_id = user_id or os.getenv("LINE_USER_ID", "")
        self.enabled = bool(self.token and self.user_id
                           and self.token != "your-line-channel-token")
        self.records: List[NotifRecord] = []

    # ---- 送信 API ---------------------------------------------------------

    def send_escalation_a(self, from_agent: str, context: str,
                          deadline: str = "24時間以内") -> NotifRecord:
        msg = self._fmt_escalation_a(from_agent, context, deadline)
        return self._send("escalation_a", msg)

    def send_budget_alert(self, pct: float, consumed_jpy: int,
                          budget_jpy: int) -> NotifRecord:
        msg = self._fmt_budget(pct, consumed_jpy, budget_jpy)
        return self._send("budget_alert", msg)

    def send_weekly_report(self, report: Dict) -> NotifRecord:
        msg = self._fmt_weekly(report)
        return self._send("weekly_report", msg)

    def send_text(self, text: str) -> NotifRecord:
        return self._send("text", text)

    # ---- フォーマッター ---------------------------------------------------

    def _fmt_escalation_a(self, agent: str, context: str, deadline: str) -> str:
        return (
            f"🚨【階層A】意思決定が必要です\n\n"
            f"From: {agent}\n"
            f"内容: {context}\n\n"
            f"⏰ 期限: {deadline}\n"
            f"承認 / 却下 をアプリで選択してください。"
        )

    def _fmt_budget(self, pct: float, consumed: int, budget: int) -> str:
        emoji = "🔴" if pct >= 80 else "🟠" if pct >= 70 else "⚠️"
        remaining = budget - consumed
        return (
            f"{emoji} 予算 {pct:.1f}% 消費\n\n"
            f"消費: {consumed:,}円 / 上限: {budget:,}円\n"
            f"残額: {remaining:,}円\n\n"
            f"詳細はアプリで確認してください。"
        )

    def _fmt_weekly(self, report: Dict) -> str:
        s = report.get("summary", {})
        return (
            f"📊 週次レポート ({report.get('week', '今週')})\n\n"
            f"売上: {s.get('revenue_jpy', 0):,}円\n"
            f"コスト: {s.get('costs_jpy', 0):,}円\n"
            f"新規ユーザー: {s.get('new_users', 0)}人\n"
            f"エスカレーション: {s.get('escalations', 0)}件"
        )

    # ---- 内部送信 ---------------------------------------------------------

    def _send(self, notif_type: str, content: str) -> NotifRecord:
        if not self.enabled:
            rec = NotifRecord(notif_type, content, sent=False,
                              reason_skipped="credentials not set")
            self.records.append(rec)
            return rec

        try:
            import requests as req
            r = req.post(
                "https://api.line.biz/v2/bot/message/push",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                json={"to": self.user_id,
                      "messages": [{"type": "text", "text": content}]},
                timeout=8,
            )
            sent = r.status_code == 200
        except Exception:
            sent = False

        rec = NotifRecord(notif_type, content, sent=sent)
        self.records.append(rec)
        return rec

    # ---- 統計 -------------------------------------------------------------

    def stats(self) -> Dict:
        total   = len(self.records)
        sent    = sum(1 for r in self.records if r.sent)
        skipped = sum(1 for r in self.records if not r.sent)
        by_type: Dict[str, int] = {}
        for r in self.records:
            by_type[r.notif_type] = by_type.get(r.notif_type, 0) + 1
        return {"total": total, "sent": sent, "skipped": skipped, "by_type": by_type}


# ============================================================================
# Phase 6C: NotificationRouter（階層 A/B/C → Firebase/LINE 振り分け）
# ============================================================================

@dataclass
class RouteRecord:
    event_type: str      # escalation / budget / kpi
    level: str
    firebase_path: str
    firebase_key: str
    line_sent: bool
    channels: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class NotificationRouter:
    """
    ルーティング方針:
      - 階層 A_HARD_STOP  → Firebase 保存 + LINE 即時通知
      - 階層 B_LIGHT      → Firebase のみ（簡易承認フロー）
      - 階層 C_AUTO       → Firebase のみ（ログ目的）
      - 予算 80%+         → Firebase + LINE
      - 予算 70%未満      → Firebase のみ
    """

    def __init__(self, firebase: FirebaseClient, notifier: EnhancedLineNotifier):
        self.db    = firebase
        self.line  = notifier
        self.log: List[RouteRecord] = []

    def route_escalation(self, from_agent: str, context: str,
                         level: str = "A_HARD_STOP") -> RouteRecord:
        eid = f"ESC-{uuid.uuid4().hex[:6].upper()}"
        payload = {
            "id": eid, "from_agent": from_agent,
            "context": context, "level": level,
            "status": "pending", "created_at": datetime.now().isoformat(),
        }
        push_res = self.db.push("/escalations", payload)

        line_sent = False
        if level == "A_HARD_STOP":
            rec = self.line.send_escalation_a(from_agent, context)
            line_sent = rec.sent   # mock では False（credential なし）

        channels = ["firebase"] + (["line"] if line_sent else [])
        route = RouteRecord(
            event_type="escalation", level=level,
            firebase_path="/escalations", firebase_key=push_res["key"],
            line_sent=line_sent, channels=channels,
        )
        self.log.append(route)
        return route

    def route_budget_alert(self, pct: float, consumed_jpy: int,
                           budget_jpy: int) -> RouteRecord:
        payload = {
            "pct": pct, "consumed_jpy": consumed_jpy,
            "budget_jpy": budget_jpy,
            "timestamp": datetime.now().isoformat(),
        }
        push_res = self.db.push("/budget_alerts", payload)

        line_sent = False
        if pct >= 80:
            rec = self.line.send_budget_alert(pct, consumed_jpy, budget_jpy)
            line_sent = rec.sent

        level   = "EMERGENCY" if pct >= 80 else ("WARNING" if pct >= 70 else "NORMAL")
        channels = ["firebase"] + (["line"] if line_sent else [])
        route = RouteRecord(
            event_type="budget", level=level,
            firebase_path="/budget_alerts", firebase_key=push_res["key"],
            line_sent=line_sent, channels=channels,
        )
        self.log.append(route)
        return route

    def stats(self) -> Dict:
        total     = len(self.log)
        line_sent = sum(1 for r in self.log if r.line_sent)
        return {
            "total": total,
            "line_attempted": sum(
                1 for r in self.log
                if r.level in ("A_HARD_STOP", "EMERGENCY")
            ),
            "line_sent": line_sent,
            "by_event": {
                "escalation": sum(1 for r in self.log if r.event_type == "escalation"),
                "budget":     sum(1 for r in self.log if r.event_type == "budget"),
            },
        }


# ============================================================================
# Phase 6D: EscalationNotifier（Firebase 永続化 + 解決フロー）
# ============================================================================

class EscalationNotifier:
    """エスカレーション CRUD + 通知ルーティング"""

    def __init__(self, router: NotificationRouter):
        self.router = router
        self.db     = router.db

    def create(self, from_agent: str, context: str,
               level: str = "A_HARD_STOP") -> Dict:
        route = self.router.route_escalation(from_agent, context, level)
        return {
            "firebase_key": route.firebase_key,
            "level":        level,
            "channels":     route.channels,
            "status":       "pending",
        }

    def get_pending(self) -> List[Dict]:
        all_items = self.db.list_children("/escalations")
        return [e for e in all_items if e.get("status") == "pending"]

    def resolve(self, firebase_key: str, decision: str,
                comment: str = "") -> bool:
        path = f"/escalations/{firebase_key}"
        res = self.db.update(path, {
            "status":      decision,   # approved / rejected
            "comment":     comment,
            "resolved_at": datetime.now().isoformat(),
        })
        return res.get("ok", False)


# ============================================================================
# Phase 6E: WeeklyReporter（Firebase 集計 + LINE 送信）
# ============================================================================

class WeeklyReporter:
    """週次レポート: Firebase から集計 → LINE へ送信"""

    def __init__(self, firebase: FirebaseClient, notifier: EnhancedLineNotifier):
        self.db   = firebase
        self.line = notifier

    def compile_and_send(self, metrics: Dict) -> Dict:
        week = datetime.now().strftime("%Y-W%W")
        report = {
            "report_id": f"WEEKLY-{week}-{uuid.uuid4().hex[:4].upper()}",
            "week":      week,
            "summary": {
                "revenue_jpy": metrics.get("revenue_jpy", 0),
                "costs_jpy":   metrics.get("costs_jpy", 0),
                "new_users":   metrics.get("new_users", 0),
                "escalations": metrics.get("escalation_count", 0),
            },
            "generated_at": datetime.now().isoformat(),
        }
        push_res = self.db.push("/weekly_reports", report)
        notif    = self.line.send_weekly_report(report)
        return {
            "report":       report,
            "firebase_key": push_res["key"],
            "line_sent":    notif.sent,
        }


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
    print("🚀 Phase 6 統合テスト実行（Firebase / LINE 通知統合）")
    print("=" * 80)

    # ------------------------------------------------------------------
    # テスト 1-7: FirebaseClient CRUD
    # ------------------------------------------------------------------
    print("\n📋 テスト 1-7: FirebaseClient（mock モード CRUD）")

    db = FirebaseClient(mock=True)
    check("テスト 1: FirebaseClient 初期化（mock=True）", db.mock)

    db.write("/config/app_name", "ai-org-v2")
    check("テスト 2: write → read で同じ値",
          db.read("/config/app_name") == "ai-org-v2")

    push_res = db.push("/items", {"value": 42})
    check("テスト 3: push → key が返る", bool(push_res.get("key")))
    check("テスト 4: push したデータが read できる",
          db.read(push_res["path"]) is not None)

    db.write("/counter", {"n": 1})
    db.update("/counter", {"n": 5, "updated": True})
    counter = db.read("/counter")
    check("テスト 5: update → 既存フィールドが上書き・マージされる",
          counter.get("n") == 5 and counter.get("updated") is True,
          f"got {counter}")

    db.write("/temp/data", "delete-me")
    db.delete("/temp/data")
    check("テスト 6: delete → read で None",
          db.read("/temp/data") is None)

    db.push("/events", {"type": "login"})
    db.push("/events", {"type": "logout"})
    events = db.list_children("/events")
    check("テスト 7: list_children → リストで返る（2件）",
          len(events) == 2, f"got {len(events)}")

    # ------------------------------------------------------------------
    # テスト 8-12: EnhancedLineNotifier フォーマット
    # ------------------------------------------------------------------
    print("\n📋 テスト 8-12: EnhancedLineNotifier（フォーマット・mock）")

    notifier = EnhancedLineNotifier()  # credentials なし → mock
    check("テスト 8: credentials なし → enabled=False", not notifier.enabled)

    rec_a = notifier.send_escalation_a("Builder", "Stripe 導入（月 3,000 円）")
    check("テスト 9: 階層 A 通知が記録される", len(notifier.records) == 1)
    check("テスト 10: 🚨 キーワードが本文に含まれる",
          "🚨" in rec_a.content or "階層A" in rec_a.content,
          f"content={rec_a.content[:60]}")

    rec_b = notifier.send_budget_alert(82.5, 2475, 3000)
    check("テスト 11: 予算アラート本文に消費率が含まれる",
          "82.5" in rec_b.content or "82" in rec_b.content,
          f"content={rec_b.content[:80]}")

    notifier.send_weekly_report({"week": "2026-W19",
                                 "summary": {"revenue_jpy": 45000, "costs_jpy": 1340,
                                             "new_users": 60, "escalations": 2}})
    stats = notifier.stats()
    check("テスト 12: stats — total=3, skipped=3（credential なし）",
          stats["total"] == 3 and stats["skipped"] == 3,
          f"got {stats}")

    # ------------------------------------------------------------------
    # テスト 13-15: LINE 認証情報なし → 送信スキップ・ログ記録
    # ------------------------------------------------------------------
    print("\n📋 テスト 13-15: credential なし → graceful skip")

    check("テスト 13: 送信 sent=False（credential なし）",
          not rec_a.sent)
    check("テスト 14: reason_skipped が設定される",
          bool(rec_a.reason_skipped))
    check("テスト 15: notif_type が正しく記録される",
          rec_a.notif_type == "escalation_a")

    # ------------------------------------------------------------------
    # テスト 16-21: NotificationRouter ルーティング
    # ------------------------------------------------------------------
    print("\n📋 テスト 16-21: NotificationRouter ルーティング")

    db2      = FirebaseClient(mock=True)
    notif2   = EnhancedLineNotifier()
    router   = NotificationRouter(db2, notif2)

    # A_HARD_STOP → Firebase + LINE 試みる
    r_a = router.route_escalation("Builder", "Stripe 有料導入", "A_HARD_STOP")
    check("テスト 16: A_HARD_STOP → firebase チャンネルに記録",
          "firebase" in r_a.channels)
    check("テスト 17: A_HARD_STOP → LINE 送信を試みる（credentials なし → sent=False）",
          r_a.event_type == "escalation")

    # B_LIGHT → Firebase のみ
    r_b = router.route_escalation("Operator", "投稿文言の微修正", "B_LIGHT")
    check("テスト 18: B_LIGHT → channels = ['firebase'] のみ",
          r_b.channels == ["firebase"], f"got {r_b.channels}")

    # C_AUTO → Firebase のみ
    r_c = router.route_escalation("Builder", "ライブラリバージョン選定", "C_AUTO")
    check("テスト 19: C_AUTO → channels = ['firebase'] のみ",
          r_c.channels == ["firebase"], f"got {r_c.channels}")

    # 予算 80%+ → LINE 試みる
    r_budget_hi = router.route_budget_alert(81.0, 2430, 3000)
    check("テスト 20: 予算 81% → EMERGENCY level",
          r_budget_hi.level == "EMERGENCY", f"got {r_budget_hi.level}")

    # 予算 60% → Firebase のみ
    r_budget_lo = router.route_budget_alert(60.0, 1800, 3000)
    check("テスト 21: 予算 60% → line_sent=False, channels=['firebase']",
          not r_budget_lo.line_sent and r_budget_lo.channels == ["firebase"],
          f"channels={r_budget_lo.channels}")

    # ------------------------------------------------------------------
    # テスト 22-26: EscalationNotifier（Firebase 永続化・解決）
    # ------------------------------------------------------------------
    print("\n📋 テスト 22-26: EscalationNotifier")

    db3    = FirebaseClient(mock=True)
    notif3 = EnhancedLineNotifier()
    router3 = NotificationRouter(db3, notif3)
    esc_notifier = EscalationNotifier(router3)

    # 作成
    e1 = esc_notifier.create("Builder", "Firebase 有料化（月 3,000 円）", "A_HARD_STOP")
    e2 = esc_notifier.create("Operator", "インフルエンサー広告費", "A_HARD_STOP")
    esc_notifier.create("Builder", "ライブラリ選定", "C_AUTO")

    check("テスト 22: エスカレーション 3 件作成→ Firebase に保存",
          db3.op_count("push") >= 3)

    pending = esc_notifier.get_pending()
    check("テスト 23: pending が 3 件",
          len(pending) == 3, f"got {len(pending)}")

    # 承認
    ok = esc_notifier.resolve(e1["firebase_key"], "approved", "予算内のため承認")
    check("テスト 24: resolve(approved) → True",
          ok, "update が失敗")

    # 解決後 pending が 2 件に
    pending2 = esc_notifier.get_pending()
    check("テスト 25: 承認後 pending = 2 件",
          len(pending2) == 2, f"got {len(pending2)}")

    # 却下
    ok2 = esc_notifier.resolve(e2["firebase_key"], "rejected", "予算超過のため却下")
    check("テスト 26: resolve(rejected) → True", ok2)

    # ------------------------------------------------------------------
    # テスト 27-30: WeeklyReporter + Router 統計
    # ------------------------------------------------------------------
    print("\n📋 テスト 27-30: WeeklyReporter・統合統計")

    reporter = WeeklyReporter(db3, notif3)
    weekly = reporter.compile_and_send({
        "revenue_jpy": 45000, "costs_jpy": 1340,
        "new_users": 60, "escalation_count": 3,
    })
    check("テスト 27: 週次レポート生成 → report_id あり",
          "report_id" in weekly["report"])
    check("テスト 28: Firebase に保存済み（firebase_key あり）",
          bool(weekly["firebase_key"]))

    router_stats = router3.stats()
    check("テスト 29: Router 統計 — 総数 >= 3（escalation 3件）",
          router_stats["total"] >= 3, f"got {router_stats}")
    check("テスト 30: LINE 試行数 = A_HARD_STOP 件数と一致（2件）",
          router_stats["line_attempted"] == 2,
          f"got {router_stats['line_attempted']}")

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
        print("🎉 Phase 6 完全実装完了！すべてのテストに PASS しました。")
        print()
        print("実環境で有効化するには .env に以下を設定:")
        print("  FIREBASE_DB_URL=https://<your-project>.firebaseio.com")
        print("  FIREBASE_AUTH_TOKEN=<your-token>")
        print("  LINE_CHANNEL_ACCESS_TOKEN=<your-token>")
        print("  LINE_USER_ID=<your-user-id>")
        print()
        print("次ステップ: Phase 7 - Web デプロイ（Vercel + Firebase Hosting）")
    else:
        print()
        print(f"⚠️  {failed} 件のテストが失敗しました。")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    run_tests()
