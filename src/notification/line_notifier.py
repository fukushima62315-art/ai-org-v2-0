# src/notification/line_notifier.py
# LINE Messaging API を使用した通知

import os
import json
import requests
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

class LineNotifier:
    """
    LINE Messaging API を使用してユーザーに通知
    """
    
    def __init__(self, channel_token: str = "", user_id: str = ""):
        self.channel_token = channel_token or os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        self.user_id = user_id or os.getenv("LINE_USER_ID", "")
        self.api_url = "https://api.line.biz/v2/bot/message/push"
        self.is_enabled = bool(self.channel_token and self.user_id)
    
    def send_escalation_a(self, escalation_data: Dict) -> bool:
        """
        階層 A エスカレーション通知を LINE で送信
        """
        if not self.is_enabled:
            self._log_notification(escalation_data, "SKIPPED")
            return False
        
        message_text = self._format_escalation_a(escalation_data)
        return self._send_message(message_text)
    
    def send_budget_alert(self, budget_status: Dict) -> bool:
        """
        予算警告を LINE で送信
        """
        if not self.is_enabled:
            return False
        
        if budget_status["status"] == "NORMAL":
            return False  # 通常運用は通知しない
        
        message_text = self._format_budget_alert(budget_status)
        return self._send_message(message_text)
    
    def send_80_percent_proposal(self, escalation_data: Dict) -> bool:
        """
        80% 到達時の追課金提案を LINE で送信
        """
        if not self.is_enabled:
            self._log_notification(escalation_data, "SKIPPED")
            return False
        
        message_text = self._format_80_percent_proposal(escalation_data)
        return self._send_message(message_text)
    
    def send_completion_notice(self, message: str) -> bool:
        """汎用メッセージ送信"""
        if not self.is_enabled:
            return False
        
        return self._send_message(message)
    
    def _format_escalation_a(self, data: Dict) -> str:
        """階層 A 通知をテキストに整形"""
        return f"""
🚨 【階層 A】意思決定が必要です

{data.get('trigger_reason', '意思決定が必要な案件が発生しました')}

【詳細】
{self._format_context(data.get('context', {}))}

【ユーザーへの質問】
{data.get('decision_request', {}).get('primary_question', '')}

【推奨】
{data.get('ceo_recommendation', {}).get('preferred_action', '')}

⏰ 期限: {data.get('decision_request', {}).get('deadline', '指定なし')}

返信待機中...
        """.strip()
    
    def _format_budget_alert(self, status: Dict) -> str:
        """予算警告をテキストに整形"""
        status_names = {
            "WARNING_50": "⚠️ 警告（50%）",
            "CAUTION_70": "🟠 注意（70%）",
            "EMERGENCY_80": "🔴 危機（80%）",
            "STOPPED_100": "⛔ 停止（100%）"
        }
        
        message = f"""
{status_names.get(status['status'], status['status'])}

【予算状況】
月次上限: {status['monthly_limit']:,} 円
消費済み: {status['consumed_jpy']:,} 円 ({status['percentage']}%)
残額: {status['monthly_limit'] - status['consumed_jpy']:,} 円

【エージェント別】
"""
        for agent, cost in status.get('by_agent', {}).items():
            message += f"{agent}: {cost:,} 円\n"
        
        message += "\n詳細は Web ポータルで確認してください"
        
        return message.strip()
    
    def _format_80_percent_proposal(self, escalation_data: Dict) -> str:
        """80% 追課金提案をテキストに整形"""
        return f"""
🔴 【予算 80% 到達】追加課金の要否を判定してください

【現状】
消費額: {escalation_data['current_status']['consumed_jpy']:,} 円
残額: {escalation_data['current_status']['remaining_jpy']:,} 円
進捗: {escalation_data['current_status']['percentage']}%

【ユーザー決定】以下のいずれかを選択:

1️⃣ 追加課金を承認 → 追加予算額を回答
2️⃣ 制限モードで継続 → 出力機能を制限
3️⃣ 月末まで停止 → 全エージェント停止

進行中プロジェクトと見込み利益を確認の上、判定ください。
        """.strip()
    
    def _format_context(self, context: Dict) -> str:
        """コンテキストをフォーマット"""
        lines = []
        for key, value in context.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"{key}: {value}")
        
        return "\n".join(lines) if lines else "詳細情報なし"
    
    def _send_message(self, message_text: str) -> bool:
        """LINE API でメッセージを送信"""
        if not self.is_enabled:
            return False
        
        headers = {
            "Authorization": f"Bearer {self.channel_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "to": self.user_id,
            "messages": [
                {
                    "type": "text",
                    "text": message_text
                }
            ]
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self._log_notification({"message": message_text}, "SENT")
                return True
            else:
                self._log_notification(
                    {"message": message_text, "error": response.text},
                    "FAILED"
                )
                print(f"❌ LINE API Error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self._log_notification(
                {"message": message_text, "error": str(e)},
                "ERROR"
            )
            print(f"❌ LINE Notification Error: {e}")
            return False
    
    def _log_notification(self, data: Dict, status: str):
        """通知ログを記録"""
        log_path = Path("src/logs/notifications.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "enabled": self.is_enabled,
            "data": data
        }
        
        with open(log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# __init__.py
__all__ = ['LineNotifier']
