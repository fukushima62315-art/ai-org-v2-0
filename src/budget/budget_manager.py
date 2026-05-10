# src/budget/budget_manager.py
# v2.0 月次予算管理と 80% 警告システム

import json
from datetime import datetime
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional
from config import Config

class BudgetStatus(Enum):
    NORMAL = "NORMAL"
    WARNING_50 = "WARNING_50"
    CAUTION_70 = "CAUTION_70"
    EMERGENCY_80 = "EMERGENCY_80"
    STOPPED_100 = "STOPPED_100"

class BudgetManager:
    """
    月次予算管理
    - 50% で警告
    - 70% で注意
    - 80% でユーザー判定（追課金 or 制限 or 停止）
    - 100% で自動停止
    """
    
    def __init__(self, config=None):
        if config is None:
            config = Config
        
        # config が辞書か オブジェクトか判定
        if isinstance(config, dict):
            self.monthly_limit = config.get("monthly_budget_jpy", Config.MONTHLY_BUDGET_JPY)
            warning_pct = config.get("warning_threshold_percent", Config.WARNING_THRESHOLD_PERCENT)
            caution_pct = config.get("caution_threshold_percent", Config.CAUTION_THRESHOLD_PERCENT)
            emergency_pct = config.get("emergency_threshold_percent", Config.EMERGENCY_THRESHOLD_PERCENT)
            
            self.agent_budgets = {
                "strategist": config.get("strategist_budget", Config.STRATEGIST_BUDGET),
                "builder": config.get("builder_budget", Config.BUILDER_BUDGET),
                "operator": config.get("operator_budget", Config.OPERATOR_BUDGET),
                "reserve": config.get("reserve_budget", Config.RESERVE_BUDGET)
            }
        else:
            self.monthly_limit = config.MONTHLY_BUDGET_JPY
            warning_pct = config.WARNING_THRESHOLD_PERCENT
            caution_pct = config.CAUTION_THRESHOLD_PERCENT
            emergency_pct = config.EMERGENCY_THRESHOLD_PERCENT
            
            self.agent_budgets = {
                "strategist": config.STRATEGIST_BUDGET,
                "builder": config.BUILDER_BUDGET,
                "operator": config.OPERATOR_BUDGET,
                "reserve": config.RESERVE_BUDGET
            }
        
        self.warning_threshold = self.monthly_limit * (warning_pct / 100)
        self.caution_threshold = self.monthly_limit * (caution_pct / 100)
        self.emergency_threshold = self.monthly_limit * (emergency_pct / 100)
        
        self.log_path = Path(config.get("budget_log_path", Config.BUDGET_LOG_PATH) if isinstance(config, dict) else config.BUDGET_LOG_PATH)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.current_month = None
        self.monthly_consumption = {}  # {YYYY-MM: {agent: cost}}
        self._load_history()
    
    def _load_history(self):
        """ログから過去の消費履歴を読み込む"""
        if not self.log_path.exists():
            return
        
        with open(self.log_path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    month = entry.get("month")
                    agent = entry.get("agent")
                    cost = entry.get("cost_jpy", 0)
                    
                    if month not in self.monthly_consumption:
                        self.monthly_consumption[month] = {}
                    
                    if agent not in self.monthly_consumption[month]:
                        self.monthly_consumption[month][agent] = 0
                    
                    self.monthly_consumption[month][agent] += cost
                except json.JSONDecodeError:
                    continue
    
    def get_current_month_key(self) -> str:
        """現在の年月（YYYY-MM）を取得"""
        return datetime.utcnow().strftime("%Y-%m")
    
    def log_consumption(self, agent: str, cost_jpy: float, description: str = ""):
        """エージェントのコスト消費を記録"""
        month_key = self.get_current_month_key()
        
        if month_key not in self.monthly_consumption:
            self.monthly_consumption[month_key] = {}
        
        if agent not in self.monthly_consumption[month_key]:
            self.monthly_consumption[month_key][agent] = 0
        
        self.monthly_consumption[month_key][agent] += cost_jpy
        
        # ログに記録
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "month": month_key,
            "agent": agent,
            "cost_jpy": cost_jpy,
            "description": description,
            "cumulative_jpy": self.get_monthly_total(month_key)
        }
        
        self._append_to_log(entry)
    
    def get_monthly_total(self, month_key: Optional[str] = None) -> float:
        """指定月の合計消費額を取得"""
        if month_key is None:
            month_key = self.get_current_month_key()
        
        if month_key not in self.monthly_consumption:
            return 0
        
        return sum(self.monthly_consumption[month_key].values())
    
    def get_budget_status(self) -> Dict:
        """現在の予算ステータスを取得"""
        month_key = self.get_current_month_key()
        total_consumed = self.get_monthly_total(month_key)
        percentage = (total_consumed / self.monthly_limit) * 100
        
        # ステータス判定
        if total_consumed >= self.monthly_limit:
            status = BudgetStatus.STOPPED_100
        elif total_consumed >= self.emergency_threshold:
            status = BudgetStatus.EMERGENCY_80
        elif total_consumed >= self.caution_threshold:
            status = BudgetStatus.CAUTION_70
        elif total_consumed >= self.warning_threshold:
            status = BudgetStatus.WARNING_50
        else:
            status = BudgetStatus.NORMAL
        
        return {
            "month": month_key,
            "monthly_limit": self.monthly_limit,
            "consumed_jpy": round(total_consumed, 1),
            "remaining_jpy": round(self.monthly_limit - total_consumed, 1),
            "percentage": round(percentage, 1),
            "status": status.value,
            "by_agent": self.monthly_consumption.get(month_key, {}),
            "thresholds": {
                "warning_50": self.warning_threshold,
                "caution_70": self.caution_threshold,
                "emergency_80": self.emergency_threshold
            }
        }
    
    def check_and_escalate(self) -> Optional[Dict]:
        """
        予算ステータスをチェックし、
        エスカレーションが必要な場合に提案を返す
        """
        status = self.get_budget_status()
        
        if status["status"] == BudgetStatus.EMERGENCY_80.value:
            return self._create_80_percent_escalation(status)
        elif status["status"] == BudgetStatus.STOPPED_100.value:
            return self._create_100_percent_stop()
        
        return None
    
    def _create_80_percent_escalation(self, status: Dict) -> Dict:
        """
        80% 到達時のエスカレーション提案
        「追課金額 + プロジェクト見込み」を提示
        """
        consumed = status["consumed_jpy"]
        remaining_in_current = status["remaining_jpy"]
        
        return {
            "escalation_level": "A_HARD_STOP",
            "timestamp": datetime.utcnow().isoformat(),
            "alert_type": "BUDGET_80_PERCENT",
            "message": "🔴 Claude API 予算が 80% に到達しました。追加課金の要否を判定してください。",
            
            "current_status": {
                "consumed_jpy": consumed,
                "remaining_jpy": remaining_in_current,
                "percentage": status["percentage"],
                "monthly_limit": status["monthly_limit"]
            },
            
            "by_agent": status["by_agent"],
            
            "user_decision_request": {
                "primary_question": "以下のいずれかを選択してください",
                "options": [
                    {
                        "id": "approve_additional_budget",
                        "label": "追加課金を承認",
                        "requires_input": "追加予算額（円）",
                        "impact": "予算を増額して継続運用"
                    },
                    {
                        "id": "restrict_operations",
                        "label": "制限モードで継続",
                        "impact": "出力機能を制限、月末まで待機"
                    },
                    {
                        "id": "pause_until_next_month",
                        "label": "月末まで停止",
                        "impact": "全エージェント停止、次月 1 日に自動リセット"
                    }
                ],
                "current_projects": "進行中プロジェクトと完成までの推定追加コストを入力してください"
            },
            
            "recommendation": {
                "text": "進行中プロジェクトの優先度と見込み利益を確認し、追加課金の必要性を判定してください",
                "template": """
【プロジェクト判定用テンプレート】

プロジェクト名: 
状態: （開発中/テスト中/リリース待機）
完成までの推定追加コスト: _____ 円
完成後の見込み:
  - ユーザー数: 
  - 月次売上: 
  - リスク: （法務/競合/その他）

判定: （価値あり/様子見/中止）
        """
            }
        }
    
    def _create_100_percent_stop(self) -> Dict:
        """100% 到達時は自動停止"""
        return {
            "escalation_level": "A_HARD_STOP",
            "timestamp": datetime.utcnow().isoformat(),
            "alert_type": "BUDGET_LIMIT_REACHED",
            "status": "FROZEN",
            "message": "⛔ Claude API 予算上限に到達。全エージェント停止中です。",
            "next_action": f"{self.get_current_month_key()}-01 00:00 JST に自動リセット",
            "what_still_works": [
                "GitHub/Git 操作",
                "Supabase（無料枠）",
                "ローカルテスト"
            ]
        }
    
    def _append_to_log(self, entry: Dict):
        """ログファイルに追記"""
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def monthly_report(self) -> Dict:
        """月次財務レポートを生成"""
        month_key = self.get_current_month_key()
        status = self.get_budget_status()
        
        return {
            "report_period": month_key,
            "budget": {
                "limit": self.monthly_limit,
                "consumed": status["consumed_jpy"],
                "remaining": status["remaining_jpy"],
                "percentage": status["percentage"]
            },
            "by_agent": {
                agent: {
                    "allocated": self.agent_budgets[agent],
                    "used": status["by_agent"].get(agent, 0),
                    "remaining": self.agent_budgets[agent] - status["by_agent"].get(agent, 0),
                    "usage_percent": round(
                        (status["by_agent"].get(agent, 0) / self.agent_budgets[agent] * 100)
                        if self.agent_budgets[agent] > 0 else 0,
                        1
                    )
                }
                for agent in self.agent_budgets
            },
            "status": status["status"],
            "escalation_needed": status["status"] in [
                BudgetStatus.WARNING_50.value,
                BudgetStatus.CAUTION_70.value,
                BudgetStatus.EMERGENCY_80.value,
                BudgetStatus.STOPPED_100.value
            ]
        }

# __init__.py
__all__ = ['BudgetManager', 'BudgetStatus']
