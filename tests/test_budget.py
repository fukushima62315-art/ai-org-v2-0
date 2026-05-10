# tests/test_budget.py
# 予算管理エンジンのテスト

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.budget.budget_manager import BudgetManager, BudgetStatus

def clear_logs():
    """ログファイルをクリア"""
    log_path = Path("src/logs/budget.log")
    if log_path.exists():
        log_path.unlink()

def test_budget_normal():
    """✅ 通常運用テスト（0-50%）"""
    clear_logs()
    manager = BudgetManager({
        "monthly_budget_jpy": 3000,
        "strategist_budget": 800,
        "builder_budget": 1500,
        "operator_budget": 500,
        "reserve_budget": 200,
        "warning_threshold_percent": 50,
        "caution_threshold_percent": 70,
        "emergency_threshold_percent": 80
    })
    
    manager.log_consumption("builder", 500, "MVP development")
    status = manager.get_budget_status()
    assert round(status["consumed_jpy"], 1) == 500
    assert status["status"] == BudgetStatus.NORMAL.value
    print("✅ PASS: 通常運用（50% 以下）")

def test_budget_warning_50():
    """⚠️ 警告（50%）テスト"""
    clear_logs()
    manager = BudgetManager({
        "monthly_budget_jpy": 3000,
        "strategist_budget": 800,
        "builder_budget": 1500,
        "operator_budget": 500,
        "reserve_budget": 200,
        "warning_threshold_percent": 50,
        "caution_threshold_percent": 70,
        "emergency_threshold_percent": 80
    })
    
    manager.log_consumption("builder", 1500, "Development work")
    status = manager.get_budget_status()
    assert round(status["consumed_jpy"], 1) == 1500
    assert status["status"] == BudgetStatus.WARNING_50.value
    print("✅ PASS: 警告（50%）")

def test_budget_emergency_80():
    """🔴 危機（80%）テスト"""
    clear_logs()
    manager = BudgetManager({
        "monthly_budget_jpy": 3000,
        "strategist_budget": 800,
        "builder_budget": 1500,
        "operator_budget": 500,
        "reserve_budget": 200,
        "warning_threshold_percent": 50,
        "caution_threshold_percent": 70,
        "emergency_threshold_percent": 80
    })
    
    manager.log_consumption("builder", 2400, "Large task")
    status = manager.get_budget_status()
    assert round(status["consumed_jpy"], 1) == 2400
    assert status["status"] == BudgetStatus.EMERGENCY_80.value
    
    escalation = manager.check_and_escalate()
    assert escalation is not None
    assert escalation["alert_type"] == "BUDGET_80_PERCENT"
    print("✅ PASS: 危機（80%）エスカレーション")

if __name__ == "__main__":
    print("\n🧪 Budget Manager Tests\n")
    test_budget_normal()
    test_budget_warning_50()
    test_budget_emergency_80()
    print("\n🎉 All budget tests passed!\n")
