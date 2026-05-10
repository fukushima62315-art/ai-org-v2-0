#!/usr/bin/env python3
"""
Phase 2 自動実行スクリプト
Strategist RAR-S 計算エンジン
単一ファイル、依存性ゼロで実行可能

実装内容:
  - RAR-S スコア計算（log10ベース、範囲 0.3〜1.5）
  - 3 シナリオ財務試算（保守・中立・楽観）
  - Conviction スコア（信念ベースの kill 基準緩和）
  - KillCriteria 自動生成・判定
  - 月次振り返り機能
"""

import json
import math
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

# ============================================================================
# Phase 2: RAR-S 入力・出力データクラス
# ============================================================================

@dataclass
class RARSInput:
    """RAR-S スコア計算の入力"""
    opportunity_id: str
    title: str
    monthly_revenue_jpy: float       # 月次収益期待値 (JPY)
    success_probability: float        # 成功確率 0.0-1.0
    risk_factor: float                # リスク係数 0.0-2.0（高いほど危険）
    time_to_market_months: int        # 市場投入まで何ヶ月
    gross_margin: float = 0.70       # 粗利率
    growth_rate_annual: float = 0.30 # 年間成長率
    annual_cost_jpy: float = 0.0     # 年間固定コスト (JPY)

    def __post_init__(self):
        self.success_probability = max(0.01, min(1.0, self.success_probability))
        self.risk_factor = max(0.0, min(2.0, self.risk_factor))
        self.time_to_market_months = max(1, self.time_to_market_months)


@dataclass
class ScenarioResult:
    """1シナリオの試算結果"""
    scenario_name: str           # conservative / neutral / optimistic
    revenue_multiplier: float
    rar_s_score: float
    annual_gross_profit_jpy: float
    cumulative_3year_jpy: float


@dataclass
class RARSResult:
    """RAR-S 全シナリオ結果"""
    opportunity_id: str
    title: str
    timestamp: str
    conservative: ScenarioResult
    neutral: ScenarioResult
    optimistic: ScenarioResult
    money_required: bool
    legal_risk: bool

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# Phase 2: Conviction スコア
# ============================================================================

@dataclass
class ConvictionScore:
    """Conviction スコア — ユーザーの信念強度を表す"""
    opportunity_id: str
    score: float                    # 0〜10
    rationale: str
    registered_at: str
    override_kill_threshold: bool   # kill 基準を緩和するか

    @property
    def is_strong(self) -> bool:
        return self.score >= 7.0

    @property
    def override_threshold(self) -> float:
        """score が高いほど撤退基準を緩和する割合"""
        if self.score >= 9.0:
            return 0.5   # 50% 緩和
        elif self.score >= 7.0:
            return 0.3   # 30% 緩和
        else:
            return 0.0   # 緩和なし


# ============================================================================
# Phase 2: Kill Criteria（撤退基準）
# ============================================================================

@dataclass
class KillCriteria:
    """撤退基準 — 自動生成または手動設定"""
    opportunity_id: str
    revenue_threshold_jpy: float   # 月次収益がこれ以下なら撤退
    months_to_evaluate: int        # 評価タイミング（ヶ月後）
    max_burn_jpy: float            # 最大許容コスト (JPY)
    auto_generated: bool = True

    def should_kill(
        self,
        actual_monthly_revenue: float,
        months_elapsed: int,
        total_spent_jpy: float,
        conviction: Optional[ConvictionScore] = None,
    ) -> Tuple[bool, str]:
        """撤退判定。(kill: bool, reason: str) を返す"""
        threshold = self.revenue_threshold_jpy
        burn_limit = self.max_burn_jpy

        if conviction and conviction.override_kill_threshold:
            relaxation = conviction.override_threshold
            threshold *= (1 - relaxation)
            burn_limit *= (1 + relaxation)

        if months_elapsed >= self.months_to_evaluate:
            if actual_monthly_revenue < threshold:
                return True, f"収益 {actual_monthly_revenue:,.0f}円 < 基準 {threshold:,.0f}円"

        if total_spent_jpy > burn_limit:
            return True, f"コスト {total_spent_jpy:,.0f}円 > 上限 {burn_limit:,.0f}円"

        return False, "継続"


# ============================================================================
# Phase 2: RAR-S 計算エンジン
# ============================================================================

class RARSCalculator:
    """
    RAR-S = log10( EV_annual / (REF × risk × speed_penalty) ) + 1.0
    クランプ範囲: 0.3 〜 1.5
    """

    REFERENCE_ANNUAL_EV = 1_200_000  # 基準 EV (100万円/年)

    SCENARIOS = {
        "conservative": {"revenue": 0.5, "prob": 0.7, "risk": 1.3},
        "neutral":       {"revenue": 1.0, "prob": 1.0, "risk": 1.0},
        "optimistic":    {"revenue": 1.5, "prob": 1.2, "risk": 0.8},
    }

    @classmethod
    def calculate(cls, inp: RARSInput) -> RARSResult:
        scenarios: Dict[str, ScenarioResult] = {}
        for name, m in cls.SCENARIOS.items():
            adj_revenue = inp.monthly_revenue_jpy * m["revenue"]
            adj_prob    = min(1.0, inp.success_probability * m["prob"])
            adj_risk    = min(2.0, inp.risk_factor * m["risk"])

            score  = cls._rar_s(adj_revenue, adj_prob, adj_risk, inp.time_to_market_months)
            annual = cls._annual_gp(adj_revenue, inp.gross_margin, inp.annual_cost_jpy)
            cum3yr = cls._cum_3year(annual, inp.growth_rate_annual)

            scenarios[name] = ScenarioResult(
                scenario_name=name,
                revenue_multiplier=m["revenue"],
                rar_s_score=round(score, 3),
                annual_gross_profit_jpy=round(annual),
                cumulative_3year_jpy=round(cum3yr),
            )

        return RARSResult(
            opportunity_id=inp.opportunity_id,
            title=inp.title,
            timestamp=datetime.now().isoformat(),
            conservative=scenarios["conservative"],
            neutral=scenarios["neutral"],
            optimistic=scenarios["optimistic"],
            money_required=inp.annual_cost_jpy > 0,
            legal_risk=False,
        )

    @classmethod
    def _rar_s(cls, monthly_rev: float, prob: float, risk: float, months: int) -> float:
        ev_annual     = monthly_rev * 12 * prob
        speed_penalty = max(0.5, months / 6)
        denominator   = cls.REFERENCE_ANNUAL_EV * max(0.1, risk) * speed_penalty
        raw = math.log10(max(ev_annual, 1) / denominator) + 1.0
        return max(0.3, min(1.5, raw))

    @classmethod
    def _annual_gp(cls, monthly_rev: float, margin: float, annual_cost: float) -> float:
        return monthly_rev * 12 * margin - annual_cost

    @classmethod
    def _cum_3year(cls, year1_gp: float, growth: float) -> float:
        year2 = year1_gp * (1 + growth)
        year3 = year2   * (1 + growth)
        return year1_gp + year2 + year3


# ============================================================================
# Phase 2: 機会総合評価
# ============================================================================

class OpportunityEvaluator:
    """RAR-S + Conviction + KillCriteria を統合した機会評価"""

    def __init__(self):
        self.evaluations: List[Dict] = []

    def evaluate(
        self,
        inp: RARSInput,
        conviction: Optional[ConvictionScore] = None,
    ) -> Dict:
        result = RARSCalculator.calculate(inp)

        burn_base = inp.annual_cost_jpy if inp.annual_cost_jpy > 0 else inp.monthly_revenue_jpy * 6
        kill = KillCriteria(
            opportunity_id=inp.opportunity_id,
            revenue_threshold_jpy=inp.monthly_revenue_jpy * 0.3,
            months_to_evaluate=max(3, inp.time_to_market_months + 2),
            max_burn_jpy=burn_base * 1.5,
            auto_generated=True,
        )

        eval_result = {
            "opportunity_id": inp.opportunity_id,
            "title": inp.title,
            "rar_s": {
                "conservative": result.conservative.rar_s_score,
                "neutral":      result.neutral.rar_s_score,
                "optimistic":   result.optimistic.rar_s_score,
            },
            "gross_profit_3year": {
                "conservative": result.conservative.cumulative_3year_jpy,
                "neutral":      result.neutral.cumulative_3year_jpy,
                "optimistic":   result.optimistic.cumulative_3year_jpy,
            },
            "kill_criteria": {
                "revenue_threshold_jpy": kill.revenue_threshold_jpy,
                "months_to_evaluate":    kill.months_to_evaluate,
                "max_burn_jpy":          kill.max_burn_jpy,
            },
            "conviction_score":   conviction.score if conviction else None,
            "needs_user_approval": result.money_required or result.legal_risk,
            "recommendation":     self._recommend(result.neutral.rar_s_score),
        }

        self.evaluations.append(eval_result)
        return eval_result

    def _recommend(self, rar_s: float) -> str:
        if rar_s >= 1.3:
            return "強く推奨：高い収益性・低リスク"
        elif rar_s >= 1.0:
            return "推奨：収益性・リスクバランス良好"
        elif rar_s >= 0.7:
            return "条件付き推奨：要追加検証"
        else:
            return "非推奨：収益性・リスクが課題"

    def get_top_opportunities(self, n: int = 3) -> List[Dict]:
        return sorted(
            self.evaluations,
            key=lambda x: x["rar_s"]["neutral"],
            reverse=True,
        )[:n]


# ============================================================================
# Phase 2: 月次振り返り
# ============================================================================

class MonthlyReview:
    """月次振り返りレポート生成"""

    def __init__(self):
        self.evaluations: List[Dict] = []
        self.month = datetime.now().strftime("%Y-%m")

    def add_evaluation(self, eval_result: Dict):
        self.evaluations.append(eval_result)

    def get_stats(self) -> Dict:
        if not self.evaluations:
            return {"total": 0, "avg_rar_s": 0.0, "recommended": 0, "needs_approval": 0}
        scores = [e["rar_s"]["neutral"] for e in self.evaluations]
        return {
            "total":          len(self.evaluations),
            "avg_rar_s":      round(sum(scores) / len(scores), 3),
            "recommended":    sum(1 for s in scores if s >= 1.0),
            "needs_approval": sum(1 for e in self.evaluations if e["needs_user_approval"]),
            "month":          self.month,
        }

    def generate_report(self) -> Dict:
        stats = self.get_stats()
        top3  = sorted(self.evaluations, key=lambda x: x["rar_s"]["neutral"], reverse=True)[:3]
        return {
            "report_id":        f"MONTHLY-{self.month}-{uuid.uuid4().hex[:6].upper()}",
            "month":            self.month,
            "stats":            stats,
            "top_opportunities": top3,
            "generated_at":     datetime.now().isoformat(),
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
    print("🚀 Phase 2 統合テスト実行")
    print("=" * 80)

    # ------------------------------------------------------------------
    # テスト 1-3: RARSInput 基本
    # ------------------------------------------------------------------
    print("\n📋 テスト 1-3: RARSInput 基本")
    inp = RARSInput(
        opportunity_id="OPP-001",
        title="英会話アプリ月額サービス",
        monthly_revenue_jpy=200_000,
        success_probability=0.6,
        risk_factor=0.8,
        time_to_market_months=4,
        gross_margin=0.75,
        growth_rate_annual=0.40,
        annual_cost_jpy=500_000,
    )
    check("テスト 1: RARSInput 作成", inp.opportunity_id == "OPP-001")
    check("テスト 2: success_probability クランプ (0, 1]",
          0.0 < inp.success_probability <= 1.0)
    check("テスト 3: time_to_market_months >= 1", inp.time_to_market_months >= 1)

    # ------------------------------------------------------------------
    # テスト 4-8: RAR-S スコア計算
    # ------------------------------------------------------------------
    print("\n📋 テスト 4-8: RAR-S スコア計算")
    result = RARSCalculator.calculate(inp)
    check("テスト 4: conservative スコア範囲 [0.3, 1.5]",
          0.3 <= result.conservative.rar_s_score <= 1.5,
          f"got {result.conservative.rar_s_score}")
    check("テスト 5: neutral スコア範囲 [0.3, 1.5]",
          0.3 <= result.neutral.rar_s_score <= 1.5,
          f"got {result.neutral.rar_s_score}")
    check("テスト 6: optimistic スコア範囲 [0.3, 1.5]",
          0.3 <= result.optimistic.rar_s_score <= 1.5,
          f"got {result.optimistic.rar_s_score}")
    check("テスト 7: optimistic >= neutral >= conservative",
          result.optimistic.rar_s_score >= result.neutral.rar_s_score
          >= result.conservative.rar_s_score,
          f"opt={result.optimistic.rar_s_score} "
          f"neu={result.neutral.rar_s_score} "
          f"con={result.conservative.rar_s_score}")
    check("テスト 8: timestamp 生成", bool(result.timestamp))

    # ------------------------------------------------------------------
    # テスト 9-11: 3年累積粗利試算
    # ------------------------------------------------------------------
    print("\n📋 テスト 9-11: 3年累積粗利試算")
    check("テスト 9: conservative 3年累積 > 0",
          result.conservative.cumulative_3year_jpy > 0,
          f"got {result.conservative.cumulative_3year_jpy}")
    check("テスト 10: optimistic > neutral > conservative (3年累積)",
          result.optimistic.cumulative_3year_jpy
          > result.neutral.cumulative_3year_jpy
          > result.conservative.cumulative_3year_jpy)
    expected_neutral_gp = round(200_000 * 12 * 0.75 - 500_000)
    check("テスト 11: neutral 年次粗利 = 月収×12×margin - cost",
          result.neutral.annual_gross_profit_jpy == expected_neutral_gp,
          f"got {result.neutral.annual_gross_profit_jpy}, expected {expected_neutral_gp}")

    # ------------------------------------------------------------------
    # テスト 12-14: ConvictionScore
    # ------------------------------------------------------------------
    print("\n📋 テスト 12-14: ConvictionScore")
    conviction = ConvictionScore(
        opportunity_id="OPP-001",
        score=8.5,
        rationale="息子の英語習得という強い動機があり、市場ニーズも確認済み",
        registered_at=datetime.now().isoformat(),
        override_kill_threshold=True,
    )
    check("テスト 12: ConvictionScore 生成", conviction.score == 8.5)
    check("テスト 13: is_strong (score >= 7.0)", conviction.is_strong)
    check("テスト 14: override_threshold = 0.3 (score 7〜9)",
          conviction.override_threshold == 0.3)

    # ------------------------------------------------------------------
    # テスト 15-17: KillCriteria
    # ------------------------------------------------------------------
    print("\n📋 テスト 15-17: KillCriteria")
    kill = KillCriteria(
        opportunity_id="OPP-001",
        revenue_threshold_jpy=60_000,
        months_to_evaluate=6,
        max_burn_jpy=1_200_000,
        auto_generated=True,
    )
    # 収益不足 → 撤退
    triggered, reason = kill.should_kill(30_000, 7, 500_000)
    check("テスト 15: 収益不足で撤退", triggered, f"reason={reason}")

    # 収益十分 → 継続
    no_kill, _ = kill.should_kill(100_000, 7, 500_000)
    check("テスト 16: 収益十分なら継続", not no_kill)

    # Conviction 緩和: threshold が 60,000 × 0.7 = 42,000 に下がる
    # 実収益 50,000 >= 42,000 なので継続
    conviction_kill, _ = kill.should_kill(50_000, 7, 500_000, conviction)
    check("テスト 17: Conviction 緩和で撤退基準が下がる（50,000円が継続になる）",
          not conviction_kill)

    # ------------------------------------------------------------------
    # テスト 18-21: OpportunityEvaluator
    # ------------------------------------------------------------------
    print("\n📋 テスト 18-21: OpportunityEvaluator 総合評価")
    evaluator = OpportunityEvaluator()
    eval_result = evaluator.evaluate(inp, conviction)
    check("テスト 18: 評価結果に rar_s キーあり", "rar_s" in eval_result)
    check("テスト 19: JSON シリアライズ可能", bool(json.dumps(eval_result)))
    check("テスト 20: kill_criteria 自動生成", "kill_criteria" in eval_result)
    check("テスト 21: conviction_score = 8.5 反映",
          eval_result["conviction_score"] == 8.5)

    # ------------------------------------------------------------------
    # テスト 22-23: 複数機会ランキング
    # ------------------------------------------------------------------
    print("\n📋 テスト 22-23: 複数機会比較・ランキング")
    inp_low  = RARSInput("OPP-002", "低収益サービス",  10_000, 0.3, 1.5, 12)
    inp_high = RARSInput("OPP-003", "高収益サービス", 500_000, 0.8, 0.5,  2)
    evaluator.evaluate(inp_low)
    evaluator.evaluate(inp_high)

    top2 = evaluator.get_top_opportunities(2)
    check("テスト 22: top 2 件取得", len(top2) == 2)
    check("テスト 23: OPP-003 が 1 位",
          top2[0]["opportunity_id"] == "OPP-003",
          f"got {top2[0]['opportunity_id']}")

    # ------------------------------------------------------------------
    # テスト 24-26: MonthlyReview
    # ------------------------------------------------------------------
    print("\n📋 テスト 24-26: 月次振り返り")
    review = MonthlyReview()
    review.add_evaluation(evaluator.evaluations[0])  # OPP-001
    review.add_evaluation(evaluator.evaluations[1])  # OPP-002
    review.add_evaluation(evaluator.evaluations[2])  # OPP-003

    stats = review.get_stats()
    check("テスト 24: 月次統計 3 件", stats["total"] == 3,
          f"got {stats['total']}")
    check("テスト 25: 平均 RAR-S 範囲 [0.3, 1.5]",
          0.3 <= stats["avg_rar_s"] <= 1.5,
          f"got {stats['avg_rar_s']}")

    report = review.generate_report()
    check("テスト 26: 月次レポート生成（report_id + top_opportunities）",
          "report_id" in report and "top_opportunities" in report)

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
        print("🎉 Phase 2 完全実装完了！すべてのテストに PASS しました。")
        print()
        print("次ステップ: Phase 3 - Builder × Operator 統合テスト")
    else:
        print()
        print(f"⚠️  {failed} 件のテストが失敗しました。")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    run_tests()
