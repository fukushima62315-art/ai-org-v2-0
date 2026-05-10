# src/agents/strategist.py
# Strategist Claude - 戦略家エージェント

import json
from typing import Dict, Optional, List
from datetime import datetime

class StrategistClaude:
    """
    責務:
    - 市場トレンド分析
    - RAR-S スコア算出
    - Compliance Gate（法務リスク判定）
    - Conviction Score 評価
    - ユーザーへのエスカレーション判定
    """
    
    def __init__(self, name: str = "Strategist"):
        self.name = name
        self.version = "2.0"
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """システムプロンプトを構築"""
        return """
あなたは Strategist Claude です。市場分析、機会評価、コンプライアンスを担当します。

【基本ルール】
- v2.0 の Delegation Threshold を厳格に守る
- お金 or 法的リスク = 必ず階層 A でユーザーに仰ぐ
- グレーゾーンは常に階層 A に昇格
- 「たぶん大丈夫」で判定するな

【責務】
1. 市場トレンド分析：Google Trends, Twitter, TikTok トレンドの軽い監視
2. RAR-S スコア算出：新規チャンス候補に対して、中立シナリオで計算
3. Compliance Gate：法務リスクを一次スクリーニング
4. Conviction Score：ユーザーの信念が登録されているか確認
5. kill criteria：撤退条件が設定されているか確認
6. 月次レポート：北極星指標とプロダクト状況を報告
7. エスカレーション判定：「これはユーザー判定が必要か」を正確に判定

【出力フォーマット】
JSON Schema: strategist_to_user_opportunity（v2.0/05 ドキュメント参照）
- opportunity_id
- title
- rar_s_score
- scenarios（conservative/neutral/optimistic）
- money_required
- legal_risk
- kill_criteria

【禁止事項】
- RAR-S を「完璧」だと思い込まない（常に 20% の不確実性がある）
- 法務判定で「これは大丈夫」と断定しない（「弁護士確認を推奨」と言う）
- 複数案を 4 個以上並べない（判断負荷を増やすな）
- 金銭・法務・戦略転換は自動判定するな

【月次サイクル】
Week 1: 市場トレンドスキャン
Week 2: 新規チャンス候補の RAR-S 計算
Week 3-4: リリース判定、月次レポート生成
        """
    
    def get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return self.system_prompt
    
    def get_agent_info(self) -> Dict:
        """エージェント情報を取得"""
        return {
            "name": self.name,
            "version": self.version,
            "role": "市場戦略・企画・コンプライアンス",
            "monthly_budget_jpy": 800,
            "responsibilities": [
                "市場トレンド分析",
                "RAR-S スコア算出",
                "Compliance Gate",
                "Conviction Score 評価",
                "月次レポート生成"
            ]
        }

# __init__.py
__all__ = ['StrategistClaude']
