#!/usr/bin/env python3
"""
Phase 8 自動実行スクリプト
ベータテスト・改善サイクル — AI 組織自体のドッグフーディング
単一ファイル、依存性ゼロで実行可能

実装内容:
  - AgentDecisionLog          : 各エージェント判定の記録（モデル・コスト・結果）
  - EscalationAccuracyChecker : 階層 A/B/C 判定の正解率（人間オーバーライドで測定）
  - BudgetAccuracyMonitor     : 予測コスト vs 実コストの誤差追跡
  - IncidentReporter          : 予算超過・誤判定・モデル誤用などのインシデント記録
  - PromptTuningSuggester     : オーバーライド/インシデント → プロンプト改善提案
  - IterationPlanner          : 改善反復管理（閾値・プロンプト・モデル配分の更新）
"""

import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# ============================================================================
# 共通定数（既存 Phase との整合）
# ============================================================================

VALID_AGENTS         = ("strategist", "builder", "operator")
VALID_MODELS         = ("haiku", "sonnet")          # opus は禁止
ESCALATION_LEVELS    = ("A_HARD_STOP", "B_LIGHT", "C_AUTO")
INCIDENT_SEVERITIES  = ("P0", "P1", "P2", "P3")


# ============================================================================
# Phase 8A: AgentDecisionLog
# ============================================================================

@dataclass
class DecisionRecord:
    decision_id: str
    agent:       str          # strategist / builder / operator
    task_type:   str          # 例: "RAR-S 検証", "ライブラリ選定"
    model_used:  str          # haiku / sonnet
    cost_jpy:    float        # 実コスト（円）
    duration_ms: int          # 所要時間
    escalation_level: str     # 判定された階層 A/B/C
    context_summary: str      # 判定根拠の要約
    timestamp:   str = field(default_factory=lambda: datetime.now().isoformat())


class AgentDecisionLog:
    """エージェント判定の永続記録 — 全ての分析の元データ"""

    def __init__(self):
        self.records: List[DecisionRecord] = []

    def log(self, agent: str, task_type: str, model_used: str,
            cost_jpy: float, escalation_level: str = "C_AUTO",
            duration_ms: int = 0, context_summary: str = "") -> DecisionRecord:
        if agent not in VALID_AGENTS:
            raise ValueError(f"Invalid agent: {agent}")
        if model_used not in VALID_MODELS:
            raise ValueError(f"Invalid model (opus は禁止): {model_used}")
        if escalation_level not in ESCALATION_LEVELS:
            raise ValueError(f"Invalid escalation: {escalation_level}")

        rec = DecisionRecord(
            decision_id=f"DEC-{uuid.uuid4().hex[:6].upper()}",
            agent=agent, task_type=task_type, model_used=model_used,
            cost_jpy=round(float(cost_jpy), 3),
            duration_ms=int(duration_ms),
            escalation_level=escalation_level,
            context_summary=context_summary,
        )
        self.records.append(rec)
        return rec

    def by_agent(self, agent: str) -> List[DecisionRecord]:
        return [r for r in self.records if r.agent == agent]

    def by_model(self, model: str) -> List[DecisionRecord]:
        return [r for r in self.records if r.model_used == model]

    def total_cost_jpy(self, agent: Optional[str] = None) -> float:
        items = self.by_agent(agent) if agent else self.records
        return round(sum(r.cost_jpy for r in items), 3)

    def model_distribution(self) -> Dict[str, Dict]:
        """Haiku/Sonnet の使用比率と消費額（v2.0 配分目標との比較用）"""
        out: Dict[str, Dict] = {}
        total_cost = self.total_cost_jpy() or 1.0
        for m in VALID_MODELS:
            items = self.by_model(m)
            cost = sum(r.cost_jpy for r in items)
            out[m] = {
                "calls":      len(items),
                "cost_jpy":   round(cost, 3),
                "share_pct":  round(cost / total_cost * 100, 1),
            }
        return out


# ============================================================================
# Phase 8B: EscalationAccuracyChecker
# ============================================================================

@dataclass
class OverrideRecord:
    decision_id:    str
    agent:          str
    original_level: str       # エージェントの判定
    corrected_level: str      # 人間が修正した階層
    reason:         str
    timestamp:      str = field(default_factory=lambda: datetime.now().isoformat())


class EscalationAccuracyChecker:
    """
    人間オーバーライドを記録し、エージェント判定の正解率を計測。
    過剰エスカレーション (例: Cで済むのを A 扱い) と
    過小エスカレーション (例: A なのに C 扱い = 危険) を区別する。
    """

    LEVEL_RANK = {"A_HARD_STOP": 3, "B_LIGHT": 2, "C_AUTO": 1}

    def __init__(self, log: AgentDecisionLog):
        self.log = log
        self.overrides: List[OverrideRecord] = []

    def record_override(self, decision_id: str, corrected_level: str,
                        reason: str = "") -> Optional[OverrideRecord]:
        if corrected_level not in ESCALATION_LEVELS:
            return None
        rec = next((r for r in self.log.records
                    if r.decision_id == decision_id), None)
        if not rec:
            return None
        ovr = OverrideRecord(
            decision_id=decision_id, agent=rec.agent,
            original_level=rec.escalation_level,
            corrected_level=corrected_level, reason=reason,
        )
        self.overrides.append(ovr)
        return ovr

    def accuracy(self, agent: Optional[str] = None) -> Dict:
        """
        正解率 = (オーバーライドされていない判定) / (全判定)
        """
        decisions = self.log.by_agent(agent) if agent else self.log.records
        decision_ids = {r.decision_id for r in decisions}
        total = len(decisions)
        overridden_ids = {o.decision_id for o in self.overrides
                          if o.decision_id in decision_ids}
        correct = total - len(overridden_ids)

        over   = sum(1 for o in self.overrides
                     if o.decision_id in decision_ids
                     and self.LEVEL_RANK[o.original_level]
                     >  self.LEVEL_RANK[o.corrected_level])
        under  = sum(1 for o in self.overrides
                     if o.decision_id in decision_ids
                     and self.LEVEL_RANK[o.original_level]
                     <  self.LEVEL_RANK[o.corrected_level])

        return {
            "agent":          agent or "all",
            "total":          total,
            "correct":        correct,
            "overridden":     len(overridden_ids),
            "over_escalated":  over,    # 過剰 (A→C など)
            "under_escalated": under,   # 過小 (C→A など。本番で危険)
            "accuracy_pct":   round(correct / total * 100, 1) if total else 0.0,
        }

    def worst_agent(self) -> Optional[str]:
        """
        最も誤判定が多いエージェントを返す（プロンプト改善対象）。
        accuracy が同点の場合は under_escalated（=本番で危険）が多い方を優先。
        """
        scored = []
        for a in VALID_AGENTS:
            stats = self.accuracy(a)
            if stats["total"] == 0:
                continue
            scored.append((a, stats["accuracy_pct"], stats["under_escalated"]))
        if not scored:
            return None
        # accuracy 昇順（低いほど悪い）→ under 降順（多いほど危険）
        scored.sort(key=lambda x: (x[1], -x[2]))
        return scored[0][0]


# ============================================================================
# Phase 8C: BudgetAccuracyMonitor
# ============================================================================

@dataclass
class CostEstimate:
    decision_id:   str
    predicted_jpy: float
    actual_jpy:    float
    error_pct:     float
    timestamp:     str = field(default_factory=lambda: datetime.now().isoformat())


class BudgetAccuracyMonitor:
    """予測コスト vs 実コストの誤差を追跡 — モデル選択戦略の妥当性検証"""

    def __init__(self, log: AgentDecisionLog):
        self.log = log
        self.estimates: List[CostEstimate] = []

    def record(self, decision_id: str, predicted_jpy: float) -> Optional[CostEstimate]:
        rec = next((r for r in self.log.records
                    if r.decision_id == decision_id), None)
        if not rec:
            return None
        actual = rec.cost_jpy
        # ゼロ除算対策
        denom  = max(predicted_jpy, 0.001)
        err    = round((actual - predicted_jpy) / denom * 100, 2)
        est    = CostEstimate(
            decision_id=decision_id,
            predicted_jpy=round(predicted_jpy, 3),
            actual_jpy=actual,
            error_pct=err,
        )
        self.estimates.append(est)
        return est

    def mape(self) -> float:
        """Mean Absolute Percentage Error"""
        if not self.estimates:
            return 0.0
        return round(sum(abs(e.error_pct) for e in self.estimates)
                     / len(self.estimates), 2)

    def systematic_bias(self) -> str:
        """系統誤差の方向（過小見積もりか過大見積もりか）"""
        if not self.estimates:
            return "no_data"
        avg = sum(e.error_pct for e in self.estimates) / len(self.estimates)
        if   avg > 10:  return "underestimate"   # 実コストが予測より高い
        elif avg < -10: return "overestimate"
        else:           return "balanced"

    def over_budget_decisions(self, threshold_pct: float = 30.0) -> List[CostEstimate]:
        """予測の N% 以上超過した判定を返す"""
        return [e for e in self.estimates if e.error_pct > threshold_pct]


# ============================================================================
# Phase 8D: IncidentReporter
# ============================================================================

INCIDENT_TYPES = (
    "budget_overrun",      # 月予算超過 / 80% 超過アラート
    "wrong_escalation",    # 階層誤判定で人間介入が必要になった
    "model_misuse",        # クリティカル判定なのに Haiku を使った 等
    "api_error",           # Anthropic API エラー / レート制限
    "decision_timeout",    # 判定が想定時間を大幅超過
)


@dataclass
class Incident:
    incident_id: str
    incident_type: str
    severity:    str          # P0–P3
    related_decision_id: str
    description: str
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved:    bool = False
    resolution:  str  = ""


class IncidentReporter:
    """運用インシデント記録 — Phase 8 改善サイクルへの入力"""

    def __init__(self):
        self.incidents: Dict[str, Incident] = {}

    def report(self, incident_type: str, severity: str,
               description: str,
               related_decision_id: str = "") -> Incident:
        if incident_type not in INCIDENT_TYPES:
            incident_type = "wrong_escalation"
        if severity not in INCIDENT_SEVERITIES:
            severity = "P2"
        iid = f"INC-{uuid.uuid4().hex[:6].upper()}"
        inc = Incident(
            incident_id=iid, incident_type=incident_type,
            severity=severity, related_decision_id=related_decision_id,
            description=description,
        )
        self.incidents[iid] = inc
        return inc

    def resolve(self, incident_id: str, resolution: str) -> bool:
        inc = self.incidents.get(incident_id)
        if not inc:
            return False
        inc.resolved = True
        inc.resolution = resolution
        return True

    def open_incidents(self) -> List[Incident]:
        return [i for i in self.incidents.values() if not i.resolved]

    def by_type(self) -> Dict[str, int]:
        c = {t: 0 for t in INCIDENT_TYPES}
        for i in self.incidents.values():
            c[i.incident_type] = c.get(i.incident_type, 0) + 1
        return c

    def critical_count(self) -> int:
        return sum(1 for i in self.incidents.values()
                   if i.severity in ("P0", "P1") and not i.resolved)


# ============================================================================
# Phase 8E: PromptTuningSuggester
# ============================================================================

@dataclass
class TuningSuggestion:
    suggestion_id: str
    target_agent:  str          # strategist / builder / operator / "all"
    target_kind:   str          # "prompt" / "threshold" / "model_mix"
    priority:      str          # P0–P3
    evidence_count: int
    description:   str
    proposed_change: str


class PromptTuningSuggester:
    """
    オーバーライド・インシデント・コスト誤差を分析し、
    どのエージェントの何を直すべきかを具体提案として出力。
    """

    def __init__(self, accuracy: EscalationAccuracyChecker,
                 budget: BudgetAccuracyMonitor,
                 incidents: IncidentReporter):
        self.accuracy  = accuracy
        self.budget    = budget
        self.incidents = incidents

    def generate(self) -> List[TuningSuggestion]:
        suggestions: List[TuningSuggestion] = []

        # 1. 過小エスカレーション (P0 — 本番で危険)
        for agent in VALID_AGENTS:
            stats = self.accuracy.accuracy(agent)
            if stats["under_escalated"] >= 1:
                suggestions.append(TuningSuggestion(
                    suggestion_id=f"TUN-{uuid.uuid4().hex[:6].upper()}",
                    target_agent=agent, target_kind="prompt", priority="P0",
                    evidence_count=stats["under_escalated"],
                    description=(
                        f"{agent} が階層を過小判定 ({stats['under_escalated']}件) "
                        "— 本番で重大インシデントに直結"
                    ),
                    proposed_change=(
                        f"{agent} のシステムプロンプトに「金銭・法務・命に関わる"
                        "判定は必ず A_HARD_STOP に上げる」例示を追加"
                    ),
                ))

        # 2. 過剰エスカレーション (P2 — UX/コスト悪化だが安全)
        for agent in VALID_AGENTS:
            stats = self.accuracy.accuracy(agent)
            if stats["over_escalated"] >= 2:
                suggestions.append(TuningSuggestion(
                    suggestion_id=f"TUN-{uuid.uuid4().hex[:6].upper()}",
                    target_agent=agent, target_kind="threshold", priority="P2",
                    evidence_count=stats["over_escalated"],
                    description=(
                        f"{agent} が過剰エスカレーション ({stats['over_escalated']}件)"
                        " — 人間の判断負荷増・運用コスト増"
                    ),
                    proposed_change=(
                        f"DelegationThreshold で {agent} 由来の B_LIGHT 基準を"
                        "緩和、C_AUTO 範囲を拡大"
                    ),
                ))

        # 3. コスト見積もりの系統誤差
        bias = self.budget.systematic_bias()
        if bias == "underestimate":
            suggestions.append(TuningSuggestion(
                suggestion_id=f"TUN-{uuid.uuid4().hex[:6].upper()}",
                target_agent="all", target_kind="model_mix", priority="P1",
                evidence_count=len(self.budget.estimates),
                description=(
                    f"コスト系統的に過小見積もり (MAPE={self.budget.mape()}%) "
                    "— 月次 3,000 円予算を超過するリスク"
                ),
                proposed_change=(
                    "ModelSelector で Sonnet 強制条件を絞り、Haiku 比率を 60→70% に"
                ),
            ))

        # 4. P0/P1 未解決インシデント
        crit = self.incidents.critical_count()
        if crit > 0:
            suggestions.append(TuningSuggestion(
                suggestion_id=f"TUN-{uuid.uuid4().hex[:6].upper()}",
                target_agent="all", target_kind="prompt", priority="P0",
                evidence_count=crit,
                description=f"未解決の P0/P1 インシデント {crit} 件",
                proposed_change="該当インシデントの根本原因を特定し、関連エージェントの判定ロジックを修正",
            ))

        # 優先度順にソート
        order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        suggestions.sort(key=lambda s: (order.get(s.priority, 9),
                                        -s.evidence_count))
        return suggestions


# ============================================================================
# Phase 8F: IterationPlanner
# ============================================================================

@dataclass
class Iteration:
    iter_id:    str
    name:       str
    target_changes: List[str]            # 例: ["strategist プロンプト v2", "Haiku 70%"]
    suggestion_ids: List[str]
    started_at: str
    ended_at:   Optional[str] = None
    metrics_before: Dict[str, float] = field(default_factory=dict)
    metrics_after:  Dict[str, float] = field(default_factory=dict)
    status:     str = "planning"


class IterationPlanner:
    """改善反復管理 — 計画 → 実行 → 評価のサイクル"""

    def __init__(self):
        self.iterations: Dict[str, Iteration] = {}

    def plan(self, name: str, target_changes: List[str],
             suggestion_ids: Optional[List[str]] = None,
             metrics_before: Optional[Dict] = None) -> Iteration:
        iid = f"ITR-{uuid.uuid4().hex[:6].upper()}"
        it = Iteration(
            iter_id=iid, name=name, target_changes=target_changes,
            suggestion_ids=suggestion_ids or [],
            started_at=datetime.now().isoformat(),
            metrics_before=metrics_before or {},
        )
        self.iterations[iid] = it
        return it

    def activate(self, iter_id: str) -> bool:
        it = self.iterations.get(iter_id)
        if not it or it.status != "planning":
            return False
        it.status = "active"
        return True

    def evaluate(self, iter_id: str,
                 metrics_after: Dict[str, float]) -> Dict:
        it = self.iterations.get(iter_id)
        if not it:
            return {"ok": False}
        it.metrics_after = metrics_after
        it.ended_at      = datetime.now().isoformat()
        it.status        = "done"

        deltas: Dict[str, float] = {}
        for k, after in metrics_after.items():
            before = it.metrics_before.get(k, 0.0)
            deltas[k] = round(after - before, 2)

        # 主要 KPI が改善したかを判定
        # accuracy_pct は上昇が良い、mape は下降が良い、incidents は下降が良い
        improved = (
            deltas.get("accuracy_pct", 0) >= 0
            and deltas.get("mape", 0) <= 0
            and deltas.get("open_incidents", 0) <= 0
        )

        return {
            "ok": True,
            "iter_id": iter_id,
            "metrics_delta": deltas,
            "improved": improved,
        }

    def stats(self) -> Dict:
        by_status: Dict[str, int] = {}
        for it in self.iterations.values():
            by_status[it.status] = by_status.get(it.status, 0) + 1
        return {"total": len(self.iterations), "by_status": by_status}


# ============================================================================
# テスト実行
# ============================================================================

def run_tests():
    passed = 0
    failed = 0
    errors: List[str] = []

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
    print("🚀 Phase 8 統合テスト実行（AI 組織自体のベータテスト・改善サイクル）")
    print("=" * 80)

    # ------------------------------------------------------------------
    # テスト 1-6: AgentDecisionLog
    # ------------------------------------------------------------------
    print("\n📋 テスト 1-6: AgentDecisionLog")

    log = AgentDecisionLog()

    d1 = log.log("strategist", "RAR-S 検証",       "sonnet", 4.2,
                 "A_HARD_STOP", duration_ms=1800,
                 context_summary="Stripe 月3,000円課金")
    d2 = log.log("strategist", "トレンド分析",      "haiku",  0.6,
                 "C_AUTO", duration_ms=600,
                 context_summary="OSS ライブラリ動向")
    d3 = log.log("builder",    "ライブラリ選定",     "haiku",  0.5,
                 "C_AUTO", context_summary="React 18 採用")
    d4 = log.log("builder",    "致命的バグ判定",     "sonnet", 3.8,
                 "A_HARD_STOP", context_summary="DB マイグレーション失敗")
    d5 = log.log("operator",   "クレーム文言判定",   "sonnet", 2.1,
                 "B_LIGHT",   context_summary="返金要求対応")
    d6 = log.log("operator",   "定型 SNS 投稿",     "haiku",  0.3,
                 "C_AUTO",    context_summary="日次告知")

    check("テスト 1: 6 件記録 + 各 decision_id が一意",
          len(log.records) == 6
          and len({r.decision_id for r in log.records}) == 6)

    check("テスト 2: by_agent('strategist') = 2 件",
          len(log.by_agent("strategist")) == 2)

    haiku_calls = log.by_model("haiku")
    check("テスト 3: Haiku 使用 = 3 件",
          len(haiku_calls) == 3, f"got {len(haiku_calls)}")

    total = log.total_cost_jpy()
    expected = 4.2 + 0.6 + 0.5 + 3.8 + 2.1 + 0.3   # 11.5
    check("テスト 4: 総コスト = 11.5 円",
          abs(total - expected) < 0.01, f"got {total}")

    # Opus 使用拒否
    raised = False
    try:
        log.log("strategist", "test", "opus", 50.0)
    except ValueError:
        raised = True
    check("テスト 5: Opus 使用は ValueError で拒否（v2.0 禁止モデル）",
          raised)

    dist = log.model_distribution()
    # Sonnet コスト 10.1, Haiku 1.4 → Sonnet 87.8%, Haiku 12.2%
    check("テスト 6: model_distribution の Sonnet share_pct ≈ 87.8%",
          abs(dist["sonnet"]["share_pct"] - 87.8) < 0.5,
          f"got {dist}")

    # ------------------------------------------------------------------
    # テスト 7-12: EscalationAccuracyChecker
    # ------------------------------------------------------------------
    print("\n📋 テスト 7-12: EscalationAccuracyChecker")

    checker = EscalationAccuracyChecker(log)

    # d3 (Builder, ライブラリ選定 → C_AUTO) を人間が「これは B_LIGHT にすべき」と修正
    o1 = checker.record_override(d3.decision_id, "B_LIGHT",
                                 "新規依存追加は軽承認すべき")
    check("テスト 7: オーバーライド記録 — under_escalated 検出",
          o1 is not None
          and checker.LEVEL_RANK[o1.original_level]
          < checker.LEVEL_RANK[o1.corrected_level])

    # d6 (Operator, 定型 SNS → C_AUTO) を人間が「BLightに上げて」=> under
    checker.record_override(d6.decision_id, "B_LIGHT",
                            "新規告知文言は事前確認が望ましい")

    # d5 (Operator, クレーム → B_LIGHT) を人間が「これは即対応」= A_HARD_STOP に上げる
    checker.record_override(d5.decision_id, "A_HARD_STOP",
                            "クレーム規模が想定以上")

    # d2 (Strategist, トレンド分析 → C_AUTO) は問題なし → オーバーライド無し
    # d4 (Builder, 致命的バグ → A_HARD_STOP) を人間が C_AUTO に下げる = over
    checker.record_override(d4.decision_id, "C_AUTO",
                            "実は再現性なく軽微")

    op_stats = checker.accuracy("operator")
    check("テスト 8: operator 正解率 = 0.0%（2/2 オーバーライド）",
          op_stats["overridden"] == 2 and op_stats["accuracy_pct"] == 0.0,
          f"got {op_stats}")

    builder_stats = checker.accuracy("builder")
    # builder: d3 = under, d4 = over → over_escalated=1, under_escalated=1
    check("テスト 9: builder — over=1, under=1",
          builder_stats["over_escalated"] == 1
          and builder_stats["under_escalated"] == 1,
          f"got {builder_stats}")

    overall = checker.accuracy()
    # 6 件中 4 件オーバーライド → 正解 2 件 → 33.3%
    check("テスト 10: 全体正解率 = 33.3%",
          abs(overall["accuracy_pct"] - 33.3) < 0.1,
          f"got {overall}")

    worst = checker.worst_agent()
    check("テスト 11: worst_agent = operator（精度 0%）",
          worst == "operator", f"got {worst}")

    strategist_stats = checker.accuracy("strategist")
    check("テスト 12: strategist 正解率 = 100%（オーバーライド無し）",
          strategist_stats["accuracy_pct"] == 100.0,
          f"got {strategist_stats}")

    # ------------------------------------------------------------------
    # テスト 13-17: BudgetAccuracyMonitor
    # ------------------------------------------------------------------
    print("\n📋 テスト 13-17: BudgetAccuracyMonitor")

    monitor = BudgetAccuracyMonitor(log)

    # 系統的に過小見積もり: 全部「予測 < 実コスト」
    monitor.record(d1.decision_id, predicted_jpy=3.0)   # actual 4.2 → +40%
    monitor.record(d2.decision_id, predicted_jpy=0.4)   # actual 0.6 → +50%
    monitor.record(d3.decision_id, predicted_jpy=0.4)   # actual 0.5 → +25%
    monitor.record(d4.decision_id, predicted_jpy=2.5)   # actual 3.8 → +52%
    monitor.record(d5.decision_id, predicted_jpy=1.5)   # actual 2.1 → +40%

    check("テスト 13: 5 件の見積もり記録",
          len(monitor.estimates) == 5)

    mape = monitor.mape()
    # 平均: (40+50+25+52+40)/5 ≈ 41.4
    check("テスト 14: MAPE ≈ 41.4%（過小見積もり傾向）",
          35 <= mape <= 50, f"got {mape}")

    bias = monitor.systematic_bias()
    check("テスト 15: 系統誤差 = 'underestimate'（実コストが予測より高い）",
          bias == "underestimate", f"got {bias}")

    over = monitor.over_budget_decisions(threshold_pct=30.0)
    check("テスト 16: 30% 超過の判定 = 4 件",
          len(over) == 4, f"got {len(over)}")

    # 存在しない decision_id
    null_est = monitor.record("DEC-NOTEXIST", 1.0)
    check("テスト 17: 存在しない decision_id → None",
          null_est is None)

    # ------------------------------------------------------------------
    # テスト 18-22: IncidentReporter
    # ------------------------------------------------------------------
    print("\n📋 テスト 18-22: IncidentReporter")

    inc_reporter = IncidentReporter()

    inc1 = inc_reporter.report(
        "wrong_escalation", "P0",
        "Operator がクレーム判定を B_LIGHT に放置 → 顧客離脱",
        related_decision_id=d5.decision_id,
    )
    inc_reporter.report(
        "budget_overrun", "P1",
        "週次でコスト消費が予測 +40%、月次 3,000 円逼迫",
    )
    inc_reporter.report(
        "model_misuse", "P2",
        "Builder が致命的バグ判定で Haiku 試行（後で Sonnet へ）",
    )
    # 不正値 → P2 にフォールバック
    inc_reporter.report("unknown_type", "X9", "...")

    check("テスト 18: 4 件記録 + 不正値はフォールバック",
          len(inc_reporter.incidents) == 4)

    open_now = inc_reporter.open_incidents()
    check("テスト 19: open_incidents = 4 件（未解決）",
          len(open_now) == 4)

    inc_reporter.resolve(inc1.incident_id, "Operator プロンプトに再分類例を追加")
    check("テスト 20: resolve 後 open = 3 件",
          len(inc_reporter.open_incidents()) == 3)

    crit = inc_reporter.critical_count()
    check("テスト 21: 未解決 critical (P0+P1) = 1 件",
          crit == 1, f"got {crit}")

    by_type = inc_reporter.by_type()
    check("テスト 22: by_type 集計 — wrong_escalation=2 (1 fallback含む)",
          by_type["wrong_escalation"] >= 2,
          f"got {by_type}")

    # ------------------------------------------------------------------
    # テスト 23-27: PromptTuningSuggester
    # ------------------------------------------------------------------
    print("\n📋 テスト 23-27: PromptTuningSuggester")

    suggester = PromptTuningSuggester(checker, monitor, inc_reporter)
    suggestions = suggester.generate()

    check("テスト 23: 提案が生成される（>=1）",
          len(suggestions) >= 1, f"got {len(suggestions)}")

    # under_escalated は P0 で出る
    has_p0 = any(s.priority == "P0" for s in suggestions)
    check("テスト 24: P0 提案あり（under_escalation または critical incident 由来）",
          has_p0, f"priorities={[s.priority for s in suggestions]}")

    # operator は under が 1 件以上ある
    has_operator_target = any(s.target_agent == "operator" for s in suggestions)
    check("テスト 25: operator 向け提案が含まれる",
          has_operator_target,
          f"agents={[s.target_agent for s in suggestions]}")

    # underestimate bias → model_mix 提案 P1
    has_model_mix = any(s.target_kind == "model_mix" for s in suggestions)
    check("テスト 26: コスト過小見積もり → model_mix 提案あり",
          has_model_mix,
          f"kinds={[s.target_kind for s in suggestions]}")

    # ソート順: P0 が先頭
    check("テスト 27: 優先度ソート — 先頭は P0",
          suggestions[0].priority == "P0",
          f"got {suggestions[0].priority}")

    # ------------------------------------------------------------------
    # テスト 28-30: IterationPlanner
    # ------------------------------------------------------------------
    print("\n📋 テスト 28-30: IterationPlanner")

    planner = IterationPlanner()
    metrics_before = {
        "accuracy_pct":     33.3,
        "mape":             41.4,
        "open_incidents":   3,
    }
    it = planner.plan(
        name="Sprint-α / Operator プロンプト改修・Haiku 比率上げ",
        target_changes=[
            "Operator プロンプトに階層判定例 5 件追加",
            "ModelSelector の Haiku デフォルト比率 60→70%",
            "DelegationThreshold の B_LIGHT 基準を緩和",
        ],
        suggestion_ids=[s.suggestion_id for s in suggestions[:3]],
        metrics_before=metrics_before,
    )
    planner.activate(it.iter_id)

    check("テスト 28: 反復作成 → status='active'",
          planner.iterations[it.iter_id].status == "active")

    metrics_after = {
        "accuracy_pct":     72.0,    # +38.7
        "mape":             18.0,    # -23.4
        "open_incidents":   1,       # -2
    }
    result = planner.evaluate(it.iter_id, metrics_after)
    check("テスト 29: 評価結果 improved=True（accuracy↑ mape↓ incidents↓）",
          result["ok"] and result["improved"]
          and abs(result["metrics_delta"]["accuracy_pct"] - 38.7) < 0.1,
          f"got {result}")

    stats = planner.stats()
    check("テスト 30: stats — total=1, by_status.done=1",
          stats["total"] == 1 and stats["by_status"].get("done") == 1,
          f"got {stats}")

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
        print("🎉 Phase 8 完全実装完了！すべてのテストに PASS しました。")
        print()
        print("AI 組織の自己改善サイクル:")
        print("  1. AgentDecisionLog          — 全判定の記録")
        print("  2. EscalationAccuracyChecker — 階層判定の正解率測定")
        print("  3. BudgetAccuracyMonitor     — コスト予測の精度監視")
        print("  4. IncidentReporter          — 運用インシデント追跡")
        print("  5. PromptTuningSuggester     — データ → プロンプト改善提案")
        print("  6. IterationPlanner          — 改善サイクル管理")
        print()
        print("次ステップ: Phase 9 - 本番運用・継続的監視")
    else:
        print()
        print(f"⚠️  {failed} 件のテストが失敗しました。")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    run_tests()
