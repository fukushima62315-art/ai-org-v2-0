# src/judgment/delegation_threshold.py
# v2.0 意思決定権限委譲ルール実装

import json
from enum import Enum
from datetime import datetime
from typing import Dict, Optional, List

class EscalationLevel(Enum):
    A_HARD_STOP = "A_HARD_STOP"
    B_LIGHT_APPROVAL = "B_LIGHT_APPROVAL"
    C_AUTO_DECIDED = "C_AUTO_DECIDED"

class DelegationThreshold:
    """
    v2.0 Delegation Threshold を実装
    
    基本ルール:
    - お金がかかる → 必ず階層 A
    - 法的リスクがある → 必ず階層 A
    - それ以外 → 階層 B or C
    """
    
    def __init__(self):
        # A-1: 金銭発生系キーワード
        self.money_keywords = [
            "課金", "有料", "支出", "金銭", "予算", "コスト", "手数料",
            "クレジットカード", "銀行", "決済", "広告", "購入", "投資",
            "外部サービス", "SaaS", "API", "契約", "契約更新",
            "月額", "年額", "料金", "返金", "補償", "リファンド",
            "アップグレード", "プラン", "有償", "料金プラン"
        ]
        
        # A-2: 法的リスク系キーワード（カテゴリ別）
        self.legal_risk_keywords = {
            "個人情報": ["個人情報", "個人データ", "メール", "電話番号", "住所", "生年月日", "ユーザー情報", "プロフィール"],
            "医療健康": ["医療", "健康", "身体", "疾患", "治療", "処方", "診断", "医師法", "薬機法", "カロリー", "体重"],
            "金融投資": ["金融", "投資", "資産", "為替", "株", "仮想通貨", "ローン", "金商法", "投資信託"],
            "未成年": ["未成年", "子ども", "小学生", "中学生", "高校生", "親権者", "保護者", "青少年"],
            "著作権": ["著作権", "商標", "キャラクター", "画像", "音声", "動画", "コンテンツ"],
            "景表法薬機": ["景品表示", "効能効果", "医学的", "誇大広告", "不実表示"],
            "特商法": ["特商法", "通信販売", "サブスク", "自動更新", "解約"],
            "規約": ["利用規約", "プライバシーポリシー", "規約", "利用条件", "ポリシー"]
        }
    
    def judge(self, decision_text: str, context: Dict = None) -> Dict:
        """
        意思決定文を受け取り、階層を判定
        
        Args:
            decision_text: 判定対象のテキスト
            context: 追加コンテキスト（金額、対象者など）
        
        Returns:
            {
                "escalation_level": "A_HARD_STOP" | "B_LIGHT_APPROVAL" | "C_AUTO_DECIDED",
                "reason": "判定理由",
                "money_risk": bool,
                "legal_risk_categories": List[str],
                "required_user_approval": bool,
                "approval_deadline_hours": Optional[int],
                "timestamp": str
            }
        """
        if context is None:
            context = {}
        
        text_lower = decision_text.lower()
        
        # ===== 階層 A チェック =====
        has_money = self._check_money_risk(text_lower, context)
        legal_risks = self._check_legal_risk(text_lower)
        
        if has_money or legal_risks:
            return {
                "escalation_level": EscalationLevel.A_HARD_STOP.value,
                "reason": f"金銭リスク: {has_money}, 法務リスク: {len(legal_risks) > 0}",
                "money_risk": has_money,
                "legal_risk_categories": legal_risks,
                "required_user_approval": True,
                "approval_deadline_hours": None,  # 緊急性あり
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # ===== 階層 B チェック =====
        if self._check_light_approval(text_lower, context):
            return {
                "escalation_level": EscalationLevel.B_LIGHT_APPROVAL.value,
                "reason": "軽微な変更（予算・計画再配分 20% 未満）",
                "money_risk": False,
                "legal_risk_categories": [],
                "required_user_approval": True,
                "approval_deadline_hours": 24,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # ===== 階層 C（自動判定）=====
        return {
            "escalation_level": EscalationLevel.C_AUTO_DECIDED.value,
            "reason": "技術的判定。金銭・法務影響なし",
            "money_risk": False,
            "legal_risk_categories": [],
            "required_user_approval": False,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _check_money_risk(self, text_lower: str, context: Dict) -> bool:
        """
        金銭リスクをチェック
        - キーワード検出
        - context で金額チェック（月 1,000 円以上 or 既存予算 10% 以上）
        """
        # キーワード検出
        if any(kw in text_lower for kw in self.money_keywords):
            return True
        
        # 金額チェック（コンテキストがあれば）
        if context.get("estimated_cost_jpy"):
            if context["estimated_cost_jpy"] >= 1000:
                return True
        
        if context.get("reallocation_percent"):
            if context["reallocation_percent"] >= 10:
                return True
        
        return False
    
    def _check_legal_risk(self, text_lower: str) -> List[str]:
        """
        法的リスクをチェック、リスク分類を返す
        """
        detected_risks = []
        
        for risk_category, keywords in self.legal_risk_keywords.items():
            if any(kw.lower() in text_lower for kw in keywords):
                detected_risks.append(risk_category)
        
        return list(set(detected_risks))  # 重複排除
    
    def _check_light_approval(self, text_lower: str, context: Dict) -> bool:
        """
        階層 B（簡易承認）に該当するかチェック
        - 予算・計画の 5-20% 再配分
        - SNS 投稿方針変更
        - 軽微な仕様変更
        """
        light_keywords = ["計画", "スケジュール", "投稿", "方針", "軽微", "削減", "調整"]
        
        if any(kw in text_lower for kw in light_keywords):
            if context.get("reallocation_percent"):
                if 5 <= context["reallocation_percent"] < 20:
                    return True
            else:
                return True
        
        return False

# __init__.py
__all__ = ['DelegationThreshold', 'EscalationLevel']
