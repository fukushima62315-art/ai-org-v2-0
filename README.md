# AI駆動スタートアップ型自己改善組織 v2.0 — 実装コード

**バージョン:** 2.0（Phase 0 実装版）
**作成日:** 2026-05-10
**ステータス:** 開発中

---

## 📋 目次

1. [セットアップ](#セットアップ)
2. [プロジェクト構成](#プロジェクト構成)
3. [コンポーネント説明](#コンポーネント説明)
4. [テスト実行](#テスト実行)
5. [トラブルシューティング](#トラブルシューティング)

---

## 🚀 セットアップ

### 前提条件

- Python 3.11+
- pip
- Git

### 初期設定

```bash
# 1. リポジトリをクローン（または新規作成）
git clone <repository-url>
cd ai-org-v2-0

# 2. 仮想環境を作成
python -m venv venv

# 3. 仮想環境を有効化
# macOS / Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# 4. 依存パッケージをインストール
pip install -r requirements.txt

# 5. .env ファイルを設定
cp .env.example .env
# .env を編集して、実際の値を入力
# 特に ANTHROPIC_API_KEY を設定
```

### 環境変数の確認

```bash
# 設定値の妥当性をチェック
python -c "from config import config; issues = config.validate(); print('\n'.join(issues)) if issues else print('✅ 設定は正常です')"
```

---

## 📁 プロジェクト構成

```
ai-org-v2-0/
├── config.py                    # 設定ファイル（.env から読み込み）
├── .env.example                 # 環境変数テンプレート
├── .gitignore                   # Git 無視設定
├── requirements.txt             # Python 依存パッケージ
├── README.md                    # このファイル
│
├── src/
│   ├── agents/                  # 3 エージェント定義
│   │   ├── __init__.py
│   │   ├── strategist.py        # Strategist Claude
│   │   ├── builder.py           # Builder Claude
│   │   └── operator.py          # Operator Claude
│   │
│   ├── budget/                  # 予算管理エンジン
│   │   ├── __init__.py
│   │   └── budget_manager.py    # 月次予算＆80% ルール
│   │
│   ├── judgment/                # 階層判定エンジン
│   │   ├── __init__.py
│   │   └── delegation_threshold.py  # A/B/C 階層判定
│   │
│   ├── notification/            # 通知エンジン
│   │   ├── __init__.py
│   │   └── line_notifier.py     # LINE Messaging API
│   │
│   ├── schemas/                 # JSON スキーマ（未実装）
│   │   └── .gitkeep
│   │
│   ├── logs/                    # ログファイル（生成時に作成）
│   │   ├── audit.log
│   │   ├── budget.log
│   │   └── notifications.log
│   │
│   └── utils/                   # ユーティリティ
│       ├── __init__.py
│       └── .gitkeep
│
└── tests/
    ├── __init__.py
    ├── test_budget.py           # 予算管理テスト
    └── test_delegation.py       # 階層判定テスト
```

---

## 🎯 モデル選択戦略（v2.0）

### 基本方針

v2.0 の「限りなく低く」の理念に従い、月次 3,000 円予算下で**費用対効果を最大化**します：

| モデル | 役割 | 月次割当 | 理由 |
|---|---|---|---|
| **Haiku** | 定型処理・軽微な判定 | 60%（1,810 円） | 最安値、反復タスク多数 |
| **Sonnet** | クリティカル判定・検証 | 40%（1,190 円） | 金銭・法務・命 に関わる判定 |
| **Opus** | — | **0%（禁止）** | コスト が 15 倍、ROI が見合わない |

### エージェント別配分

```
Strategist（市場分析・企画）
  ├─ Haiku 560 円: トレンド分析、RAR-S 計算、Compliance Gate
  └─ Sonnet 240 円: RAR-S 検証（金銭判定）

Builder（開発・実装）
  ├─ Haiku 900 円: テストケース、バグ軽微修正
  └─ Sonnet 600 円: 致命的バグ（データロス）、セキュリティ

Operator（SNS・財務）
  ├─ Haiku 350 円: 定型投稿、KPI 数値化
  └─ Sonnet 150 円: クレーム判定、炎上リスク

予備
  └─ Sonnet 200 円: 緊急判定、予期しないクリティカル
```

### 使用例

```python
from src.models import ModelSelector

selector = ModelSelector()

# Haiku を選択（定型処理）
model = selector.select_model(
    agent="strategist",
    task_type="トレンド分析スキャン"
)
# → "haiku"

# Sonnet を選択（金銭判定）
model = selector.select_model(
    agent="strategist",
    task_type="RAR-S スコア検証",
    context={"financial_impact": True}
)
# → "sonnet"

# クリティカル判定は必ず Sonnet
model = selector.select_model(
    agent="builder",
    task_type="任意",
    is_critical=True
)
# → "sonnet"
```

---

### 1. `config.py` — 設定管理

```python
from config import Config

# 設定値にアクセス
print(Config.MONTHLY_BUDGET_JPY)  # 3000
print(Config.STRATEGIST_BUDGET)   # 800
```

**設定項目:**
- `ANTHROPIC_API_KEY`: Claude API キー
- `MONTHLY_BUDGET_JPY`: 月次予算（円）
- `*_BUDGET`: エージェント別予算配分

---

### 2. `src/budget/budget_manager.py` — 予算管理

**主要機能:**
- 月次予算の消費追跡
- 50% / 70% / 80% / 100% のステータス判定
- 80% 到達時のエスカレーション提案生成

**使用例:**

```python
from src.budget import BudgetManager
from config import Config

manager = BudgetManager(Config)

# コスト消費を記録
manager.log_consumption("builder", 500, "MVP development")

# 予算ステータスを確認
status = manager.get_budget_status()
print(status["percentage"])  # 16.7%
print(status["status"])      # "NORMAL"

# 80% 時のエスカレーション確認
escalation = manager.check_and_escalate()
if escalation:
    print(escalation["alert_type"])  # "BUDGET_80_PERCENT"
```

---

### 3. `src/judgment/delegation_threshold.py` — 階層判定

**階層:**
- **A: HARD_STOP** — お金 or 法的リスク → ユーザー必ず確認
- **B: LIGHT_APPROVAL** — 軽微な変更 → 24h で承認
- **C: AUTO_DECIDED** — 技術選定など → 自動判定

**使用例:**

```python
from src.judgment import DelegationThreshold

judge = DelegationThreshold()

# ケース 1: 金銭発生（階層 A）
result = judge.judge(
    "Firebase の有料プランに切り替える",
    {"estimated_cost_jpy": 2500}
)
print(result["escalation_level"])  # "A_HARD_STOP"

# ケース 2: 技術選定（階層 C）
result = judge.judge("React を Vue に変更")
print(result["escalation_level"])  # "C_AUTO_DECIDED"
```

---

### 4. `src/notification/line_notifier.py` — LINE 通知

**使用例:**

```python
from src.notification import LineNotifier

notifier = LineNotifier()

# エスカレーション通知
escalation_data = {
    "trigger_reason": "Firebase プラン切り替えの判定",
    "context": {"cost": "2,500 円/月"}
}
notifier.send_escalation_a(escalation_data)

# 予算警告
budget_status = {
    "status": "EMERGENCY_80",
    "consumed_jpy": 2400,
    "monthly_limit": 3000,
    "percentage": 80.0
}
notifier.send_80_percent_proposal(budget_status)
```

**設定要件:**
- LINE Developers でチャンネル作成
- Channel Access Token を `.env` に設定

---

### 5. `src/models/model_selector.py` — モデル選択戦略

**主要機能:**
- Haiku/Sonnet の自動選択
- エージェント別・タスク別の判定
- クリティカルタスク の Sonnet 強制
- 月次モデル使用統計

**使用例:**

```python
from src.models import ModelSelector

selector = ModelSelector()

# タスク種別でモデル自動選択
model = selector.select_model(
    agent="builder",
    task_type="致命的バグ判定",
    context={"severity": "CRITICAL"}
)
# → "sonnet"

# 金銭判定は必ず Sonnet
model = selector.select_model(
    agent="strategist",
    task_type="RAR-S 検証",
    context={"financial_impact": True}
)
# → "sonnet"

# 月次使用統計
usage = selector.get_monthly_usage()
print(usage)
# → {"haiku": {...}, "sonnet": {...}, "opus": {"status": "FORBIDDEN"}}
```

---

```python
from src.agents import StrategistClaude, BuilderClaude, OperatorClaude

strategist = StrategistClaude()
print(strategist.get_system_prompt())
# → システムプロンプトを取得

builder = BuilderClaude()
print(builder.get_agent_info())
# → {"name": "Builder", "role": "開発・実装・QA", ...}
```

---

## 🧪 テスト実行

### すべてのテストを実行

```bash
python -m pytest tests/ -v
```

### 個別テストを実行

```bash
# 予算管理テスト
python tests/test_budget.py

# 階層判定テスト
python tests/test_delegation.py
```

### テスト結果の例

```
🧪 Budget Manager Tests

✅ PASS: 通常運用（50% 以下）
✅ PASS: 警告（50%）
✅ PASS: 注意（70%）
✅ PASS: 危機（80%）エスカレーション
✅ PASS: 停止（100%）
✅ PASS: 月次レポート生成

🎉 All budget tests passed!
```

---

## ⚠️ トラブルシューティング

### Q1: `ModuleNotFoundError: No module named 'anthropic'`

```bash
# 依存パッケージが足りない
pip install -r requirements.txt
```

### Q2: `ANTHROPIC_API_KEY が設定されていません`

```bash
# .env を作成して API キーを設定
cp .env.example .env
# .env を編集して、ANTHROPIC_API_KEY を入力
```

### Q3: LINE 通知が届かない

```bash
# LINE トークンが設定されているか確認
grep LINE_CHANNEL_ACCESS_TOKEN .env

# 設定されていなければ .env に追加
echo "LINE_CHANNEL_ACCESS_TOKEN=your-token" >> .env
echo "LINE_USER_ID=your-user-id" >> .env
```

---

## 📊 ログの確認

```bash
# 予算ログ
tail -f src/logs/budget.log

# 監査ログ
tail -f src/logs/audit.log

# 通知ログ
tail -f src/logs/notifications.log
```

---

## 🔐 本番環境への展開チェック

リリース前に確認してください：

- [ ] `.env` に `ANTHROPIC_API_KEY` を設定
- [ ] `.env` を `.gitignore` に含めている
- [ ] テストをすべてパスしている
- [ ] ログディレクトリが作成できる
- [ ] LINE トークンが有効（通知機能を使う場合）

---

## 📞 サポート

問題が発生した場合：

1. ログファイルを確認（`src/logs/`）
2. テストを実行して動作確認（`python tests/test_*.py`）
3. 設定値を確認（`python -c "from config import config; config.validate()"`)

---

**v2.0 Phase 0 実装完了！** 🎉

次のステップ → Phase 1（DelegationThreshold の完全統合）
