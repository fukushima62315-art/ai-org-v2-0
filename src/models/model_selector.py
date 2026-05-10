# src/models/model_selector.py
# v2.0 モデル選択戦略：Haiku デフォルト + Sonnet クリティカル判定

import json
from enum import Enum
from typing import Dict, Literal, Optional
from datetime import datetime

class ModelType(Enum):
    HAIKU = "claude-3-5-haiku-20241022"
    SONNET = "claude-sonnet-4-20250514"
    OPUS = "claude-opus-4-6"  # 禁止

class TaskPriority(Enum):
    """タスク優先度 = Claude API コストに直結"""
    ROUTINE = "ROUTINE"              # Haiku 推奨
    NORMAL = "NORMAL"                # Haiku 推奨
    COMPLEX = "COMPLEX"              # Sonnet 推奨
    CRITICAL = "CRITICAL"            # Sonnet 必須
    EMERGENCY = "EMERGENCY"          # Sonnet 必須

class ModelSelector:
    """
    v2.0 モデル選択戦略を実装
    
    基本原則:
    - Haiku をデフォルト（月予算 70-80%）
    - Sonnet をクリティカル判定（月予算 20-30%）
    - Opus は絶対に使用しない（0%）
    
    予算配分:
    - Strategist: Haiku 560 円 + Sonnet 240 円 = 800 円
    - Builder: Haiku 900 円 + Sonnet 600 円 = 1,500 円
    - Operator: Haiku 350 円 + Sonnet 150 円 = 500 円
    - 予備: Sonnet 200 円 = 200 円
    """
    
    def __init__(self):
        self.monthly_limit = 3000
        self.haiku_budget = 1810  # 月 60%
        self.sonnet_budget = 1190  # 月 40%
        self.opus_forbidden = True
        
        self.monthly_consumption = {
            "haiku": 0,
            "sonnet": 0,
            "opus": 0
        }
    
    def select_model(
        self,
        agent: str,
        task_type: str,
        context: Dict = None,
        is_critical: bool = False
    ) -> Literal["haiku", "sonnet"]:
        """
        エージェント・タスク・コンテキストに基づいてモデルを選択
        
        Args:
            agent: "strategist" | "builder" | "operator"
            task_type: タスク種別（複数記述例は下記参照）
            context: 追加コンテキスト
            is_critical: クリティカル判定（金銭・法務・命に関わる）
        
        Returns:
            "haiku" | "sonnet"
        
        例:
        1. Strategist のトレンド分析 → haiku
        2. Strategist の RAR-S 検証 → sonnet（金銭判定）
        3. Builder のテストケース生成 → haiku
        4. Builder の重大バグ判定 → sonnet（データロス可能性）
        5. Operator の定型 SNS 投稿 → haiku
        6. Operator のクレーム判定 → sonnet（炎上リスク）
        """
        
        # ===== クリティカル判定は必ず Sonnet =====
        if is_critical:
            return "sonnet"
        
        # ===== エージェント別の選択ロジック =====
        if agent == "strategist":
            return self._select_strategist(task_type, context)
        elif agent == "builder":
            return self._select_builder(task_type, context)
        elif agent == "operator":
            return self._select_operator(task_type, context)
        else:
            return "haiku"  # デフォルト
    
    def _select_strategist(self, task_type: str, context: Dict = None) -> str:
        """
        Strategist のモデル選択
        
        Haiku 推奨:
        - トレンド分析（キーワード抽出）
        - RAR-S 計算（CSV → JSON + log10）
        - Compliance Gate（キーワード判定）
        - 月次レポート出力（テンプレート）
        
        Sonnet 推奨:
        - RAR-S 検証（金銭判定、境界値）
        - 複雑な法務リスク判定
        - Conviction 登録の審査
        """
        
        task_lower = task_type.lower()
        context = context or {}
        
        # Sonnet が必要なケース
        sonnet_triggers = [
            "検証" in task_lower,
            "審査" in task_lower,
            "判定" in task_lower and "複雑" in task_lower,
            context.get("is_verification", False),
            context.get("financial_impact", False)
        ]
        
        if any(sonnet_triggers):
            return "sonnet"
        
        # デフォルト Haiku
        return "haiku"
    
    def _select_builder(self, task_type: str, context: Dict = None) -> str:
        """
        Builder のモデル選択
        
        Haiku 推奨:
        - テストケース生成
        - バグ報告からの原因特定（軽微）
        - コード整形・リファクタリング提案
        - デプロイスクリプト生成
        - 既知バグの修正手順
        
        Sonnet 推奨:
        - 致命的バグ判定（データロス可能性）
        - 法務リスクを伴うバグ（個人情報漏洩など）
        - セキュリティ脆弱性判定
        - 複雑な設計判断
        """
        
        task_lower = task_type.lower()
        context = context or {}
        
        # 重大度フラグ
        severity = context.get("severity", "LOW").upper()
        is_security = context.get("is_security", False)
        is_personal_data = context.get("involves_personal_data", False)
        
        # Sonnet が必要なケース
        sonnet_triggers = [
            severity in ["CRITICAL", "HIGH"],
            is_security,
            is_personal_data,
            "致命" in task_lower,
            "セキュリティ" in task_lower,
            "個人情報" in task_lower
        ]
        
        if any(sonnet_triggers):
            return "sonnet"
        
        # デフォルト Haiku
        return "haiku"
    
    def _select_operator(self, task_type: str, context: Dict = None) -> str:
        """
        Operator のモデル選択
        
        Haiku 推奨:
        - テンプレート化投稿（事前承認）
        - KPI 数値の文章化
        - SNS スケジューリング候補抽出
        - 日程調整
        
        Sonnet 推奨:
        - クレーム・炎上リスク判定
        - 創意工夫が必要な投稿
        - ブランド価値が大きい投稿
        - ユーザーの怒りレベル判定
        """
        
        task_lower = task_type.lower()
        context = context or {}
        
        # Sonnet が必要なケース
        sonnet_triggers = [
            "クレーム" in task_lower,
            "炎上" in task_lower,
            "判定" in task_lower,
            "創意" in task_lower,
            "ブランド" in task_lower,
            context.get("is_important_announcement", False),
            context.get("has_viral_risk", False),
            context.get("user_emotion", "NEUTRAL") in ["ANGRY", "URGENT"]
        ]
        
        if any(sonnet_triggers):
            return "sonnet"
        
        # デフォルト Haiku
        return "haiku"
    
    def get_model_info(self, model: str) -> Dict:
        """モデル情報を取得"""
        model_info = {
            "haiku": {
                "model_id": ModelType.HAIKU.value,
                "cost_per_million_input": 3,  # USD
                "cost_per_million_output": 15,  # USD
                "speed": "fastest",
                "capacity": "8k tokens",
                "use_case": "定型処理・軽微な判定",
                "monthly_allocation": "60%（1,810 円）"
            },
            "sonnet": {
                "model_id": ModelType.SONNET.value,
                "cost_per_million_input": 3,  # USD (Haiku と同価格)
                "cost_per_million_output": 15,  # USD (Haiku と同価格)
                "speed": "balanced",
                "capacity": "200k tokens",
                "use_case": "クリティカル判定・検証",
                "monthly_allocation": "40%（1,190 円）"
            },
            "opus": {
                "model_id": ModelType.OPUS.value,
                "cost_per_million_input": 15,  # USD
                "cost_per_million_output": 75,  # USD
                "speed": "slowest",
                "capacity": "200k tokens",
                "use_case": "禁止",
                "monthly_allocation": "0%（0 円）"
            }
        }
        
        return model_info.get(model, {})
    
    def log_usage(self, model: str, token_count: Dict):
        """モデル使用を記録"""
        if model == "haiku":
            self.monthly_consumption["haiku"] += token_count.get("total", 0)
        elif model == "sonnet":
            self.monthly_consumption["sonnet"] += token_count.get("total", 0)
        elif model == "opus":
            raise ValueError("❌ Opus は使用禁止です")
    
    def get_monthly_usage(self) -> Dict:
        """月次モデル使用統計"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "monthly_limit": self.monthly_limit,
            "haiku": {
                "allocation": self.haiku_budget,
                "used": self.monthly_consumption["haiku"],
                "remaining": self.haiku_budget - self.monthly_consumption["haiku"]
            },
            "sonnet": {
                "allocation": self.sonnet_budget,
                "used": self.monthly_consumption["sonnet"],
                "remaining": self.sonnet_budget - self.monthly_consumption["sonnet"]
            },
            "opus": {
                "status": "FORBIDDEN",
                "allocation": 0,
                "used": 0
            }
        }

# __init__.py
__all__ = ['ModelSelector', 'ModelType', 'TaskPriority']
