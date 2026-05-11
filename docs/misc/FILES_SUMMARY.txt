#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 0 完全自動化スクリプト — Claude Code 対応版

【処理内容】
1. 現在の環境確認（Windows PowerShell セキュリティ対応）
2. .env ファイル作成・API キー設定
3. 仮想環境作成
4. パッケージインストール（anthropic, python-dotenv, jsonschema など）
5. 3 つのテスト実行（予算管理・階層判定・モデル選択）
6. 最終レポート生成

【使用方法】
python phase0_automation.py

【セキュリティ】
- Windows PowerShell ExecutionPolicy に対応
- 管理者権限不要（スクリプト実行のみ）
"""

import os
import sys
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# ============================================================================
# ユーティリティ関数
# ============================================================================

class Colors:
    """ターミナルカラー"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    """大きな見出しを表示"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("=" * 70)
    print(f"  {text}")
    print("=" * 70)
    print(Colors.END)

def print_step(step_num: int, text: str):
    """ステップを表示"""
    print(f"\n{Colors.CYAN}📍 Step {step_num}: {text}{Colors.END}")
    print("-" * 70)

def print_success(text: str):
    """成功メッセージ"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str):
    """エラーメッセージ"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text: str):
    """警告メッセージ"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text: str):
    """情報メッセージ"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

# ============================================================================
# Phase 0 実装クラス
# ============================================================================

class Phase0Automation:
    """Phase 0 完全自動化"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.venv_path = self.project_root / "venv"
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "steps_completed": [],
            "tests_passed": [],
            "tests_failed": [],
            "warnings": [],
            "errors": []
        }
    
    def run(self):
        """メイン実行フロー"""
        try:
            print_header("Phase 0 完全自動化スクリプト")
            print("このスクリプトは以下を自動実行します：")
            print("  ✓ .env ファイル作成・API キー設定")
            print("  ✓ Python 仮想環境作成")
            print("  ✓ パッケージインストール")
            print("  ✓ テスト実行（3 種類）")
            print("  ✓ 最終レポート生成")
            
            # 環境確認
            self.step_check_environment()
            
            # .env 設定
            self.step_setup_env()
            
            # 仮想環境
            self.step_create_venv()
            
            # パッケージインストール
            self.step_install_packages()
            
            # テスト実行
            self.step_run_tests()
            
            # 最終レポート
            self.step_final_report()
            
        except KeyboardInterrupt:
            print_error("\nユーザーがキャンセルしました")
            sys.exit(1)
        except Exception as e:
            print_error(f"予期しないエラー: {e}")
            sys.exit(1)
    
    # ========================================================================
    # Step 1: 環境確認
    # ========================================================================
    
    def step_check_environment(self):
        """環境確認"""
        print_step(1, "環境確認")
        
        # Python バージョン
        python_version = sys.version.split()[0]
        print_info(f"Python バージョン: {python_version}")
        
        # プロジェクトディレクトリ
        print_info(f"プロジェクトディレクトリ: {self.project_root}")
        
        # 必須ファイル確認
        required_files = [".env.example", "config.py", "requirements.txt"]
        for file in required_files:
            if (self.project_root / file).exists():
                print_success(f"ファイル存在: {file}")
            else:
                print_error(f"ファイル未検出: {file}")
                raise FileNotFoundError(f"{file} が見つかりません")
        
        # 必須フォルダ確認
        required_dirs = ["src", "tests"]
        for dir_name in required_dirs:
            if (self.project_root / dir_name).exists():
                print_success(f"フォルダ存在: {dir_name}/")
            else:
                print_error(f"フォルダ未検出: {dir_name}/")
                raise FileNotFoundError(f"{dir_name}/ が見つかりません")
        
        self.results["steps_completed"].append("環境確認")
    
    # ========================================================================
    # Step 2: .env 設定
    # ========================================================================
    
    def step_setup_env(self):
        """Step 2: .env ファイルをセットアップ"""
        print_step(2, ".env ファイル設定")
        
        # .env.example コピー
        if not self.env_example.exists():
            print_error(f"{self.env_example} が見つかりません")
            raise FileNotFoundError(f".env.example")
        
        shutil.copy(self.env_example, self.env_file)
        print_success(f".env ファイルを作成: {self.env_file}")
        
        # API キー入力
        print_info("Anthropic API キーを入力してください")
        api_key = input("🔑 API キー (sk-ant-v0-...): ").strip()
        
        # バリデーション
        if not api_key.startswith("sk-ant-v0-"):
            print_warning("キーが 'sk-ant-v0-' で始まっていません")
            confirm = input("続行しますか？ (y/n): ").strip().lower()
            if confirm != 'y':
                print_error("セットアップをキャンセルしました")
                sys.exit(1)
        
        # .env ファイル更新
        with open(self.env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        env_content = env_content.replace(
            "ANTHROPIC_API_KEY=your-api-key-here",
            f"ANTHROPIC_API_KEY={api_key}"
        )
        
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print_success(f"API キーを設定しました")
        print_info(f"キー: {api_key[:20]}...")
        self.results["steps_completed"].append(".env 設定")
    
    # ========================================================================
    # Step 3: 仮想環境作成
    # ========================================================================
    
    def step_create_venv(self):
        """Step 3: 仮想環境を作成"""
        print_step(3, "Python 仮想環境作成")
        
        if self.venv_path.exists():
            print_warning(f"仮想環境がすでに存在します: {self.venv_path}")
            confirm = input("再作成しますか？ (y/n): ").strip().lower()
            if confirm == 'y':
                shutil.rmtree(self.venv_path)
                print_info("既存の仮想環境を削除しました")
            else:
                print_info("既存の仮想環境を使用します")
                self.results["steps_completed"].append("仮想環境作成")
                return
        
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(self.venv_path)],
                check=True,
                capture_output=True
            )
            print_success(f"仮想環境を作成しました: {self.venv_path}")
            self.results["steps_completed"].append("仮想環境作成")
        except subprocess.CalledProcessError as e:
            print_error(f"仮想環境の作成に失敗しました: {e}")
            raise
    
    # ========================================================================
    # Step 4: パッケージインストール
    # ========================================================================
    
    def step_install_packages(self):
        """Step 4: パッケージをインストール"""
        print_step(4, "依存パッケージインストール")
        
        # pip パスを取得
        if sys.platform == "win32":
            pip_exe = self.venv_path / "Scripts" / "pip.exe"
        else:
            pip_exe = self.venv_path / "bin" / "pip"
        
        if not pip_exe.exists():
            print_error(f"pip が見つかりません: {pip_exe}")
            raise FileNotFoundError("pip")
        
        # requirements.txt から読み込み
        requirements_file = self.project_root / "requirements.txt"
        if not requirements_file.exists():
            print_error(f"{requirements_file} が見つかりません")
            raise FileNotFoundError("requirements.txt")
        
        # インストール実行
        print_info("パッケージをインストール中...")
        try:
            result = subprocess.run(
                [str(pip_exe), "install", "-r", str(requirements_file)],
                capture_output=True,
                text=True,
                timeout=300  # 5 分タイムアウト
            )
            
            if result.returncode == 0:
                print_success("パッケージをインストールしました")
                # インストール済みパッケージを確認
                packages = self._get_installed_packages(pip_exe)
                for pkg in ["anthropic", "python-dotenv", "jsonschema", "requests", "pydantic"]:
                    if pkg in packages:
                        print_success(f"  ✓ {pkg}")
                    else:
                        print_warning(f"  ? {pkg}")
                self.results["steps_completed"].append("パッケージインストール")
            else:
                print_error(f"インストール失敗: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, "pip install")
        
        except subprocess.TimeoutExpired:
            print_error("インストールがタイムアウトしました（5 分以上）")
            raise
        except Exception as e:
            print_error(f"パッケージインストール中にエラー: {e}")
            raise
    
    def _get_installed_packages(self, pip_exe: Path) -> List[str]:
        """インストール済みパッケージを取得"""
        try:
            result = subprocess.run(
                [str(pip_exe), "list"],
                capture_output=True,
                text=True
            )
            packages = [line.split()[0].lower() for line in result.stdout.split('\n')[2:] if line.strip()]
            return packages
        except:
            return []
    
    # ========================================================================
    # Step 5: テスト実行
    # ========================================================================
    
    def step_run_tests(self):
        """Step 5: テストを実行"""
        print_step(5, "テスト実行")
        
        # Python パスを取得
        if sys.platform == "win32":
            python_exe = self.venv_path / "Scripts" / "python.exe"
        else:
            python_exe = self.venv_path / "bin" / "python"
        
        if not python_exe.exists():
            print_error(f"python が見つかりません: {python_exe}")
            raise FileNotFoundError("python")
        
        tests = [
            ("テスト 1: 予算管理", "tests/test_budget.py"),
            ("テスト 2: 階層判定", "tests/test_delegation.py"),
            ("テスト 3: モデル選択", "tests/test_model_selector.py")
        ]
        
        for test_name, test_file in tests:
            test_path = self.project_root / test_file
            
            if not test_path.exists():
                print_warning(f"{test_name} が見つかりません: {test_file}")
                self.results["warnings"].append(f"{test_file} 未検出")
                continue
            
            print_info(f"実行中: {test_name}")
            try:
                result = subprocess.run(
                    [str(python_exe), str(test_path)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    print_success(f"PASS: {test_name}")
                    self.results["tests_passed"].append(test_name)
                else:
                    print_error(f"FAIL: {test_name}")
                    print(result.stdout)
                    print(result.stderr)
                    self.results["tests_failed"].append(test_name)
            
            except subprocess.TimeoutExpired:
                print_error(f"タイムアウト: {test_name}")
                self.results["tests_failed"].append(test_name)
            except Exception as e:
                print_error(f"エラー: {test_name} - {e}")
                self.results["tests_failed"].append(test_name)
        
        self.results["steps_completed"].append("テスト実行")
    
    # ========================================================================
    # Step 6: 最終レポート
    # ========================================================================
    
    def step_final_report(self):
        """Step 6: 最終レポート生成"""
        print_step(6, "最終レポート")
        
        # レポート生成
        report = {
            "timestamp": self.results["timestamp"],
            "status": "SUCCESS" if not self.results["tests_failed"] else "PARTIAL_SUCCESS",
            "steps_completed": len(self.results["steps_completed"]),
            "tests_passed": len(self.results["tests_passed"]),
            "tests_failed": len(self.results["tests_failed"]),
            "details": self.results
        }
        
        # ターミナルに出力
        if self.results["tests_failed"]:
            print_warning(f"テスト失敗: {len(self.results['tests_failed'])} 個")
            for test in self.results["tests_failed"]:
                print_error(f"  ❌ {test}")
        else:
            print_success(f"すべてのテストに PASS しました！")
        
        # JSON レポート保存
        report_file = self.project_root / "phase0_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print_success(f"レポートを保存しました: {report_file}")
        
        # 次のステップ
        print_header("🎉 Phase 0 セットアップ完了！")
        print("\n次のステップ:")
        print("  1. LINE 通知設定（オプション） — src/notification/line_notifier.py")
        print("  2. Phase 1: Strategist RAR-S 計算実装")
        print("  3. Phase 2: Builder MVP 開発機能")
        print("\n詳細は README.md を参照してください。")

# ============================================================================
# メイン実行
# ============================================================================

if __name__ == "__main__":
    automation = Phase0Automation()
    automation.run()