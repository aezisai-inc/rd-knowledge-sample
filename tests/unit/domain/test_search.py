"""
Search Domain Unit Tests

TDD: Document エンティティと SearchResult のテスト。
"""

import pytest
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(__file__).replace('/tests/unit/domain/test_search.py', ''))

from services.search.domain.entities.document import (
    Document,
    DocumentId,
    SearchResult,
    SearchQuery,
)
from shared.domain.value_objects.entity_id import VectorEmbedding


class TestDocument:
    """Document エンティティのテスト"""
    
    def test_create_document_should_generate_id(self):
        """ドキュメント作成時にIDが生成される"""
        doc = Document.create(content="Test content")
        
        assert doc.id is not None
        assert isinstance(doc.id, DocumentId)
    
    def test_create_document_should_set_content(self):
        """ドキュメント作成時にコンテンツが設定される"""
        doc = Document.create(content="Test content", metadata={"source": "test"})
        
        assert doc.content == "Test content"
        assert doc.metadata == {"source": "test"}
    
    def test_create_document_with_empty_content_should_raise_error(self):
        """空コンテンツでドキュメント作成はエラー"""
        with pytest.raises(ValueError, match="cannot be empty"):
            Document.create(content="")
    
    def test_create_document_with_whitespace_only_should_raise_error(self):
        """空白のみのコンテンツでドキュメント作成はエラー"""
        with pytest.raises(ValueError, match="cannot be empty"):
            Document.create(content="   ")
    
    def test_set_embedding_should_update_document(self):
        """埋め込み設定でドキュメントが更新される"""
        doc = Document.create(content="Test")
        embedding = VectorEmbedding.from_list([0.1, 0.2, 0.3])
        
        doc.set_embedding(embedding)
        
        assert doc.embedding == embedding
        assert doc.has_embedding is True
        assert doc.updated_at is not None
    
    def test_update_content_should_clear_embedding(self):
        """コンテンツ更新で埋め込みがクリアされる"""
        doc = Document.create(content="Original")
        doc.set_embedding(VectorEmbedding.from_list([0.1, 0.2]))
        
        doc.update_content("Updated")
        
        assert doc.content == "Updated"
        assert doc.embedding is None
        assert doc.has_embedding is False
    
    def test_content_length_should_return_correct_value(self):
        """content_length が正しい値を返す"""
        doc = Document.create(content="Hello World")
        
        assert doc.content_length == 11
    
    def test_to_dict_should_return_serializable_dict(self):
        """to_dict がシリアライズ可能な辞書を返す"""
        doc = Document.create(content="Test", metadata={"key": "value"})
        
        result = doc.to_dict()
        
        assert "id" in result
        assert result["content"] == "Test"
        assert result["metadata"] == {"key": "value"}
        assert "created_at" in result
    
    def test_from_dict_should_restore_document(self):
        """from_dict でドキュメントを復元できる"""
        original = Document.create(content="Test")
        original.set_embedding(VectorEmbedding.from_list([0.1, 0.2, 0.3]))
        
        data = original.to_dict()
        restored = Document.from_dict(data)
        
        assert str(restored.id) == str(original.id)
        assert restored.content == original.content


class TestSearchQuery:
    """SearchQuery のテスト"""
    
    def test_create_query_with_valid_params(self):
        """有効なパラメータでクエリ作成"""
        query = SearchQuery(query_text="test query", top_k=5, min_score=0.5)
        
        assert query.query_text == "test query"
        assert query.top_k == 5
        assert query.min_score == 0.5
    
    def test_create_query_with_empty_text_should_raise_error(self):
        """空のクエリテキストはエラー"""
        with pytest.raises(ValueError, match="cannot be empty"):
            SearchQuery(query_text="")
    
    def test_create_query_with_invalid_top_k_should_raise_error(self):
        """無効な top_k はエラー"""
        with pytest.raises(ValueError, match="must be at least 1"):
            SearchQuery(query_text="test", top_k=0)
    
    def test_create_query_with_invalid_min_score_should_raise_error(self):
        """無効な min_score はエラー"""
        with pytest.raises(ValueError, match="must be between"):
            SearchQuery(query_text="test", min_score=1.5)


class TestSearchResult:
    """SearchResult のテスト"""
    
    def test_search_result_to_dict(self):
        """SearchResult の to_dict"""
        doc = Document.create(content="Test document")
        result = SearchResult(document=doc, score=0.95, highlights=["Test"])
        
        data = result.to_dict()
        
        assert data["score"] == 0.95
        assert data["highlights"] == ["Test"]
        assert "document" in data


class TestVectorEmbedding:
    """VectorEmbedding のテスト"""
    
    def test_cosine_similarity_same_vector(self):
        """同じベクトルのコサイン類似度は1.0"""
        vec = VectorEmbedding.from_list([1.0, 0.0, 0.0])
        
        similarity = vec.cosine_similarity(vec)
        
        assert abs(similarity - 1.0) < 0.001
    
    def test_cosine_similarity_orthogonal_vectors(self):
        """直交ベクトルのコサイン類似度は0.0"""
        vec1 = VectorEmbedding.from_list([1.0, 0.0, 0.0])
        vec2 = VectorEmbedding.from_list([0.0, 1.0, 0.0])
        
        similarity = vec1.cosine_similarity(vec2)
        
        assert abs(similarity) < 0.001
    
    def test_cosine_similarity_opposite_vectors(self):
        """逆ベクトルのコサイン類似度は-1.0"""
        vec1 = VectorEmbedding.from_list([1.0, 0.0, 0.0])
        vec2 = VectorEmbedding.from_list([-1.0, 0.0, 0.0])
        
        similarity = vec1.cosine_similarity(vec2)
        
        assert abs(similarity + 1.0) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
