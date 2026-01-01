"""
KnowledgeBase E2E テスト

ローカル環境と AWS 環境の両方で同一テストケースを実行。
"""

from __future__ import annotations

import pytest

from src.interfaces import SearchResult


class TestKnowledgeBase:
    """KnowledgeBase Protocol の E2E テスト"""

    def test_ingest_documents(self, knowledge_base, sample_documents):
        """ドキュメント取り込みテスト"""
        count = knowledge_base.ingest_documents(sample_documents)

        assert count == len(sample_documents)

    def test_retrieve(self, knowledge_base, sample_documents):
        """ドキュメント検索テスト"""
        # ドキュメント取り込み
        knowledge_base.ingest_documents(sample_documents)

        # 検索
        results = knowledge_base.retrieve(
            query="What is Amazon S3 Vectors?",
            top_k=3,
        )

        assert len(results) > 0
        assert isinstance(results[0], SearchResult)
        # S3 Vectors に関するドキュメントが上位に来るはず
        assert any("s3" in r.content.lower() or "vector" in r.content.lower() for r in results)

    def test_retrieve_with_filter(self, knowledge_base, sample_documents):
        """フィルタ付き検索テスト"""
        # ドキュメント取り込み
        knowledge_base.ingest_documents(sample_documents)

        # フィルタ付き検索
        results = knowledge_base.retrieve(
            query="AWS services",
            top_k=10,
            filter={"topic": "bedrock"},
        )

        # bedrock トピックのみが返されるはず
        for result in results:
            if result.metadata:
                assert result.metadata.get("topic") == "bedrock"

    def test_retrieve_and_generate(self, knowledge_base, sample_documents, is_local):
        """RAG テスト（検索 + 回答生成）"""
        # ドキュメント取り込み
        knowledge_base.ingest_documents(sample_documents)

        # RAG 実行
        answer = knowledge_base.retrieve_and_generate(
            query="What is Amazon S3 Vectors used for?",
            top_k=3,
        )

        assert answer is not None
        assert len(answer) > 0

        if is_local:
            # ローカルモードの場合は Mock レスポンスを確認
            assert "Mock" in answer or "vector" in answer.lower()

    def test_list_documents(self, knowledge_base, sample_documents):
        """ドキュメント一覧テスト"""
        # ドキュメント取り込み
        knowledge_base.ingest_documents(sample_documents)

        # 一覧取得
        docs = knowledge_base.list_documents(limit=10)

        assert len(docs) > 0
        assert "id" in docs[0] or "content" in docs[0]

    def test_empty_query_result(self, knowledge_base, sample_documents):
        """関連ドキュメントがない場合のテスト"""
        # ドキュメント取り込み
        knowledge_base.ingest_documents(sample_documents)

        # 関連性の低いクエリ
        results = knowledge_base.retrieve(
            query="recipe for chocolate cake",
            top_k=3,
        )

        # 結果は0件または低スコア
        if results:
            assert all(r.score < 0.5 for r in results)

