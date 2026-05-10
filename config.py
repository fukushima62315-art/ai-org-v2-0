# config.py
# v2.0 組織設計の設定ファイル

import os
from dotenv import load_dotenv
from pathlib import Path

# .env ファイルを読み込む
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

class Config:
    # Claude API
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")
    
    # Budget Management
    MONTHLY_BUDGET_JPY = int(os.getenv("MONTHLY_BUDGET_JPY", 3000))
    WARNING_THRESHOLD_PERCENT = int(os.getenv("WARNING_THRESHOLD_PERCENT", 50))
    CAUTION_THRESHOLD_PERCENT = int(os.getenv("CAUTION_THRESHOLD_PERCENT", 70))
    EMERGENCY_THRESHOLD_PERCENT = int(os.getenv("EMERGENCY_THRESHOLD_PERCENT", 80))
    
    # Agent Budget Allocation
    STRATEGIST_BUDGET = int(os.getenv("STRATEGIST_BUDGET", 800))
    BUILDER_BUDGET = int(os.getenv("BUILDER_BUDGET", 1500))
    OPERATOR_BUDGET = int(os.getenv("OPERATOR_BUDGET", 500))
    RESERVE_BUDGET = int(os.getenv("RESERVE_BUDGET", 200))
    
    # LINE Notification
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    LINE_USER_ID = os.getenv("LINE_USER_ID", "")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "src/logs/audit.log")
    BUDGET_LOG_PATH = os.getenv("BUDGET_LOG_PATH", "src/logs/budget.log")
    
    @classmethod
    def validate(cls):
        """設定値の検証"""
        issues = []
        
        if not cls.ANTHROPIC_API_KEY:
            issues.append("❌ ANTHROPIC_API_KEY が設定されていません")
        
        if not cls.LINE_CHANNEL_ACCESS_TOKEN:
            issues.append("⚠️ LINE_CHANNEL_ACCESS_TOKEN が設定されていません（通知機能は無効）")
        
        if not cls.LINE_USER_ID:
            issues.append("⚠️ LINE_USER_ID が設定されていません（通知機能は無効）")
        
        if cls.MONTHLY_BUDGET_JPY < 1000:
            issues.append("⚠️ MONTHLY_BUDGET_JPY が 1,000 円未満です")
        
        return issues

config = Config()
