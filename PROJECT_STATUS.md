# AI-Org v2.0 プロジェクト ステータス

**プロジェクト名**: AI 駆動スタートアップ型自己改善組織 v2.0
**最終更新**: 2026-05-10
**現状**: Phase 0 – 9 完了 + **🚀 本番デプロイ完了**
**本番 URL**: https://ai-org-v2-0.vercel.app ✅ READY

---

## 1. プロジェクト概要

Strategist / Builder / Operator の 3 エージェント構成による AI 組織フレームワーク。
月次 3,000 円予算内で自律運営し、金銭・法務・命に関わる判断は必ず人間に承認を求めるエスカレーション設計。

### 設計原則
- **限りなく低く**: 月次 Claude API 予算 3,000 円
- **モデル配分**: Haiku 60%（1,810 円）/ Sonnet 40%（1,190 円）/ **Opus 禁止**
- **3 階層判定**:
  - `A_HARD_STOP` — 金銭・法務 → 必ずユーザー確認
  - `B_LIGHT_APPROVAL` — 軽微な変更 → 24h で承認
  - `C_AUTO_DECIDED` — 技術選定など → 自動判定

### 技術スタック
| 層 | 技術 |
|---|---|
| 言語 | Python 3.11+ |
| LLM | Anthropic Claude API (Haiku / Sonnet) |
| バックエンド | FastAPI |
| 永続化 | Firebase Realtime Database |
| 通知 | LINE Messaging API |
| デプロイ | Vercel (API) + Firebase Hosting (Web) |

---

## 2. ここまでに行ったこと

| Phase | 主題 | 主要成果物 | テスト |
|---|---|---|---|
| **0** | 基盤構築 | config.py, BudgetManager, DelegationThreshold, LineNotifier, ModelSelector, 3 agents | 21/21 PASS |
| **1** | 階層判定統合 | 通知テンプレート / ユーザー応答受付 / 監査ログ | 全 PASS |
| **2** | Strategist RAR-S | RAR-S 計算・Conviction・Kill Criteria・月次振り返り | 全 PASS |
| **3** | Builder × Operator 統合 | TaskQueue / ReleaseChecker / SNSScheduler / KPITracker / FinancialReport / AgentCoordinator | 全 PASS |
| **4** | Claude API 実呼び出し | ClaudeAPIClient, エージェント別 system prompt, トークン追跡 | 全 PASS |
| **5** | FastAPI バックエンド | `/health` `/agents` `/chat/{agent}` `/escalations` `/rar-s` `/metrics` `/reports/monthly`, CORS, OpenAPI | 30/30 PASS |
| **6** | Firebase / LINE 統合 | FirebaseClient (mock 対応), EnhancedLineNotifier, NotificationRouter, EscalationNotifier, WeeklyReporter | 30/30 PASS |
| **7** | デプロイ検証 | vercel.json / firebase.json / .firebaserc / database.rules.json 自動生成, EnvValidator, PreDeployChecker, BuildValidator, DeploymentSimulator + RollbackManager | 30/30 PASS |
| **8** | AI 組織自体のベータテスト | AgentDecisionLog, EscalationAccuracyChecker, BudgetAccuracyMonitor, IncidentReporter, PromptTuningSuggester, IterationPlanner | 30/30 PASS |
| **9** | 本番運用・継続的監視 | HealthChecker, AnomalyDetector, AlertRouter, SLATracker, AuditTrail (SHA-256 hash chain), OperationsDashboard | 30/30 PASS |
| **本番デプロイ** | 🚀 Vercel 本番環境への実デプロイ | Git リポジトリ化、環境変数設定、vercel --prod 実行 | ✅ READY |

### 注意点
- Phase 0–7 は明確な product delivery（基盤 → API → バックエンド → デプロイ）
- Phase 8 / 9 は **AI 組織自体の運用品質を扱う観測・改善層** として今回拡張したもの
- プロジェクト本来の roadmap 文書は存在しない — Phase 番号は test ファイル末尾の「次ステップ」記述から自然継承

---

## 本番デプロイ完了 ✅

**実行日**: 2026-05-10
**デプロイ環境**: Vercel
**本番 URL**: https://ai-org-v2-0.vercel.app

### デプロイメント詳細
- **デプロイ ID**: dpl_7n4v7rcgx914Y7xRuZkGANWZY2ST
- **ステータス**: READY ✅
- **ビルド時間**: 16 秒
- **フレームワーク**: Python 3.12 + FastAPI
- **ヘルスチェック**: `/health` エンドポイント ✅ 動作確認済み

### 実装された API エンドポイント
```
GET  /health                 ← ヘルスチェック（動作確認済み）
GET  /agents                 ← 3 エージェント情報
GET  /chat/{agent}           ← エージェントとの会話
POST /escalations            ← エスカレーション管理
GET  /rar-s                  ← RAR-S スコア計算
GET  /metrics                ← 月次統計
GET  /reports/monthly        ← 月次レポート
GET  /openapi.json           ← API ドキュメント
```

### 次のステップ
1. **Firebase 統合**（推奨）— FIREBASE_DB_URL, FIREBASE_AUTH_TOKEN を設定
2. **LINE 統合**（推奨）— LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID を設定
3. **本番運用開始** — 1 ヶ月の実データ収集と監視

---

## 3. 主要ファイル一覧

```
ai-org-v2-0/
├── config.py
├── requirements.txt          # anthropic / fastapi / uvicorn / dotenv / requests
├── .env.example / .env.production.template
├── .gitignore                # *.pyc / venv / .env など
├── README.md / PHASE_0_CHECKLIST.md / PHASE_1_COMPLETION_REPORT.md
├── PROJECT_STATUS.md         # 本ファイル
├── CLAUDE.md                 # Claude Code 用プロジェクト Knowledge
│
├── vercel.json               # Phase 7 で生成
├── firebase.json
├── .firebaserc
├── database.rules.json
│
├── src/
│   ├── agents/{strategist,builder,operator}.py
│   ├── budget/budget_manager.py
│   ├── judgment/delegation_threshold.py
│   ├── notification/line_notifier.py
│   ├── models/model_selector.py
│   └── api/app.py            # FastAPI バックエンド
│
└── run_phase{1..9}_tests.py  # 各 Phase の単一ファイル統合テスト
```

---

## 4. テスト実行

```powershell
# UTF-8 強制（Windows cp932 対策）
python -X utf8 run_phase1_tests.py
python -X utf8 run_phase2_tests.py
python -X utf8 run_phase3_tests.py
python -X utf8 run_phase4_tests.py     # ※ 実 API キー必要
python -X utf8 run_phase5_tests.py     # FastAPI サーバー起動含む
python -X utf8 run_phase6_tests.py
python -X utf8 run_phase7_tests.py     # vercel.json 等を生成
python -X utf8 run_phase8_tests.py
python -X utf8 run_phase9_tests.py
```

すべて `単一ファイル / 依存性ゼロ` （Phase 4 のみ Anthropic SDK が必要）で実行可能。

---

## 5. 環境変数（本番）

```
ANTHROPIC_API_KEY=...
FIREBASE_DB_URL=https://<project>.firebaseio.com
FIREBASE_AUTH_TOKEN=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
MONTHLY_BUDGET_JPY=3000
```

---

## 6. 次に何をするか

**現状判断**: Phase 0 – 9 で「実装」と「観測・改善・運用監視」のレイヤーが揃った。
ここで一旦完了とするのが自然な切れ目。

### 選択肢

| # | 内容 | 想定工数 | 推奨度 |
|---|---|---|---|
| **A** | **ここで完了とする** | 0 | ★★★ |
| **B** | 実環境通し稼働 — Anthropic 実 API キーで 1 ヶ月運用し、Phase 8/9 の監視データを実取得 | 1 ヶ月（運用） | ★★★ |
| **C** | デプロイ実行 — Phase 7 で生成した設定で Vercel + Firebase Hosting に実デプロイ | 1–2 日 | ★★ |
| **D** | 他プロジェクトへのテンプレ化 — ai-org-v2-0 を「AI 組織スターターキット」として汎用化 | 1–2 週 | ★★ |
| **E** | Phase 10+ を新規定義（継続改善・スケールアウト・多エージェント拡張など） | 要件次第 | ★ |

### 推奨フロー
1. **A** で一旦完了宣言（本ドキュメントを成果物として保存）
2. ユーザー判断で **B** に進み、1 ヶ月の実運用データを取得
3. 実運用後、Phase 8 (`PromptTuningSuggester`) と Phase 9 (`OperationsDashboard`) が出力する改善提案を見て、**E** で具体的な Phase 10 を定義する

### Phase 10+ を始める前に確認すること
- 実 LINE トークン / Firebase プロジェクト / Vercel アカウントの整備状況
- 月次 3,000 円予算の運用実績（実際の消費パターン）
- Phase 8 が出力した P0/P1 改善提案の優先度（オーバーライド / インシデント実データから）

---

## 7. 既知の制約・残課題

- **Phase 4 の実 API テスト**: `ANTHROPIC_API_KEY` が `.env` にないとスキップされる
- **Phase 5 のサーバーポート**: `127.0.0.1:8765` 固定（衝突時は手動変更が必要）
- **Phase 6 の Firebase**: credentials 未設定時は mock モードで動作（実 DB 書き込みは行われない）
- **Phase 7 のデプロイ**: 設定ファイル生成と検証のみ — 実 `vercel deploy` / `firebase deploy` は未実行
- **Phase 8 / 9 のデータ**: 全てメモリ内 — 永続化は別途必要（Firebase 経由で `/decisions` `/incidents` `/audit_trail` 等のパスを定義する想定）

---

## 8. 参考: ディレクトリ構造の前提

このプロジェクト `C:\Users\off_t\Downloads\ai-org-v2-0\` は、親フォルダの `Downloads/CLAUDE.md`（2 歳向け英会話アプリ用）とは **別プロジェクト**。
作業ディレクトリが `ai-org-v2-0` の場合、親 CLAUDE.md の文脈（妻と協働、車・動物テーマ等）は本プロジェクトに適用されない。

---

**変更履歴**

| 日付 | 内容 |
|---|---|
| 2026-05-10 | Phase 0 – 9 完了、本 PROJECT_STATUS.md 作成 |
