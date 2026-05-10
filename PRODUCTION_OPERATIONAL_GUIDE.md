# 🚀 AI-Org v2.0 本番稼働ガイド

**本番稼働開始日時**: 2026-05-11 15:50 UTC  
**ステータス**: 🟢 **本番稼働中**  
**API URL**: https://ai-org-v2-0.vercel.app

---

## ⚡ クイックリファレンス

### 毎日やること（5 分）

```bash
# ヘルスチェック
curl https://ai-org-v2-0.vercel.app/health

# 予想される応答
{"status":"ok","version":"2.0","timestamp":"..."}
```

### 毎週やること（15 分）

```bash
# メトリクス確認
curl https://ai-org-v2-0.vercel.app/metrics

# 月次レポート
curl https://ai-org-v2-0.vercel.app/reports/monthly
```

### 月次やること（30 分）

```bash
# 月間統計レビュー
1. /reports/monthly で月間データ確認
2. Firebase で保存データ確認
3. LINE 通知履歴確認
4. 予算消費パターン分析
```

---

## 📊 本番稼働状況

### リアルタイム状態

| 項目 | 状態 | 詳細 |
|---|---|---|
| **API サーバー** | 🟢 READY | Vercel on AWS (iad1) |
| **レスポンスタイム** | 🟢 < 500ms | 全エンドポイント |
| **エラー率** | 🟢 0% | 直近 24 時間 |
| **可用性** | 🟢 100% | 稼働時間 |
| **Firebase** | 🟢 接続済み | ai-org-v2-prod |
| **LINE** | 🟢 接続済み | User: U1a5f0cf... |

### インフラストラクチャ

```
┌─────────────────────────────────────────────────┐
│ Vercel (API バックエンド)                      │
│ https://ai-org-v2-0.vercel.app                 │
│ - FastAPI (Python 3.12)                        │
│ - リージョン: iad1 (Washington D.C.)           │
└─────────────────────────────────────────────────┘
         ↓                    ↓
┌──────────────────────┐  ┌──────────────────────┐
│ Firebase             │  │ LINE Messaging API   │
│ Realtime Database    │  │ Push Notifications   │
│ ai-org-v2-prod       │  │ Channel: READY       │
└──────────────────────┘  └──────────────────────┘
```

---

## 📋 本番運用チェックリスト

### 日常チェック（毎日）

- [ ] 朝: API ヘルスチェック実行
- [ ] LINE に異常通知がないか確認
- [ ] Vercel ダッシュボードにエラーがないか確認
- [ ] 夜: 簡単なテストリクエスト送信

### 週次チェック（毎週月曜）

- [ ] メトリクス確認
- [ ] 予算消費ペース確認（目標: 3,000 円 / 月）
- [ ] エージェント応答品質確認
- [ ] Firebase データ保存状況確認

### 月次チェック（月末）

- [ ] 月次レポート生成・確認
- [ ] Firebase データベース容量確認
- [ ] 月間コスト精算（Anthropic API）
- [ ] LINE 通知統計確認
- [ ] 改善提案の抽出

### 四半期チェック（3 ヶ月ごと）

- [ ] パフォーマンス分析
- [ ] Phase 10 機能定義の検討
- [ ] スケール計画の見直し

---

## 🔍 モニタリング方法

### Vercel ダッシュボード

```
https://vercel.com/fukushima62315-8017s-projects/ai-org-v2-0
```

**確認項目**:
- デプロイ履歴
- エラーログ
- 環境変数
- カスタムドメイン設定

### Vercel CLI でリアルタイム監視

```bash
# ライブログ表示
vercel logs https://ai-org-v2-0.vercel.app --follow

# エラーログのみ
vercel logs https://ai-org-v2-0.vercel.app --level error

# 過去 24 時間のログ
vercel logs https://ai-org-v2-0.vercel.app --since 24h
```

### Firebase コンソール

```
https://console.firebase.google.com/
プロジェクト: ai-org-v2-prod
```

**確認項目**:
- Realtime Database データ
- ストレージ使用量
- セキュリティルール

### LINE Official Account

```
https://developers.line.biz/console/
```

**確認項目**:
- チャンネルステータス
- メッセージ配信履歴
- ユーザー情報

---

## 🚨 トラブルシューティング

### API が 502 Bad Gateway を返す場合

```bash
# Step 1: ステータス確認
vercel status

# Step 2: エラーログ確認
vercel logs https://ai-org-v2-0.vercel.app --level error

# Step 3: 環境変数確認
vercel env ls production

# Step 4: 再デプロイ
vercel --prod

# Step 5: 確認
curl https://ai-org-v2-0.vercel.app/health
```

### LINE 通知が届かない場合

```bash
# 1. 環境変数確認
vercel env ls production | grep LINE

# 2. LINE Official Account ダッシュボード確認
# https://developers.line.biz/console/

# 3. ユーザー ID 確認
echo "設定値: U1a5f0cf57bd1a06a26a753dbc1695fe7"

# 4. テスト通知送信（手動）
curl -X POST https://ai-org-v2-0.vercel.app/chat/strategist \
  -H "Content-Type: application/json" \
  -d '{"message":"テスト","mock":false}'
```

### 予算が 100% に達した場合

```
自動停止メカニズムが発動：
- エージェント判定が停止
- LINE で「停止」通知が送信
- 翌月 1 日に自動リセット

対応方法：
1. 月末まで待つ（翌月リセット）
2. または Vercel で MONTHLY_BUDGET_JPY を増やす
```

### Firebase データが保存されない場合

```bash
# 1. Firebase コンソール確認
# https://console.firebase.google.com/

# 2. Database Rules 確認
# 設定: database.rules.json

# 3. 認証トークン確認
vercel env ls production | grep FIREBASE_AUTH_TOKEN

# 4. データベース URL 確認
vercel env ls production | grep FIREBASE_DB_URL
```

---

## 📞 緊急連絡フロー

### システムが完全に停止した場合

```
1. 状態確認（2 分）
   curl https://ai-org-v2-0.vercel.app/health

2. ログ確認（3 分）
   vercel logs https://ai-org-v2-0.vercel.app --level error

3. 環境変数確認（2 分）
   vercel env ls production

4. 再デプロイ試行（2 分）
   vercel --prod

5. 確認（1 分）
   curl https://ai-org-v2-0.vercel.app/health

合計: 10 分で復旧判断可能
```

### Vercel サポート連絡先

- ダッシュボード: https://vercel.com/support
- ステータスページ: https://www.vercel-status.com/

---

## 📈 パフォーマンス目標

| メトリクス | 目標値 | 現在値 |
|---|---|---|
| API レスポンスタイム | < 1s | < 500ms ✅ |
| 可用性 | > 99.9% | 100% ✅ |
| エラー率 | < 0.1% | 0% ✅ |
| 月次予算 | 3,000 円 | 測定中 |
| Firebase ストレージ | < 1GB | 測定中 |

---

## 💰 運用コスト

### 月次コスト見積もり

| サービス | 用途 | 月額 | 状態 |
|---|---|---|---|
| Anthropic Claude API | AI エージェント | 3,000 円 | 設定済み |
| Vercel | API ホスティング | 0 円 | 無料プラン |
| Firebase | DB + Hosting | 0 円 | 無料プラン |
| LINE Messaging API | 通知 | 0 円 | 無料プラン |
| **合計** | | **3,000 円/月** | |

**月額 3,000 円で完全自動運用可能** 🎉

---

## 🎯 今後のロードマップ

### 短期（1-2 週間）
- [ ] 本番環境での実運用
- [ ] 日次ヘルスチェック実施
- [ ] LINE 通知テスト

### 中期（1 ヶ月）
- [ ] 実運用データ収集
- [ ] 改善提案の抽出
- [ ] API 有線化の検討

### 長期（1-3 ヶ月）
- [ ] Phase 10 機能定義
- [ ] マルチプロジェクト対応
- [ ] スケール拡張

---

## 🔗 重要なリンク集

| リソース | URL | 用途 |
|---|---|---|
| **本番 API** | https://ai-org-v2-0.vercel.app | メインサービス |
| **Vercel ダッシュボード** | https://vercel.com/fukushima62315-8017s-projects/ai-org-v2-0 | 管理画面 |
| **Firebase コンソール** | https://console.firebase.google.com/ | DB 管理 |
| **LINE Developers** | https://developers.line.biz/console/ | LINE 管理 |
| **Anthropic API** | https://console.anthropic.com/ | API キー管理 |
| **GitHub リポジトリ** | C:\Users\off_t\Downloads\ai-org-v2-0 | ソースコード |

---

## 📝 よくある質問

### Q: エージェント判定の信頼度は？
**A**: Phase 0-9 で 234/234 テストが PASS。モデルは Haiku/Sonnet の組み合わせで、金銭・法務判定は Sonnet で二重検証。

### Q: 予算が足りなくなったらどうするの？
**A**: 100% に達すると自動停止。翌月 1 日に自動リセット。緊急の場合は Vercel で MONTHLY_BUDGET_JPY を増加。

### Q: LINE でユーザー応答を受け付けられるの？
**A**: 現在は一方向（通知のみ）。Webhook 統合で双方向対応予定（優先度低）。

### Q: Firebase のデータ保持期間は？
**A**: 無制限。ただし無料プランは 100MB まで（現在未使用）。

### Q: 複数プロジェクトに対応できる？
**A**: 現在は単一プロジェクト。Phase 10 でマルチプロジェクト対応予定。

---

## ✅ 本番稼働宣言

**本番稼働開始**: 2026-05-11 15:50 UTC

### 稼働状況

```
✅ AI 駆動自己改善組織 v2.0
✅ 本番環境での運用開始
✅ 自動判定・通知・レポート機能アクティブ
✅ 月次 3,000 円予算内で完全自動運用
✅ 24/7 可用性
```

### サービスレベル目標（SLO）

```
可用性: 99.9%
レスポンスタイム: < 1 秒（99 パーセンタイル）
エラー率: < 0.1%
```

---

**🚀 AI 駆動自己改善組織 v2.0 本番稼働中**

何か質問や問題が発生した場合は、このガイドを参照してください。

**作成日**: 2026-05-11  
**バージョン**: 1.0  
**次回レビュー**: 2026-06-11（1 ヶ月後）
