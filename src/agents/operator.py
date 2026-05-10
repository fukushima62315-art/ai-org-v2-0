# src/agents/operator.py
# Operator Claude - 運用エージェント

import json
from typing import Dict, Optional, List
from datetime import datetime

class OperatorClaude:
    """
    責務:
    - SNS 運用（投稿スケジューリング）
    - ユーザー獲得施策
    - 月次財務レポート
    - ユーザーサポート初期対応
    """
    
    def __init__(self, name: str = "Operator"):
        self.name = name
        self.version = "2.0"
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """システムプロンプトを構築"""
        return """
あなたは Operator Claude です。SNS 運用、財務、ユーザー獲得を担当します。

【基本ルール】
- 有償広告・インフルエンサーは自動判定しない（階層 A）
- 炎上リスクのある投稿は Strategist に相談
- ユーザークレームは即座に Strategist へ（階層 A 判定）
- 月次予算の消費状況を常に監視

【責務】
1. SNS 投稿：事前承認テンプレートで定期投稿
2. ユーザー獲得：オーガニック（無償）チャネル優先
3. 月次財務レポート：売上、コスト、キャッシュフローを集計
4. ユーザーサポート：問い合わせ対応の初期受け付け
5. KPI 監視：DAU, MAU, リテンション等の追跡

【禁止事項】
- 有償広告を勝手に出稿
- クレームを握りつぶす（必ず Strategist へ）
- 炎上リスクを見落とす（投稿前に判定）
- 予算制約を無視

【月次サイクル】
Week 1: 前月実績集計
Week 2: SNS 投稿計画作成
Week 3-4: 定期投稿、ユーザー対応
Week 4 末: 月次レポート生成
        """
    
    def get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return self.system_prompt
    
    def get_agent_info(self) -> Dict:
        """エージェント情報を取得"""
        return {
            "name": self.name,
            "version": self.version,
            "role": "SNS 運用・財務・ユーザー獲得",
            "monthly_budget_jpy": 500,
            "responsibilities": [
                "SNS 投稿",
                "ユーザー獲得",
                "月次財務レポート",
                "ユーザーサポート"
            ]
        }

# __init__.py
__all__ = ['OperatorClaude']
