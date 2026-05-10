#!/usr/bin/env python3
"""
Phase 3 自動実行スクリプト
Builder × Operator 統合テスト
単一ファイル、依存性ゼロで実行可能

実装内容:
  - TaskQueue          : Builder タスク管理（分解・優先度・ステータス）
  - ReleaseChecker     : リリース前チェック（セキュリティ・法務・UX）
  - SNSScheduler       : Operator SNS 投稿管理（炎上リスク判定）
  - KPITracker         : DAU/MAU/リテンション監視・アラート
  - FinancialReport    : 月次財務レポート（収支・予算消化率）
  - AgentCoordinator   : エージェント間連携・エスカレーション
"""

import json
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from enum import Enum

# ============================================================================
# Phase 3A: Builder — TaskQueue（タスク管理）
# ============================================================================

class TaskStatus(str, Enum):
    PENDING    = "pending"
    IN_PROGRESS = "in_progress"
    DONE       = "done"
    BLOCKED    = "blocked"

class TaskPriority(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"

@dataclass
class BuildTask:
    task_id: str
    title: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    estimated_hours: float = 0.0
    requires_escalation: bool = False
    escalation_reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    def complete(self):
        self.status = TaskStatus.DONE
        self.completed_at = datetime.now().isoformat()

    def block(self, reason: str):
        self.status = TaskStatus.BLOCKED
        self.requires_escalation = True
        self.escalation_reason = reason


class TaskQueue:
    """Builder のタスクキュー"""

    PAID_SAAS_KEYWORDS = ["stripe", "twilio", "sendgrid", "有料api", "有料saas", "課金"]
    PERSONAL_DATA_KEYWORDS = ["個人情報", "メール収集", "氏名取得", "住所", "認証情報"]

    def __init__(self):
        self.tasks: List[BuildTask] = []

    def add(self, title: str, priority: TaskPriority,
            estimated_hours: float = 1.0) -> BuildTask:
        task = BuildTask(
            task_id=f"TASK-{uuid.uuid4().hex[:6].upper()}",
            title=title,
            priority=priority,
            estimated_hours=estimated_hours,
        )
        # 自動エスカレーション判定
        lower = title.lower()
        for kw in self.PAID_SAAS_KEYWORDS:
            if kw in lower:
                task.block(f"有料 SaaS 導入の可能性: '{kw}'")
                break
        for kw in self.PERSONAL_DATA_KEYWORDS:
            if kw in lower:
                task.block(f"個人情報取扱い: '{kw}'")
                break
        self.tasks.append(task)
        return task

    def get_by_status(self, status: TaskStatus) -> List[BuildTask]:
        return [t for t in self.tasks if t.status == status]

    def get_by_priority(self, priority: TaskPriority) -> List[BuildTask]:
        return [t for t in self.tasks if t.priority == priority]

    def sprint_summary(self) -> Dict:
        total = len(self.tasks)
        done  = sum(1 for t in self.tasks if t.status == TaskStatus.DONE)
        blocked = sum(1 for t in self.tasks if t.status == TaskStatus.BLOCKED)
        hours_remaining = sum(
            t.estimated_hours for t in self.tasks
            if t.status not in (TaskStatus.DONE,)
        )
        return {
            "total": total,
            "done": done,
            "blocked": blocked,
            "pending_hours": round(hours_remaining, 1),
            "completion_rate": round(done / total * 100, 1) if total else 0.0,
        }


# ============================================================================
# Phase 3A: Builder — ReleaseChecker（リリース前チェック）
# ============================================================================

@dataclass
class CheckItem:
    name: str
    passed: bool
    detail: str
    blocking: bool = True  # False = 警告のみ


class ReleaseChecker:
    """リリース前チェックリスト"""

    def __init__(self, feature_name: str):
        self.feature_name = feature_name
        self.checks: List[CheckItem] = []

    def check_security(self, has_auth: bool, has_input_validation: bool,
                       has_rate_limit: bool) -> "ReleaseChecker":
        self.checks.append(CheckItem(
            "認証実装",
            has_auth,
            "認証あり" if has_auth else "認証なし — ブロッカー",
        ))
        self.checks.append(CheckItem(
            "入力バリデーション",
            has_input_validation,
            "実装済み" if has_input_validation else "未実装 — XSS/SQLi リスク",
        ))
        self.checks.append(CheckItem(
            "レートリミット",
            has_rate_limit,
            "設定済み" if has_rate_limit else "未設定",
            blocking=False,
        ))
        return self

    def check_compliance(self, handles_personal_data: bool,
                         compliance_gate_done: bool) -> "ReleaseChecker":
        if handles_personal_data:
            self.checks.append(CheckItem(
                "Compliance Gate",
                compliance_gate_done,
                "完了" if compliance_gate_done else "個人情報処理あり — Compliance Gate 未実施",
            ))
        return self

    def check_tests(self, test_coverage_pct: float,
                    min_coverage: float = 80.0) -> "ReleaseChecker":
        passed = test_coverage_pct >= min_coverage
        self.checks.append(CheckItem(
            "テストカバレッジ",
            passed,
            f"{test_coverage_pct:.0f}% (基準 {min_coverage:.0f}%)",
        ))
        return self

    def is_release_ready(self) -> Tuple[bool, List[str]]:
        blockers = [c.detail for c in self.checks if c.blocking and not c.passed]
        return len(blockers) == 0, blockers

    def summary(self) -> Dict:
        ready, blockers = self.is_release_ready()
        return {
            "feature": self.feature_name,
            "release_ready": ready,
            "total_checks": len(self.checks),
            "passed": sum(1 for c in self.checks if c.passed),
            "blockers": blockers,
        }


# ============================================================================
# Phase 3B: Operator — SNSScheduler（SNS 投稿管理）
# ============================================================================

class PostStatus(str, Enum):
    DRAFT    = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"

@dataclass
class SNSPost:
    post_id: str
    content: str
    platform: str          # twitter / instagram / line
    scheduled_at: str
    status: PostStatus = PostStatus.DRAFT
    controversy_risk: bool = False
    risk_reason: str = ""
    requires_strategist: bool = False

    def approve(self):
        if not self.controversy_risk:
            self.status = PostStatus.APPROVED

    def reject(self, reason: str):
        self.status = PostStatus.REJECTED
        self.risk_reason = reason


CONTROVERSY_KEYWORDS = [
    "炎上", "批判", "謝罪", "問題", "差別", "政治",
    "宗教", "有料", "課金", "返金", "詐欺",
]
PAID_AD_KEYWORDS = ["広告", "スポンサー", "PR", "インフルエンサー"]


class SNSScheduler:
    """Operator の SNS 投稿スケジューラー"""

    def __init__(self):
        self.posts: List[SNSPost] = []

    def create_post(self, content: str, platform: str,
                    scheduled_at: str) -> SNSPost:
        post = SNSPost(
            post_id=f"POST-{uuid.uuid4().hex[:6].upper()}",
            content=content,
            platform=platform,
            scheduled_at=scheduled_at,
        )
        # 炎上リスク判定
        for kw in CONTROVERSY_KEYWORDS:
            if kw in content:
                post.controversy_risk = True
                post.risk_reason = f"炎上リスクキーワード: '{kw}'"
                post.requires_strategist = True
                break
        # 有償広告判定
        for kw in PAID_AD_KEYWORDS:
            if kw in content:
                post.controversy_risk = True
                post.risk_reason = f"有償広告の可能性: '{kw}'"
                post.requires_strategist = True
                break
        self.posts.append(post)
        return post

    def get_approved(self) -> List[SNSPost]:
        return [p for p in self.posts if p.status == PostStatus.APPROVED]

    def weekly_stats(self) -> Dict:
        total     = len(self.posts)
        approved  = sum(1 for p in self.posts if p.status == PostStatus.APPROVED)
        risky     = sum(1 for p in self.posts if p.controversy_risk)
        escalated = sum(1 for p in self.posts if p.requires_strategist)
        return {
            "total": total,
            "approved": approved,
            "risky": risky,
            "escalated_to_strategist": escalated,
        }


# ============================================================================
# Phase 3B: Operator — KPITracker（KPI 監視）
# ============================================================================

@dataclass
class DailyMetrics:
    date: str
    dau: int        # Daily Active Users
    new_users: int
    sessions: int
    revenue_jpy: float


class KPITracker:
    """Operator の KPI 監視"""

    DAU_DROP_ALERT_THRESHOLD = 0.20   # 20% 以上の DAU 落下でアラート

    def __init__(self):
        self.metrics: List[DailyMetrics] = []
        self.alerts: List[str] = []

    def record(self, date: str, dau: int, new_users: int,
               sessions: int, revenue_jpy: float) -> DailyMetrics:
        m = DailyMetrics(date, dau, new_users, sessions, revenue_jpy)
        # 前日比アラート
        if len(self.metrics) > 0:
            prev_dau = self.metrics[-1].dau
            if prev_dau > 0:
                drop_rate = (prev_dau - dau) / prev_dau
                if drop_rate >= self.DAU_DROP_ALERT_THRESHOLD:
                    alert = (f"⚠️ DAU 急落: {prev_dau} → {dau} "
                             f"({drop_rate * 100:.1f}% 減) [{date}]")
                    self.alerts.append(alert)
        self.metrics.append(m)
        return m

    def mau(self) -> int:
        """直近 30 日の累積ユニークユーザー（簡易: 新規ユーザー合計）"""
        recent = self.metrics[-30:]
        return sum(m.new_users for m in recent)

    def avg_dau(self) -> float:
        if not self.metrics:
            return 0.0
        return round(sum(m.dau for m in self.metrics) / len(self.metrics), 1)

    def retention_rate(self) -> float:
        """DAU / MAU × 100 (%)"""
        mau = self.mau()
        if mau == 0:
            return 0.0
        avg = self.avg_dau()
        return round(min(100.0, avg / mau * 100), 1)

    def total_revenue(self) -> float:
        return sum(m.revenue_jpy for m in self.metrics)

    def summary(self) -> Dict:
        return {
            "days_tracked": len(self.metrics),
            "avg_dau": self.avg_dau(),
            "mau": self.mau(),
            "retention_rate_pct": self.retention_rate(),
            "total_revenue_jpy": round(self.total_revenue()),
            "active_alerts": len(self.alerts),
        }


# ============================================================================
# Phase 3B: Operator — FinancialReport（月次財務レポート）
# ============================================================================

@dataclass
class CostEntry:
    category: str
    amount_jpy: float
    description: str


class FinancialReport:
    """月次財務レポート"""

    def __init__(self, month: str, budget_jpy: float):
        self.month = month
        self.budget_jpy = budget_jpy
        self.revenue_jpy: float = 0.0
        self.costs: List[CostEntry] = []

    def add_revenue(self, amount_jpy: float):
        self.revenue_jpy += amount_jpy

    def add_cost(self, category: str, amount_jpy: float, description: str = ""):
        self.costs.append(CostEntry(category, amount_jpy, description))

    def total_costs(self) -> float:
        return sum(c.amount_jpy for c in self.costs)

    def cashflow(self) -> float:
        return self.revenue_jpy - self.total_costs()

    def budget_utilization_pct(self) -> float:
        if self.budget_jpy == 0:
            return 0.0
        return round(self.total_costs() / self.budget_jpy * 100, 1)

    def is_over_budget(self) -> bool:
        return self.total_costs() > self.budget_jpy

    def generate(self) -> Dict:
        return {
            "report_id":            f"FIN-{self.month}-{uuid.uuid4().hex[:4].upper()}",
            "month":                self.month,
            "revenue_jpy":          round(self.revenue_jpy),
            "total_costs_jpy":      round(self.total_costs()),
            "cashflow_jpy":         round(self.cashflow()),
            "budget_jpy":           self.budget_jpy,
            "budget_utilization":   self.budget_utilization_pct(),
            "over_budget":          self.is_over_budget(),
            "cost_breakdown":       [asdict(c) for c in self.costs],
            "generated_at":         datetime.now().isoformat(),
        }


# ============================================================================
# Phase 3C: AgentCoordinator（エージェント間連携）
# ============================================================================

class EscalationLevel(str, Enum):
    A_HARD_STOP    = "A_HARD_STOP"     # ユーザー確認必須
    B_LIGHT        = "B_LIGHT"          # 簡易承認
    C_AUTO         = "C_AUTO"           # 自動判定

@dataclass
class AgentMessage:
    message_id: str
    from_agent: str
    to_agent: str
    subject: str
    body: str
    escalation_level: EscalationLevel
    requires_user: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AgentCoordinator:
    """Builder ↔ Operator ↔ Strategist 間の連携ハブ"""

    MONEY_KEYWORDS    = ["有料", "課金", "月額", "広告費", "stripe", "購入"]
    LEGAL_KEYWORDS    = ["個人情報", "プライバシー", "利用規約", "法務", "弁護士"]
    COMPLAINT_KEYWORDS = ["クレーム", "苦情", "返金", "炎上", "誤動作", "バグ報告"]

    def __init__(self):
        self.messages: List[AgentMessage] = []
        self.escalations: List[AgentMessage] = []

    def send(self, from_agent: str, to_agent: str,
             subject: str, body: str) -> AgentMessage:
        level = self._judge_level(subject + " " + body)
        requires_user = level == EscalationLevel.A_HARD_STOP

        msg = AgentMessage(
            message_id=f"MSG-{uuid.uuid4().hex[:6].upper()}",
            from_agent=from_agent,
            to_agent=to_agent,
            subject=subject,
            body=body,
            escalation_level=level,
            requires_user=requires_user,
        )
        self.messages.append(msg)
        if requires_user:
            self.escalations.append(msg)
        return msg

    def _judge_level(self, text: str) -> EscalationLevel:
        lower = text.lower()
        for kw in self.MONEY_KEYWORDS + self.LEGAL_KEYWORDS + self.COMPLAINT_KEYWORDS:
            if kw in lower:
                return EscalationLevel.A_HARD_STOP
        # 技術的な調整は簡易承認
        if any(kw in lower for kw in ["デプロイ", "リリース", "公開"]):
            return EscalationLevel.B_LIGHT
        return EscalationLevel.C_AUTO

    def pending_user_approvals(self) -> List[AgentMessage]:
        return [m for m in self.escalations if m.requires_user]

    def coordinator_stats(self) -> Dict:
        return {
            "total_messages":   len(self.messages),
            "escalations_a":    sum(1 for m in self.messages
                                    if m.escalation_level == EscalationLevel.A_HARD_STOP),
            "escalations_b":    sum(1 for m in self.messages
                                    if m.escalation_level == EscalationLevel.B_LIGHT),
            "auto_decided":     sum(1 for m in self.messages
                                    if m.escalation_level == EscalationLevel.C_AUTO),
            "pending_user":     len(self.pending_user_approvals()),
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
            print(f"  ❌ {name}" + (f": {detail}" if detail else ""))
            failed += 1
            errors.append(name)

    print("=" * 80)
    print("🚀 Phase 3 統合テスト実行")
    print("=" * 80)

    # ------------------------------------------------------------------
    # テスト 1-5: TaskQueue（Builder タスク管理）
    # ------------------------------------------------------------------
    print("\n📋 テスト 1-5: TaskQueue（Builder タスク管理）")
    queue = TaskQueue()

    t1 = queue.add("ログイン画面 UI 実装", TaskPriority.HIGH, 4.0)
    t2 = queue.add("音声 TTS 統合", TaskPriority.MEDIUM, 6.0)
    t3 = queue.add("Stripe 決済導入", TaskPriority.HIGH, 8.0)        # 有料SaaS → blocked
    t4 = queue.add("個人情報収集フォーム追加", TaskPriority.LOW, 3.0)  # 個人情報 → blocked
    t1.complete()

    check("テスト 1: タスク追加 4 件", len(queue.tasks) == 4)
    check("テスト 2: 有料 SaaS タスクが自動 BLOCKED",
          t3.status == TaskStatus.BLOCKED and t3.requires_escalation,
          f"status={t3.status}")
    check("テスト 3: 個人情報タスクが自動 BLOCKED",
          t4.status == TaskStatus.BLOCKED,
          f"status={t4.status}")
    check("テスト 4: 完了タスクを取得",
          len(queue.get_by_status(TaskStatus.DONE)) == 1)

    summary = queue.sprint_summary()
    check("テスト 5: スプリント統計 (done=1, blocked=2)",
          summary["done"] == 1 and summary["blocked"] == 2,
          f"got {summary}")

    # ------------------------------------------------------------------
    # テスト 6-10: ReleaseChecker（リリース前チェック）
    # ------------------------------------------------------------------
    print("\n📋 テスト 6-10: ReleaseChecker（リリース前チェック）")

    # 通過ケース
    rc_ok = (
        ReleaseChecker("英会話チャット画面 v1")
        .check_security(has_auth=True, has_input_validation=True, has_rate_limit=True)
        .check_compliance(handles_personal_data=False, compliance_gate_done=False)
        .check_tests(test_coverage_pct=85.0)
    )
    ready, blockers = rc_ok.is_release_ready()
    check("テスト 6: セキュリティ完備でリリース OK", ready, f"blockers={blockers}")
    check("テスト 7: ブロッカー 0 件", len(blockers) == 0)

    # 失敗ケース（認証なし）
    rc_fail = (
        ReleaseChecker("未認証 API エンドポイント")
        .check_security(has_auth=False, has_input_validation=True, has_rate_limit=False)
        .check_tests(test_coverage_pct=60.0)
    )
    ready_fail, blockers_fail = rc_fail.is_release_ready()
    check("テスト 8: 認証なし・カバレッジ不足でリリース NG", not ready_fail)
    check("テスト 9: ブロッカー 2 件以上", len(blockers_fail) >= 2,
          f"got {len(blockers_fail)}: {blockers_fail}")

    # Compliance Gate 未実施
    rc_compliance = (
        ReleaseChecker("ユーザー登録フォーム")
        .check_security(has_auth=True, has_input_validation=True, has_rate_limit=True)
        .check_compliance(handles_personal_data=True, compliance_gate_done=False)
        .check_tests(test_coverage_pct=90.0)
    )
    ready_c, blockers_c = rc_compliance.is_release_ready()
    check("テスト 10: 個人情報 + Compliance Gate 未実施でリリース NG",
          not ready_c, f"blockers={blockers_c}")

    # ------------------------------------------------------------------
    # テスト 11-15: SNSScheduler（Operator SNS 管理）
    # ------------------------------------------------------------------
    print("\n📋 テスト 11-15: SNSScheduler（Operator SNS 管理）")
    scheduler = SNSScheduler()

    p1 = scheduler.create_post(
        "🎉 英会話アプリがついにリリース！無料でお試しください",
        "twitter", "2026-05-11T09:00:00"
    )
    p2 = scheduler.create_post(
        "本日のサービス障害について謝罪いたします",  # 炎上リスク
        "twitter", "2026-05-11T10:00:00"
    )
    p3 = scheduler.create_post(
        "インフルエンサーとのタイアップ広告を開始します",  # 有償広告
        "instagram", "2026-05-12T12:00:00"
    )
    p1.approve()

    check("テスト 11: 通常投稿が承認される", p1.status == PostStatus.APPROVED)
    check("テスト 12: 謝罪投稿が炎上リスク検出",
          p2.controversy_risk and p2.requires_strategist,
          f"risk={p2.risk_reason}")
    check("テスト 13: 広告投稿が Strategist エスカレーション",
          p3.requires_strategist, f"risk={p3.risk_reason}")

    stats = scheduler.weekly_stats()
    check("テスト 14: 週次統計 (approved=1, escalated=2)",
          stats["approved"] == 1 and stats["escalated_to_strategist"] == 2,
          f"got {stats}")
    check("テスト 15: JSON シリアライズ可能", bool(json.dumps(stats)))

    # ------------------------------------------------------------------
    # テスト 16-20: KPITracker（KPI 監視）
    # ------------------------------------------------------------------
    print("\n📋 テスト 16-20: KPITracker（KPI 監視）")
    kpi = KPITracker()
    kpi.record("2026-05-01", dau=100, new_users=30, sessions=250, revenue_jpy=15000)
    kpi.record("2026-05-02", dau=110, new_users=25, sessions=280, revenue_jpy=18000)
    kpi.record("2026-05-03", dau=85,  new_users=20, sessions=200, revenue_jpy=12000)   # DAU 急落

    check("テスト 16: 3 日分記録",
          len(kpi.metrics) == 3)
    check("テスト 17: 平均 DAU 計算",
          kpi.avg_dau() == round((100 + 110 + 85) / 3, 1),
          f"got {kpi.avg_dau()}")
    check("テスト 18: MAU (新規ユーザー合計)",
          kpi.mau() == 75, f"got {kpi.mau()}")
    check("テスト 19: DAU 急落アラート発生",
          len(kpi.alerts) >= 1, f"alerts={kpi.alerts}")

    kpi_summary = kpi.summary()
    check("テスト 20: 総収益 = 45,000 円",
          kpi_summary["total_revenue_jpy"] == 45000,
          f"got {kpi_summary['total_revenue_jpy']}")

    # ------------------------------------------------------------------
    # テスト 21-25: FinancialReport（月次財務レポート）
    # ------------------------------------------------------------------
    print("\n📋 テスト 21-25: FinancialReport（月次財務レポート）")
    fin = FinancialReport(month="2026-05", budget_jpy=3000)
    fin.add_revenue(45000)
    fin.add_cost("API",    800,  "Claude API 利用料")
    fin.add_cost("hosting", 200, "Vercel Hobby プラン")
    fin.add_cost("tools",  500,  "各種ツール")

    check("テスト 21: 総収益 45,000 円", fin.revenue_jpy == 45000)
    check("テスト 22: 総コスト 1,500 円", fin.total_costs() == 1500,
          f"got {fin.total_costs()}")
    check("テスト 23: キャッシュフロー 43,500 円",
          fin.cashflow() == 43500, f"got {fin.cashflow()}")
    check("テスト 24: 予算消化率 50%",
          fin.budget_utilization_pct() == 50.0,
          f"got {fin.budget_utilization_pct()}")

    report = fin.generate()
    check("テスト 25: 月次レポート JSON 生成 + 予算超過なし",
          "report_id" in report and not report["over_budget"])

    # ------------------------------------------------------------------
    # テスト 26-30: AgentCoordinator（エージェント間連携）
    # ------------------------------------------------------------------
    print("\n📋 テスト 26-30: AgentCoordinator（エージェント間連携）")
    coord = AgentCoordinator()

    # Builder → Strategist: 有料 SaaS 相談（→ 階層 A）
    msg1 = coord.send(
        "Builder", "Strategist",
        "Stripe 導入の検討",
        "決済機能で Stripe 有料プランを使用したい。月額費用が発生する。",
    )
    # Operator → Strategist: クレーム報告（→ 階層 A）
    msg2 = coord.send(
        "Operator", "Strategist",
        "ユーザーからクレームあり",
        "アプリの音声機能にバグ報告があり、クレームとして受領した。",
    )
    # Builder → Operator: リリース通知（→ 階層 B）
    msg3 = coord.send(
        "Builder", "Operator",
        "v1.0 デプロイ完了",
        "英会話チャット画面の本番デプロイが完了しました。プロモーション開始可能です。",
    )
    # Operator → Builder: 軽微な修正依頼（→ 階層 C）
    msg4 = coord.send(
        "Operator", "Builder",
        "ボタンの文言変更依頼",
        "「送信」ボタンを「話しかける」に変更してください。",
    )

    check("テスト 26: 有料 SaaS 相談が 階層 A",
          msg1.escalation_level == EscalationLevel.A_HARD_STOP and msg1.requires_user)
    check("テスト 27: クレームが 階層 A",
          msg2.escalation_level == EscalationLevel.A_HARD_STOP)
    check("テスト 28: リリース通知が 階層 B",
          msg3.escalation_level == EscalationLevel.B_LIGHT,
          f"got {msg3.escalation_level}")
    check("テスト 29: 軽微依頼が 階層 C (自動判定)",
          msg4.escalation_level == EscalationLevel.C_AUTO,
          f"got {msg4.escalation_level}")

    stats_coord = coord.coordinator_stats()
    check("テスト 30: コーディネーター統計 (A=2, B=1, C=1, pending=2)",
          stats_coord["escalations_a"] == 2
          and stats_coord["escalations_b"] == 1
          and stats_coord["auto_decided"] == 1
          and stats_coord["pending_user"] == 2,
          f"got {stats_coord}")

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
        print("🎉 Phase 3 完全実装完了！すべてのテストに PASS しました。")
        print()
        print("次ステップ: Phase 4 - Claude API 統合（実際の LLM 呼び出し）")
    else:
        print()
        print(f"⚠️  {failed} 件のテストが失敗しました。")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    run_tests()
