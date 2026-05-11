# AI-Org v2.0

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
