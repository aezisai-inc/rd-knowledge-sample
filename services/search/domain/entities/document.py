"""
Document Entity - Search Bounded Context

ベクトル検索用のドキュメントエンティティ。
S3 Vector Store を使用（OpenSearch 不使用でコスト最適化）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.domain.value_objects.entity_id import VectorEmbedding


@dataclass(frozen=True)
class DocumentId:
    """ドキュメント識別子"""
    
    value: str
    
    @classmethod
    def generate(cls) -> DocumentId:
        return cls(str(uuid4()))
    
    @classmethod
    def from_string(cls, value: str) -> DocumentId:
        return cls(value)
    
    def __str__(self) -> str:
        return self.value


@dataclass
class Document:
    """
    ドキュメントエンティティ
    
    ベクトル検索の対象となるドキュメント。
    コンテンツ + 埋め込みベクトル + メタデータで構成。
    """
    
    id: DocumentId
    content: str
    embedding: Optional[VectorEmbedding] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    @classmethod
    def create(
        cls,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Document:
        """ファクトリメソッド: 新しいドキュメントを作成"""
        if not content or not content.strip():
            raise ValueError("Document content cannot be empty")
        
        return cls(
            id=DocumentId.generate(),
            content=content,
            metadata=metadata or {},
        )
    
    def set_embedding(self, embedding: VectorEmbedding) -> None:
        """埋め込みベクトルを設定"""
        self.embedding = embedding
        self.updated_at = datetime.now(timezone.utc)
    
    def update_content(self, content: str) -> None:
        """コンテンツを更新"""
        if not content or not content.strip():
            raise ValueError("Document content cannot be empty")
        
        self.content = content
        self.embedding = None  # 埋め込みは再計算が必要
        self.updated_at = datetime.now(timezone.utc)
    
    def add_metadata(self, key: str, value: Any) -> None:
        """メタデータを追加"""
        self.metadata[key] = value
        self.updated_at = datetime.now(timezone.utc)
    
    @property
    def has_embedding(self) -> bool:
        """埋め込みベクトルを持っているか"""
        return self.embedding is not None
    
    @property
    def content_length(self) -> int:
        """コンテンツの文字数"""
        return len(self.content)
    
    def to_dict(self) -> dict[str, Any]:
        """シリアライズ可能な辞書に変換"""
        return {
            "id": str(self.id),
            "content": self.content,
            "embedding": list(self.embedding.values) if self.embedding else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        """辞書からドキュメントを復元"""
        embedding = None
        if data.get("embedding"):
            embedding = VectorEmbedding.from_list(data["embedding"])
        
        return cls(
            id=DocumentId.from_string(data["id"]),
            content=data["content"],
            embedding=embedding,
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )


@dataclass(frozen=True)
class SearchResult:
    """検索結果"""
    
    document: Document
    score: float
    highlights: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """シリアライズ可能な辞書に変換"""
        return {
            "document": self.document.to_dict(),
            "score": self.score,
            "highlights": self.highlights,
        }


@dataclass
class SearchQuery:
    """検索クエリ"""
    
    query_text: str
    top_k: int = 10
    min_score: float = 0.0
    metadata_filter: Optional[dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.query_text or not self.query_text.strip():
            raise ValueError("Query text cannot be empty")
        if self.top_k < 1:
            raise ValueError("top_k must be at least 1")
        if self.min_score < 0.0 or self.min_score > 1.0:
            raise ValueError("min_score must be between 0.0 and 1.0")


# Export
__all__ = [
    "Document",
    "DocumentId",
    "SearchResult",
    "SearchQuery",
]
