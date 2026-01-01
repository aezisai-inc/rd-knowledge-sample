"""
VectorStore E2E テスト

ローカル環境と AWS 環境の両方で同一テストケースを実行。
"""

from __future__ import annotations

import pytest

from src.interfaces import SearchResult, VectorRecord


class TestVectorStore:
    """VectorStore Protocol の E2E テスト"""

    def test_create_index(self, vector_store):
        """インデックス作成テスト"""
        index_name = "test-index-create"

        # インデックス作成
        result = vector_store.create_index(
            index_name=index_name,
            dimension=128,
            distance_metric="cosine",
        )

        assert result == index_name

        # クリーンアップ
        vector_store.delete_index(index_name)

    def test_put_and_query_vectors(self, vector_store, sample_vectors):
        """ベクトル挿入・検索テスト"""
        index_name = "test-index-query"

        # インデックス作成
        vector_store.create_index(index_name=index_name, dimension=128)

        # ベクトル挿入
        records = [
            VectorRecord(
                key=v["key"],
                vector=v["vector"],
                metadata=v["metadata"],
            )
            for v in sample_vectors
        ]
        count = vector_store.put_vectors(index_name=index_name, vectors=records)

        assert count == len(sample_vectors)

        # 検索（最初のベクトルに似たものを検索）
        query_vector = sample_vectors[0]["vector"]
        results = vector_store.query_vectors(
            index_name=index_name,
            query_vector=query_vector,
            top_k=3,
        )

        assert len(results) > 0
        assert isinstance(results[0], SearchResult)
        assert results[0].key == sample_vectors[0]["key"]  # 同一ベクトルが最も類似

        # クリーンアップ
        vector_store.delete_index(index_name)

    def test_query_with_filter(self, vector_store, sample_vectors):
        """メタデータフィルタ付き検索テスト"""
        index_name = "test-index-filter"

        # インデックス作成・ベクトル挿入
        vector_store.create_index(index_name=index_name, dimension=128)
        records = [
            VectorRecord(
                key=v["key"],
                vector=v["vector"],
                metadata=v["metadata"],
            )
            for v in sample_vectors
        ]
        vector_store.put_vectors(index_name=index_name, vectors=records)

        # フィルタ付き検索
        query_vector = [0.15] * 128
        results = vector_store.query_vectors(
            index_name=index_name,
            query_vector=query_vector,
            top_k=10,
            filter={"category": "tech"},
        )

        # tech カテゴリのみが返されるはず
        assert all(r.metadata.get("category") == "tech" for r in results)

        # クリーンアップ
        vector_store.delete_index(index_name)

    def test_delete_vectors(self, vector_store, sample_vectors):
        """ベクトル削除テスト"""
        index_name = "test-index-delete"

        # インデックス作成・ベクトル挿入
        vector_store.create_index(index_name=index_name, dimension=128)
        records = [
            VectorRecord(
                key=v["key"],
                vector=v["vector"],
                metadata=v["metadata"],
            )
            for v in sample_vectors
        ]
        vector_store.put_vectors(index_name=index_name, vectors=records)

        # 削除
        deleted = vector_store.delete_vectors(
            index_name=index_name,
            keys=["doc-1", "doc-2"],
        )

        assert deleted == 2

        # 削除されたか確認
        result = vector_store.get_vector(index_name=index_name, key="doc-1")
        assert result is None

        # クリーンアップ
        vector_store.delete_index(index_name)

    def test_get_vector(self, vector_store, sample_vectors):
        """単一ベクトル取得テスト"""
        index_name = "test-index-get"

        # インデックス作成・ベクトル挿入
        vector_store.create_index(index_name=index_name, dimension=128)
        records = [
            VectorRecord(
                key=v["key"],
                vector=v["vector"],
                metadata=v["metadata"],
            )
            for v in sample_vectors
        ]
        vector_store.put_vectors(index_name=index_name, vectors=records)

        # 取得
        result = vector_store.get_vector(index_name=index_name, key="doc-1")

        assert result is not None
        assert isinstance(result, VectorRecord)
        assert result.key == "doc-1"
        assert result.metadata["title"] == "Document 1"

        # クリーンアップ
        vector_store.delete_index(index_name)

    def test_index_not_found_error(self, vector_store):
        """存在しないインデックスへのアクセスエラーテスト"""
        with pytest.raises(ValueError):
            vector_store.query_vectors(
                index_name="nonexistent-index",
                query_vector=[0.1] * 128,
                top_k=5,
            )
