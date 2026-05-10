#!/usr/bin/env python3
"""
Phase 1 自動実行スクリプト
意思決定エンジン + 通知テンプレート + ユーザー応答受付 + 監査ログ
すべてを単一ファイルに統合し、依存性なしで実行可能
"""

import json
import uuid
from typing import Dict, List, Optional, Literal, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import re

# ============================================================================
# 設定
# ============================================================================

MONTHLY_BUDGET_JPY = 3000
MONEY_TRIGGER_KEYWORDS = {
    "新規支出": ["支出", "課金", "月額", "年額", "購入", "契約"],
    "外部サービス": ["SaaS", "API", "有料", "プラン"],
}

LEGAL_RISK_KEYWORDS = {
    "個人情報": ["個人情報", "メール", "名前", "住所", "アカウント"],
    "医療健康": ["医療", "診断", "治療", "薬", "ダイエット", "体重", "身体"],
    "金融投資": ["金融", "投資", "資産", "運用"],
}

# ============================================================================
# Phase 1: 階層判定エンジン
# ============================================================================

@dataclass
class EscalationRequest:
    request_id: str
    timestamp: str
    from_agent: str
    decision_context: str
    money_involved: Optional[float] = None
    legal_risks: List[str] = None
    
    def __post_init__(self):
        if self.legal_risks is None:
            self.legal_risks = []


@dataclass
class EscalationResponse:
    request_id: str
    escalation_level: str
    triggers: List[str]
    recommendation: str


class DelegationThreshold:
    def __init__(self):
        self.history: List[EscalationResponse] = []
    
    def judge(self, request: EscalationRequest) -> EscalationResponse:
        # A-1: 金銭発生
        if self._check_money_trigger(request):
            return self._respond(request.request_id, "A_HARD_STOP", 
                               ["A-1: 金銭発生"], "お金が発生するため、ユーザー確認必須")
        
        # A-2: 法務リスク
        legal_risks = self._check_legal_risks(request)
        if legal_risks:
            return self._respond(request.request_id, "A_HARD_STOP",
                               [f"A-2: 法務リスク ({', '.join(legal_risks)})"],
                               "法務リスクがあるため、ユーザー確認必須")
        
        # B: 簡易承認
        if self._check_light_approval(request):
            return self._respond(request.request_id, "B_LIGHT_APPROVAL",
                               ["B: 簡易承認"], "軽微な変更のため、24h 以内の承認で進める")
        
        # C: 自動判定
        return self._respond(request.request_id, "C_AUTO_DECIDED",
                           ["C: 自動判定"], "技術選定などの定型判断のため自動判定で進める")
    
    def _check_money_trigger(self, request: EscalationRequest) -> bool:
        if request.money_involved is not None and request.money_involved >= 1000:
            return True
        for keywords in MONEY_TRIGGER_KEYWORDS.values():
            for keyword in keywords:
                if keyword.lower() in request.decision_context.lower():
                    return True
        return False
    
    def _check_legal_risks(self, request: EscalationRequest) -> List[str]:
        detected = []
        for category, keywords in LEGAL_RISK_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in request.decision_context.lower():
                    detected.append(category)
                    break
        detected.extend(request.legal_risks)
        return list(set(detected))
    
    def _check_light_approval(self, request: EscalationRequest) -> bool:
        light_keywords = ["計画変更", "リソース再配分", "5%", "再配分", "SNS"]
        for keyword in light_keywords:
            if keyword.lower() in request.decision_context.lower():
                return True
        return False
    
    def _respond(self, req_id: str, level: str, triggers: List[str], rec: str) -> EscalationResponse:
        response = EscalationResponse(req_id, level, triggers, rec)
        self.history.append(response)
        return response
    
    def get_stats(self) -> Dict:
        total = len(self.history)
        a = sum(1 for h in self.history if h.escalation_level == "A_HARD_STOP")
        b = sum(1 for h in self.history if h.escalation_level == "B_LIGHT_APPROVAL")
        c = sum(1 for h in self.history if h.escalation_level == "C_AUTO_DECIDED")
        return {
            "total": total,
            "layer_a": a,
            "layer_b": b,
            "layer_c": c,
            "a_pct": (a/total*100) if total > 0 else 0,
        }


# ============================================================================
# Phase 1: 通知テンプレート
# ============================================================================

@dataclass
class LayerANotification:
    escalation_level: str = "A_HARD_STOP"
    notification_id: str = ""
    from_agent: str = ""
    what_we_planned: str = ""
    why_it_matters: str = ""
    money_impact: Dict = None
    legal_impact: Dict = None
    ceo_recommendation: str = ""
    alternatives: List[Dict] = None
    
    def __post_init__(self):
        if not self.notification_id:
            self.notification_id = f"NOTIF-{uuid.uuid4().hex[:8]}"
        if self.money_impact is None:
            self.money_impact = {"applies": False}
        if self.legal_impact is None:
            self.legal_impact = {"applies": False}
        if self.alternatives is None:
            self.alternatives = []


class NotificationBuilder:
    @staticmethod
    def build_firebase():
        return LayerANotification(
            from_agent="Builder",
            what_we_planned="Firebase を Spark プランから Blaze プラン（月 3,000 円）に切り替え",
            why_it_matters="DB 容量が 500MB 上限に達した",
            money_impact={"applies": True, "amount_jpy": 3000, "monthly": True},
            ceo_recommendation="Firebase Blaze プランへのアップグレード推奨",
            alternatives=[
                {"id": "migrate", "label": "Supabase に移行", "cost": 3000, "effort_hours": 40},
                {"id": "cleanup", "label": "不要データを削除", "cost": 0, "effort_hours": 8},
            ]
        )


# ============================================================================
# Phase 1: ユーザー応答受付
# ============================================================================

@dataclass
class UserResponse:
    response_id: str
    notification_id: str
    timestamp: str
    user_decision: str  # APPROVED, REJECTED, NEEDS_INFO
    reasoning: str = ""


class UserResponseHandler:
    def __init__(self):
        self.pending: Dict = {}
        self.responses: List[UserResponse] = []
    
    def register(self, notif_id: str, from_agent: str, level: str, timeout_h: Optional[int]):
        self.pending[notif_id] = {
            "from_agent": from_agent,
            "level": level,
            "issued_at": datetime.now().isoformat(),
            "timeout_hours": timeout_h,
            "status": "PENDING"
        }
        return {"success": True, "notification_id": notif_id}
    
    def submit_response(self, notif_id: str, decision: str, reasoning: str = ""):
        if notif_id not in self.pending:
            return {"success": False, "error": "通知IDが見つかりません"}
        
        response = UserResponse(
            response_id=f"RESP-{uuid.uuid4().hex[:8]}",
            notification_id=notif_id,
            timestamp=datetime.now().isoformat(),
            user_decision=decision,
            reasoning=reasoning,
        )
        self.responses.append(response)
        self.pending[notif_id]["status"] = decision
        return {"success": True, "decision": decision}
    
    def get_stats(self) -> Dict:
        total = len(self.responses)
        approved = sum(1 for r in self.responses if r.user_decision == "APPROVED")
        return {
            "total_responses": total,
            "approved": approved,
            "approval_rate_pct": (approved/total*100) if total > 0 else 0,
            "pending": sum(1 for p in self.pending.values() if p["status"] == "PENDING")
        }


# ============================================================================
# Phase 1: 監査ログ
# ============================================================================

@dataclass
class AuditEntry:
    timestamp: str
    event_type: str
    escalation_level: str
    from_agent: str
    result: str


class AuditLogger:
    def __init__(self):
        self.entries: List[AuditEntry] = []
    
    def log_judgment(self, level: str, from_agent: str, triggers: List[str]):
        self.entries.append(AuditEntry(
            timestamp=datetime.now().isoformat(),
            event_type="JUDGMENT",
            escalation_level=level,
            from_agent=from_agent,
            result=", ".join(triggers),
        ))
    
    def get_monthly_stats(self) -> Dict:
        total = len(self.entries)
        a = sum(1 for e in self.entries if e.escalation_level == "A_HARD_STOP")
        b = sum(1 for e in self.entries if e.escalation_level == "B_LIGHT_APPROVAL")
        c = sum(1 for e in self.entries if e.escalation_level == "C_AUTO_DECIDED")
        return {
            "total": total,
            "layer_a": a,
            "layer_b": b,
            "layer_c": c,
        }


# ============================================================================
# テスト実行
# ============================================================================

def run_tests():
    """Phase 1 の 21 テストケースを実行"""
    
    print("=" * 80)
    print("🚀 Phase 1 統合テスト実行")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    # テスト 1-6: DelegationThreshold
    print("\n📋 テスト 1-6: DelegationThreshold（階層判定）")
    engine = DelegationThreshold()
    
    # テスト 1
    try:
        req1 = EscalationRequest("T1", datetime.now().isoformat(), "Builder", 
                                "Firebase 月 3000 円", money_involved=3000)
        res1 = engine.judge(req1)
        assert res1.escalation_level == "A_HARD_STOP", "金銭発生で階層 A のはず"
        print("✅ テスト 1: 金銭発生 → 階層 A")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 1 失敗: {e}")
        failed += 1
    
    # テスト 2
    try:
        req2 = EscalationRequest("T2", datetime.now().isoformat(), "Builder",
                                "個人情報（メール）を保存")
        res2 = engine.judge(req2)
        assert res2.escalation_level == "A_HARD_STOP", "個人情報で階層 A のはず"
        print("✅ テスト 2: 法務リスク（個人情報） → 階層 A")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 2 失敗: {e}")
        failed += 1
    
    # テスト 3
    try:
        req3 = EscalationRequest("T3", datetime.now().isoformat(), "Builder",
                                "ダイエットアプリで体重・身長を記録")
        res3 = engine.judge(req3)
        assert res3.escalation_level == "A_HARD_STOP", "医療健康で階層 A のはず"
        print("✅ テスト 3: 法務リスク（医療・健康） → 階層 A")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 3 失敗: {e}")
        failed += 1
    
    # テスト 4
    try:
        req4 = EscalationRequest("T4", datetime.now().isoformat(), "Strategist",
                                "開発時間を 30h → 35h に再配分（5% 増）")
        res4 = engine.judge(req4)
        assert res4.escalation_level == "B_LIGHT_APPROVAL", "軽微変更で階層 B のはず"
        print("✅ テスト 4: 軽微な変更 → 階層 B")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 4 失敗: {e}")
        failed += 1
    
    # テスト 5
    try:
        req5 = EscalationRequest("T5", datetime.now().isoformat(), "Builder",
                                "React Native ライブラリを A から B に変更")
        res5 = engine.judge(req5)
        assert res5.escalation_level == "C_AUTO_DECIDED", "技術選定で階層 C のはず"
        print("✅ テスト 5: 技術選定 → 階層 C")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 5 失敗: {e}")
        failed += 1
    
    # テスト 6
    try:
        stats = engine.get_stats()
        assert stats["total"] == 5, "5 つの判定があるはず"
        assert "a_pct" in stats, "統計に a_pct があるはず"
        print(f"✅ テスト 6: 月次統計 → 計 {stats['total']} 件, 階層A {stats['layer_a']} 件")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 6 失敗: {e}")
        failed += 1
    
    # テスト 7-11: Notification Templates
    print("\n📋 テスト 7-11: NotificationTemplates（通知テンプレート）")
    
    # テスト 7
    try:
        notif = NotificationBuilder.build_firebase()
        assert notif.escalation_level == "A_HARD_STOP", "Firebase は階層 A のはず"
        print("✅ テスト 7: Firebase テンプレート → 階層 A")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 7 失敗: {e}")
        failed += 1
    
    # テスト 8
    try:
        assert notif.money_impact["applies"] == True, "金銭影響があるはず"
        print("✅ テスト 8: 金銭影響を検出")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 8 失敗: {e}")
        failed += 1
    
    # テスト 9
    try:
        assert len(notif.alternatives) > 0, "代替案があるはず"
        print(f"✅ テスト 9: 代替案を生成 → {len(notif.alternatives)} 件")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 9 失敗: {e}")
        failed += 1
    
    # テスト 10
    try:
        assert notif.notification_id.startswith("NOTIF-"), "通知 ID が生成されているはず"
        print(f"✅ テスト 10: 通知 ID 生成 → {notif.notification_id}")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 10 失敗: {e}")
        failed += 1
    
    # テスト 11
    try:
        json_str = json.dumps(asdict(notif), ensure_ascii=False, indent=2)
        assert len(json_str) > 0, "JSON シリアライズができるはず"
        print("✅ テスト 11: JSON シリアライズ可能")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 11 失敗: {e}")
        failed += 1
    
    # テスト 12-16: UserResponseHandler
    print("\n📋 テスト 12-16: UserResponseHandler（ユーザー応答受付）")
    handler = UserResponseHandler()
    
    # テスト 12
    try:
        result = handler.register("NOTIF-001", "Builder", "A_HARD_STOP", 24)
        assert result["success"] == True, "リクエスト登録が成功するはず"
        print("✅ テスト 12: リクエスト登録")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 12 失敗: {e}")
        failed += 1
    
    # テスト 13
    try:
        result = handler.submit_response("NOTIF-001", "APPROVED", "同意します")
        assert result["success"] == True, "応答受け付けが成功するはず"
        print("✅ テスト 13: ユーザー承認応答")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 13 失敗: {e}")
        failed += 1
    
    # テスト 14
    try:
        handler.register("NOTIF-002", "Builder", "B_LIGHT_APPROVAL", 24)
        handler.submit_response("NOTIF-002", "REJECTED", "同意できません")
        assert handler.pending["NOTIF-002"]["status"] == "REJECTED", "却下ステータスが設定されているはず"
        print("✅ テスト 14: ユーザー却下応答")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 14 失敗: {e}")
        failed += 1
    
    # テスト 15
    try:
        stats = handler.get_stats()
        assert stats["total_responses"] == 2, "2 つの応答があるはず"
        assert stats["approval_rate_pct"] == 50.0, "承認率 50% のはず"
        print(f"✅ テスト 15: 月次統計 → 承認率 {stats['approval_rate_pct']:.1f}%")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 15 失敗: {e}")
        failed += 1
    
    # テスト 16
    try:
        assert stats["pending"] == 0, "待機中リクエストがないはず"
        print("✅ テスト 16: 待機中リクエスト状態")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 16 失敗: {e}")
        failed += 1
    
    # テスト 17-21: Audit & Reporting
    print("\n📋 テスト 17-21: Audit & Reporting（監査ログ・レポート）")
    audit = AuditLogger()
    
    # テスト 17
    try:
        audit.log_judgment("A_HARD_STOP", "Builder", ["金銭発生"])
        assert len(audit.entries) == 1, "1 つのログエントリがあるはず"
        print("✅ テスト 17: 判定ログ記録")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 17 失敗: {e}")
        failed += 1
    
    # テスト 18
    try:
        audit.log_judgment("B_LIGHT_APPROVAL", "Strategist", ["軽微変更"])
        assert len(audit.entries) == 2, "2 つのログエントリがあるはず"
        print("✅ テスト 18: 複数ログ記録")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 18 失敗: {e}")
        failed += 1
    
    # テスト 19
    try:
        audit.log_judgment("C_AUTO_DECIDED", "Builder", ["技術選定"])
        stats = audit.get_monthly_stats()
        assert stats["total"] == 3, "3 つのエントリがあるはず"
        print(f"✅ テスト 19: 月次統計 → 計 {stats['total']} 件（A:{stats['layer_a']}, B:{stats['layer_b']}, C:{stats['layer_c']}）")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 19 失敗: {e}")
        failed += 1
    
    # テスト 20
    try:
        entry = audit.entries[0]
        assert entry.event_type == "JUDGMENT", "イベント型が JUDGMENT のはず"
        assert entry.escalation_level == "A_HARD_STOP", "階層が A_HARD_STOP のはず"
        print("✅ テスト 20: ログエントリの詳細確認")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 20 失敗: {e}")
        failed += 1
    
    # テスト 21
    try:
        monthly_report = {
            "report_period": "2026-05",
            "total_decisions": stats["total"],
            "layer_a": stats["layer_a"],
            "layer_b": stats["layer_b"],
            "layer_c": stats["layer_c"],
        }
        json_report = json.dumps(monthly_report, ensure_ascii=False, indent=2)
        assert "2026-05" in json_report, "レポート期間が含まれているはず"
        print("✅ テスト 21: 月次レポート JSON 生成")
        passed += 1
    except AssertionError as e:
        print(f"❌ テスト 21 失敗: {e}")
        failed += 1
    
    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 テスト結果サマリー")
    print("=" * 80)
    print(f"✅ 成功: {passed}/21")
    print(f"❌ 失敗: {failed}/21")
    print(f"📈 成功率: {passed/21*100:.1f}%")
    print("=" * 80)
    
    if failed == 0:
        print("\n🎉 Phase 1 完全実装完了！すべてのテストに PASS しました。")
        print("\n次ステップ: Phase 2 - Strategist の RAR-S 計算実装")
    
    return passed == 21


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
