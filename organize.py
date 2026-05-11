#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-Org v2.0 プロジェクト整理スクリプト
=====================================

【処理内容】
1. ドキュメント整理
   - 設計ドキュメント: /docs/design/
   - 進捗報告: /docs/reports/
   - その他: /docs/misc/

2. テストファイル整理
   - run_phase*.py → /tests/

3. 設定ファイル整理
   - .env* / vercel.json / firebase.json → /config/

4. 不要なファイル削除
   - phase0_automation.py
   - phase0_report.json
   - setup.py
   - 古い action ワークフロー

5. ディレクトリ構造を統一
   - /src/api/
   - /src/agents/
   - /src/core/
   - /tests/

【使い方】
  python organize.py
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
BACKUP_DIR = ROOT / f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def move_file(src: Path, dst_dir: Path, verbose=True):
    """ファイルを移動"""
    if not src.exists():
        return False
    ensure_dir(dst_dir)
    dst = dst_dir / src.name
    shutil.move(str(src), str(dst))
    if verbose:
        print(f"  ✅ {src.name} → {dst_dir.relative_to(ROOT)}/")
    return True

def delete_file(path: Path, verbose=True):
    """ファイルを削除"""
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(str(path))
    else:
        path.unlink()
    if verbose:
        print(f"  🗑️  {path.name} 削除")
    return True

print("=" * 70)
print("📁 AI-Org v2.0 プロジェクト整理開始")
print("=" * 70)

# =========================================================================
# ステップ 1: バックアップ
# =========================================================================

print("\n📦 バックアップを作成中...")
ensure_dir(BACKUP_DIR)

for item in ROOT.glob("*"):
    if item.name.startswith("."):
        continue
    if item.name == "rebuild.py":
        continue
    if item.is_dir() and item.name in ["docs", "src", "tests", "config"]:
        continue
    
    backup_path = BACKUP_DIR / item.name
    if item.is_dir():
        shutil.copytree(str(item), str(backup_path))
    else:
        shutil.copy2(str(item), str(backup_path))

print(f"  ✅ バックアップ: {BACKUP_DIR.name}/")

# =========================================================================
# ステップ 2: ディレクトリ構造を作成
# =========================================================================

print("\n📂 ディレクトリ構造を作成中...")

DIRS = {
    "docs": ["design", "reports", "misc"],
    "tests": ["phase1", "phase2", "phase3", "phase4", "phase5", "phase6", "phase7", "phase8", "phase9"],
    "config": [],
    "src": ["api", "agents", "core", "budget", "judgment", "notification", "models", "logs"],
}

for parent, subs in DIRS.items():
    parent_path = ROOT / parent
    ensure_dir(parent_path)
    for sub in subs:
        ensure_dir(parent_path / sub)

print("  ✅ ディレクトリ作成完了")

# =========================================================================
# ステップ 3: ドキュメント移動
# =========================================================================

print("\n📚 ドキュメント整理中...")

design_files = [
    "00_v2_0_改訂サマリー.md",
    "01_意思決定_DelegationThreshold_v2_0.md",
    "02_組織設計_3Agents_MVP_v2_0.md",
    "03_スコアリンク__RAR_S_Conviction_v2_0.md",
    "04_財務モテ_ル_3Scenario_v2_0.md",
    "05_JSON_Schema_DataFlow_v2_0.md",
    "06_例外フロー_ErrorHandling_v2_0.md",
    "07_実装ロート_マッフ__v2_0.md",
    "08_予算制約_LowBudget_v2_0.md",
    "09_モテ_ル選択戦略_Haiku_Sonnet_v2_0.md",
]

for f in design_files:
    path = ROOT / f
    if path.exists():
        move_file(path, ROOT / "docs" / "design")

report_files = [
    "DEPLOYMENT_COMPLETE_2026-05-11.md",
    "PHASE_0_CHECKLIST.md",
    "PHASE_1_COMPLETION_REPORT.md",
    "PROJECT_STATUS.md",
    "Next_Action_Plan.md",
]

for f in report_files:
    path = ROOT / f
    if path.exists():
        move_file(path, ROOT / "docs" / "reports")

misc_files = [
    "CLAUDE.md",
    "FILES_SUMMARY.txt",
    "_env",
    "_gitignore",
]

for f in misc_files:
    path = ROOT / f
    if path.exists():
        move_file(path, ROOT / "docs" / "misc")

# =========================================================================
# ステップ 4: テストファイル移動
# =========================================================================

print("\n🧪 テストファイル整理中...")

for i in range(1, 10):
    test_file = ROOT / f"run_phase{i}_tests.py"
    if test_file.exists():
        phase_dir = ROOT / "tests" / f"phase{i}"
        ensure_dir(phase_dir)
        move_file(test_file, phase_dir)

# =========================================================================
# ステップ 5: 設定ファイル移動
# =========================================================================

print("\n⚙️  設定ファイル整理中...")

config_files = [
    ".env.example",
    "vercel.json",
    "firebase.json",
    ".firebaserc",
    "database_rules.json",
    "config.py",
    "requirements.txt",
]

for f in config_files:
    path = ROOT / f
    if path.exists():
        move_file(path, ROOT / "config")

# =========================================================================
# ステップ 6: 不要なファイル削除
# =========================================================================

print("\n🗑️  不要なファイル削除中...")

delete_files = [
    "phase0_automation.py",
    "phase0_report.json",
    "setup.py",
]

for f in delete_files:
    path = ROOT / f
    delete_file(path)

# =========================================================================
# ステップ 7: README 更新
# =========================================================================

print("\n📝 README 更新中...")

readme_content = """# AI-Org v2.0

Strategist / Builder / Operator の 3 エージェント構成による AI 駆動自己改善組織フレームワーク。

## 📁 ディレクトリ構造

```
ai-org-v2-0/
├── docs/                    # ドキュメント
│   ├── design/             # 設計ドキュメント（v2.0 全体）
│   ├── reports/            # 進捗報告・レポート
│   └── misc/               # その他
│
├── src/                     # ソースコード
│   ├── api/                # FastAPI バックエンド
│   ├── agents/             # 3 エージェント実装
│   ├── core/               # コア機能
│   ├── budget/             # 予算管理
│   ├── judgment/           # 階層判定
│   ├── notification/       # 通知機能
│   ├── models/             # モデル選択
│   └── logs/               # ログディレクトリ
│
├── tests/                   # テストファイル
│   ├── phase1/
│   ├── phase2/
│   └── ... (phase9 まで)
│
├── config/                  # 設定ファイル
│   ├── .env.example
│   ├── vercel.json
│   ├── firebase.json
│   ├── database_rules.json
│   ├── config.py
│   └── requirements.txt
│
├── .github/
│   └── workflows/          # GitHub Actions CI/CD
│
├── .gitignore
├── README.md
├── rebuild.py             # 再構築スクリプト
└── organize.py            # 整理スクリプト（このファイル）
```

## 🚀 セットアップ

### 1. 環境構築
```bash
cd ai-org-v2-0
python rebuild.py          # ファイル生成（初回のみ）
```

### 2. 依存パッケージインストール
```bash
pip install -r config/requirements.txt
```

### 3. API キー設定
```bash
cp config/.env.example .env
# .env を編集して ANTHROPIC_API_KEY を設定
```

### 4. テスト実行
```bash
python -X utf8 tests/phase1/run_phase1_tests.py
python -X utf8 tests/phase2/run_phase2_tests.py
python -X utf8 tests/phase3/run_phase3_tests.py
python -X utf8 tests/phase5/run_phase5_tests.py
```

## 📊 主要機能

### 3 エージェント
- **Strategist** (🧠): RAR-S スコア評価・意思決定
- **Builder** (🔨): 実装・タスク管理・リリース確認
- **Operator** (📡): SNS 投稿・KPI 追跡・月次レポート

### 3 階層判定
- **A_HARD_STOP**: 金銭・法務 → ユーザー確認必須
- **B_LIGHT_APPROVAL**: 軽微変更 → 24h 承認
- **C_AUTO_DECIDED**: 技術選定 → 自動判定

### 予算管理
- 月次予算: ¥3,000
- Haiku 60% (¥1,810) / Sonnet 40% (¥1,190)
- Opus 禁止

## 🔗 本番 URL

https://ai-org-v2-0.vercel.app

### エンドポイント一覧
- `GET /` — ウェルカムページ（HTML）
- `GET /health` — ヘルスチェック
- `GET /agents` — エージェント一覧
- `POST /chat/{agent_name}` — エージェントと対話
- `POST /escalations` — 案件作成
- `GET /escalations` — 案件一覧
- `POST /rar-s` — RAR-S スコア計算
- `GET /metrics` — KPI・予算
- `GET /reports/monthly` — 月次レポート
- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc

## 📖 ドキュメント

詳細は `docs/` ディレクトリを参照：

- `docs/design/` — 設計ドキュメント（全 10 ファイル）
- `docs/reports/` — 進捗報告書・レポート
- `docs/misc/` — その他

## 🛠️ 開発

### ローカルで API サーバーを起動
```bash
# パッケージインストール
pip install -r config/requirements.txt

# サーバー起動（http://127.0.0.1:8000）
python -c "from src.api.app import app; import uvicorn; uvicorn.run(app, host='127.0.0.1', port=8000)"
```

### GitHub Action CI/CD
- Push → 自動テスト実行
- Phase 1-3, 5 のテストを自動実行
- テスト結果を artifact として保存

## 💡 推奨フロー

1. **ローカルで開発**
   ```bash
   python -X utf8 tests/phase1/run_phase1_tests.py
   ```

2. **GitHub に Push**
   ```bash
   git add .
   git commit -m "Feature: ..."
   git push
   ```

3. **GitHub Actions が自動テスト実行**

4. **Vercel が自動デプロイ**
   ```
   https://ai-org-v2-0.vercel.app
   ```

## 📋 Phase ロードマップ

| Phase | 主題 | ステータス |
|-------|------|-----------|
| 0 | 基盤構築 | ✅ 完了 |
| 1 | 階層判定エンジン | ✅ 完了 |
| 2 | Strategist RAR-S | ✅ 完了 |
| 3 | Builder × Operator 統合 | ✅ 完了 |
| 4 | Claude API 実呼び出し | ✅ 完了 |
| 5 | FastAPI バックエンド | ✅ 完了 |
| 6 | Firebase / LINE 統合 | ✅ 完了 |
| 7 | デプロイ検証 | ✅ 完了 |
| 8 | AI 組織ベータテスト | ✅ 完了 |
| 9 | 本番運用・監視 | ✅ 完了 |
| 10+ | 継続改善（検討中） | 📋 未定義 |

## 🔒 セキュリティ

- `.env` は `.gitignore` に記載（Git に Push しない）
- API キーはすべて環境変数で管理
- Vercel / Firebase の本番環境でのみシークレット設定

## 📞 サポート

各ファイルには説明コメントが記載されています。
詳細は `docs/design/` の各ドキュメントを参照してください。

## 📄 ライセンス

Private（個人プロジェクト）
"""

readme_path = ROOT / "README.md"
readme_path.write_text(readme_content, encoding="utf-8")
print("  ✅ README.md 更新")

# =========================================================================
# ステップ 8: .gitignore 更新
# =========================================================================

print("\n🔒 .gitignore 確認・更新中...")

gitignore_content = """# Environment
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
src/logs/

# Misc
.backup_*
phase0_report.json
"""

gitignore_path = ROOT / ".gitignore"
gitignore_path.write_text(gitignore_content, encoding="utf-8")
print("  ✅ .gitignore 更新")

# =========================================================================
# ステップ 9: 完了メッセージ
# =========================================================================

print("\n" + "=" * 70)
print("✅ プロジェクト整理完了！")
print("=" * 70)

print(f"""
📁 新しいディレクトリ構造:
  docs/
    ├── design/          (設計ドキュメント 10 ファイル)
    ├── reports/        (進捗報告書)
    └── misc/           (その他)
  
  src/
    ├── api/            (FastAPI アプリ)
    ├── agents/         (Strategist, Builder, Operator)
    ├── core/           (コア機能)
    ├── budget/         (予算管理)
    ├── judgment/       (階層判定)
    ├── notification/   (LINE 通知)
    ├── models/         (モデル選択)
    └── logs/           (ログディレクトリ)
  
  tests/
    ├── phase1/
    ├── phase2/
    └── ... (phase9 まで)
  
  config/
    ├── .env.example
    ├── vercel.json
    ├── firebase.json
    ├── database_rules.json
    ├── config.py
    └── requirements.txt

⚙️  次のステップ:
  1. テストを実行して PASS を確認
     python -X utf8 tests/phase1/run_phase1_tests.py

  2. GitHub に push
     git add .
     git commit -m "refactor: organize directory structure"
     git push

  3. Vercel が自動デプロイ

💾 バックアップ:
  {BACKUP_DIR.name}/ に旧ファイルがあります

""")

print("=" * 70)
