# tests/test_model_selector.py
# モデル選択戦略のテスト

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import ModelSelector

def test_strategist_haiku_default():
    """Strategist: トレンド分析は Haiku"""
    selector = ModelSelector()
    
    model = selector.select_model(
        agent="strategist",
        task_type="トレンド分析スキャン"
    )
    
    assert model == "haiku"
    print("✅ PASS: Strategist トレンド分析 → Haiku")

def test_strategist_sonnet_verification():
    """Strategist: RAR-S 検証は Sonnet（金銭判定）"""
    selector = ModelSelector()
    
    model = selector.select_model(
        agent="strategist",
        task_type="RAR-S スコア検証",
        context={"financial_impact": True}
    )
    
    assert model == "sonnet"
    print("✅ PASS: Strategist RAR-S 検証 → Sonnet")

def test_builder_haiku_default():
    """Builder: テストケース生成は Haiku"""
    selector = ModelSelector()
    
    model = selector.select_model(
        agent="builder",
        task_type="テストケース生成"
    )
    
    assert model == "haiku"
    print("✅ PASS: Builder テストケース生成 → Haiku")

def test_builder_sonnet_critical():
    """Builder: 致命的バグは Sonnet"""
    selector = ModelSelector()
    
    model = selector.select_model(
        agent="builder",
        task_type="バグ判定",
        context={"severity": "CRITICAL", "involves_personal_data": True}
    )
    
    assert model == "sonnet"
    print("✅ PASS: Builder 致命的バグ → Sonnet")

def test_operator_haiku_default():
    """Operator: 定型投稿は Haiku"""
    selector = ModelSelector()
    
    model = selector.select_model(
        agent="operator",
        task_type="テンプレート化投稿"
    )
    
    assert model == "haiku"
    print("✅ PASS: Operator テンプレート投稿 → Haiku")

def test_operator_sonnet_critical():
    """Operator: クレーム判定は Sonnet"""
    selector = ModelSelector()
    
    model = selector.select_model(
        agent="operator",
        task_type="クレーム対応",
        context={"has_viral_risk": True}
    )
    
    assert model == "sonnet"
    print("✅ PASS: Operator クレーム判定 → Sonnet")

def test_critical_override():
    """is_critical=True なら必ず Sonnet"""
    selector = ModelSelector()
    
    model = selector.select_model(
        agent="strategist",
        task_type="軽微なタスク",
        is_critical=True
    )
    
    assert model == "sonnet"
    print("✅ PASS: is_critical=True → 必ず Sonnet")

def test_model_info():
    """モデル情報取得"""
    selector = ModelSelector()
    
    haiku_info = selector.get_model_info("haiku")
    sonnet_info = selector.get_model_info("sonnet")
    opus_info = selector.get_model_info("opus")
    
    assert haiku_info["model_id"] == "claude-3-5-haiku-20241022"
    assert sonnet_info["model_id"] == "claude-sonnet-4-20250514"
    assert opus_info["use_case"] == "禁止"
    print("✅ PASS: モデル情報取得")

def test_monthly_usage():
    """月次使用統計"""
    selector = ModelSelector()
    
    selector.log_usage("haiku", {"total": 10000})
    selector.log_usage("sonnet", {"total": 5000})
    
    usage = selector.get_monthly_usage()
    
    assert usage["haiku"]["used"] == 10000
    assert usage["sonnet"]["used"] == 5000
    assert "remaining" in usage["haiku"]
    print("✅ PASS: 月次使用統計")

def test_opus_forbidden():
    """Opus は禁止"""
    selector = ModelSelector()
    
    try:
        selector.log_usage("opus", {"total": 1000})
        assert False, "Opus を使用すべきでない"
    except ValueError as e:
        assert "禁止" in str(e)
        print("✅ PASS: Opus 禁止（エラー発生）")

if __name__ == "__main__":
    print("\n🧪 Model Selector Tests\n")
    test_strategist_haiku_default()
    test_strategist_sonnet_verification()
    test_builder_haiku_default()
    test_builder_sonnet_critical()
    test_operator_haiku_default()
    test_operator_sonnet_critical()
    test_critical_override()
    test_model_info()
    test_monthly_usage()
    test_opus_forbidden()
    print("\n🎉 All model selector tests passed!\n")
