import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path if env_path.exists() else None)
except ImportError:
    pass

class Config:
    ANTHROPIC_API_KEY            = os.getenv("ANTHROPIC_API_KEY", "")
    MONTHLY_BUDGET_JPY           = int(os.getenv("MONTHLY_BUDGET_JPY", 3000))
    WARNING_THRESHOLD_PERCENT    = int(os.getenv("WARNING_THRESHOLD_PERCENT", 50))
    CAUTION_THRESHOLD_PERCENT    = int(os.getenv("CAUTION_THRESHOLD_PERCENT", 70))
    EMERGENCY_THRESHOLD_PERCENT  = int(os.getenv("EMERGENCY_THRESHOLD_PERCENT", 80))
    STRATEGIST_BUDGET            = int(os.getenv("STRATEGIST_BUDGET", 800))
    BUILDER_BUDGET               = int(os.getenv("BUILDER_BUDGET", 1500))
    OPERATOR_BUDGET              = int(os.getenv("OPERATOR_BUDGET", 500))
    RESERVE_BUDGET               = int(os.getenv("RESERVE_BUDGET", 200))
    LINE_CHANNEL_ACCESS_TOKEN    = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    LINE_USER_ID                 = os.getenv("LINE_USER_ID", "")
    FIREBASE_DB_URL              = os.getenv("FIREBASE_DB_URL", "")
    FIREBASE_AUTH_TOKEN          = os.getenv("FIREBASE_AUTH_TOKEN", "")
    AUDIT_LOG_PATH               = os.getenv("AUDIT_LOG_PATH", "src/logs/audit.log")

config = Config()
