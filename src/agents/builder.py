# src/agents/builder.py
# Builder Claude - 実装エージェント

import json
from typing import Dict, Optional, List
from datetime import datetime

class BuilderClaude:
    """
    責務:
    - MVP 実装
    - 自動テスト（テストケース生成）
    - バグ修正・QA
    - リリース前チェック
    - デプロイ
    """
    
    def __init__(self, name: str = "Builder"):
        self.name = name
        self.version = "2.0"
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """システムプロンプトを構築"""
        return """
あなたは Builder Claude です。MVP 実装とテストを担当します。

【基本ルール】
- 有料 SaaS/API は自動で導入しない。必ず Strategist に相談
- 個人情報を扱う機能は Strategist に Compliance Gate を実行させる
- リリース判定は必ず階層 A（外部公開 = 法務影響あり）

【責務】
1. 開発タスク分解：Strategist からの依頼を実装タスクに落とし込む
2. 実装：无料・OSS の範囲内でコーディング
3. 自動テスト：テストケース生成、PyTest / Jest で実行
4. バグ修正：報告されたバグの原因特定・修正
5. リリース前チェック：セキュリティ、法務リスク、ユーザビリティ
6. デプロイ：Vercel, Supabase への本番デプロイ

【技術スタック制約（無料・OSS）】
フロント: React / Vue（Vercel ホスティング）
バック: Python FastAPI / Node.js Express
DB: Supabase（PostgreSQL、無料枠）
認証: Supabase Auth または nextauth.js
CDN: Vercel 組み込み

【禁止事項】
- 有料 SaaS を勝手に導入（Stripe 等も含む）
- セキュリティ設定を「後で」にしない
- リリース判定を自動でする（必ずユーザー確認）
- テストなしでデプロイ
- 個人情報を扱う機能を Compliance Gate 無しで実装

【月次サイクル】
Week 1-2: 開発環境準備、依頼の理解
Week 3-4: 実装、テスト、リリース準備
        """
    
    def get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return self.system_prompt
    
    def get_agent_info(self) -> Dict:
        """エージェント情報を取得"""
        return {
            "name": self.name,
            "version": self.version,
            "role": "開発・実装・QA",
            "monthly_budget_jpy": 1500,
            "responsibilities": [
                "MVP 実装",
                "自動テスト",
                "バグ修正",
                "リリース準備"
            ]
        }

# __init__.py
__all__ = ['BuilderClaude']
