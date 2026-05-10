#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 0 自動セットアップスクリプト
- .env ファイルを作成
- API キーを設定
- Python 仮想環境を作成
- パッケージをインストール
- テストを実行
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header(text):
    """見出しを表示"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")

def print_step(step_num, text):
    """ステップを表示"""
    print(f"\n📍 Step {step_num}: {text}")
    print("-" * 60)

def create_env_file():
    """Step 1: .env ファイルを作成"""
    print_step(1, ".env ファイルを作成")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_example.exists():
        print("❌ エラー: .env.example が見つかりません")
        return False
    
    # .env をコピー
    shutil.copy(env_example, env_file)
    print(f"✅ .env ファイルを作成しました: {env_file}")
    return True

def setup_api_key():
    """Step 2: API キーを設定"""
    print_step(2, "Anthropic API キーを設定")
    
    api_key = input("🔑 Anthropic API キーを入力してください (sk-ant-v0-...): ").strip()
    
    if not api_key.startswith("sk-ant-v0-"):
        print("⚠️ 警告: キーが 'sk-ant-v0-' で始まっていません")
        confirm = input("続行しますか？ (y/n): ").strip().lower()
        if confirm != 'y':
            return False
    
    # .env を読み込み
    env_file = Path(".env")
    with open(env_file, 'r', encoding='utf-8') as f:
        env_content = f.read()
    
    # API キーを置き換え
    env_content = env_content.replace(
        "ANTHROPIC_API_KEY=your-api-key-here",
        f"ANTHROPIC_API_KEY={api_key}"
    )
    
    # .env に書き込み
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"✅ API キーを設定しました")
    print(f"   キー: {api_key[:20]}...")
    return True

def create_venv():
    """Step 3: 仮想環境を作成"""
    print_step(3, "Python 仮想環境を作成")
    
    venv_path = Path("venv")
    
    if venv_path.exists():
        print(f"⚠️ 仮想環境がすでに存在します: {venv_path}")
        return True
    
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", "venv"],
            check=True
        )
        print(f"✅ 仮想環境を作成しました: {venv_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ エラー: 仮想環境の作成に失敗しました")
        print(f"   詳細: {e}")
        return False

def install_requirements():
    """Step 4: パッケージをインストール"""
    print_step(4, "依存パッケージをインストール")
    
    requirements_file = Path("requirements.txt")
    
    if not requirements_file.exists():
        print("❌ エラー: requirements.txt が見つかりません")
        return False
    
    # 仮想環境のpipパスを取得
    if sys.platform == "win32":
        pip_path = Path("venv/Scripts/pip.exe")
    else:
        pip_path = Path("venv/bin/pip")
    
    try:
        subprocess.run(
            [str(pip_path), "install", "-r", "requirements.txt"],
            check=True
        )
        print("✅ パッケージをインストールしました")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ エラー: パッケージのインストールに失敗しました")
        print(f"   詳細: {e}")
        return False

def run_tests():
    """Step 5: テストを実行"""
    print_step(5, "テストを実行")
    
    tests = [
        "tests/test_budget.py",
        "tests/test_delegation.py",
        "tests/test_model_selector.py"
    ]
    
    # 仮想環境のpythonパスを取得
    if sys.platform == "win32":
        python_path = Path("venv/Scripts/python.exe")
    else:
        python_path = Path("venv/bin/python")
    
    all_passed = True
    
    for test_file in tests:
        test_path = Path(test_file)
        if not test_path.exists():
            print(f"⚠️ テストファイルが見つかりません: {test_file}")
            continue
        
        print(f"\n📝 実行中: {test_file}")
        try:
            subprocess.run(
                [str(python_path), test_file],
                check=True
            )
            print(f"✅ PASS: {test_file}")
        except subprocess.CalledProcessError:
            print(f"❌ FAIL: {test_file}")
            all_passed = False
    
    return all_passed

def main():
    """メイン処理"""
    print_header("Phase 0 自動セットアップスクリプト")
    print("このスクリプトは以下を自動で実行します：")
    print("  1. .env ファイルを作成")
    print("  2. API キーを設定")
    print("  3. 仮想環境を作成")
    print("  4. パッケージをインストール")
    print("  5. テストを実行")
    
    # 確認
    confirm = input("\n続行しますか？ (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ キャンセルしました")
        sys.exit(1)
    
    # 実行
    try:
        # Step 1
        if not create_env_file():
            sys.exit(1)
        
        # Step 2
        if not setup_api_key():
            sys.exit(1)
        
        # Step 3
        if not create_venv():
            sys.exit(1)
        
        # Step 4
        if not install_requirements():
            sys.exit(1)
        
        # Step 5
        if run_tests():
            print_header("🎉 Phase 0 セットアップ完了！")
            print("すべてのテストに PASS しました！")
            print("\n次のステップ:")
            print("  - LINE 通知設定（オプション）")
            print("  - Phase 1（DelegationThreshold 完全統合）")
        else:
            print_header("⚠️ テストに失敗しました")
            print("詳細を確認して、もう一度実行してください")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n❌ キャンセルしました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()