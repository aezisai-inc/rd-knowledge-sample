"""
Search Handlers - CQRS Application Layer

ベクトル検索の Command/Query ハンドラ。
S3 Vector Store を使用（コスト最適化）。
"""

from dataclasses import dataclass
from typing import Any, Optional, Protocol

from services.search.domain.entities.document import (
    Document,
    DocumentId,
    SearchResult,
    SearchQuery,
)
from shared.domain.value_objects.entity_id import VectorEmbedding


# ============================================================================
# Repository Protocol
# ============================================================================

class DocumentRepository(Protocol):
    """ドキュメントリポジトリインターフェース"""
    
    async def save(self, document: Document) -> None:
        ...
    
    async def find_by_id(self, document_id: DocumentId) -> Optional[Document]:
        ...
    
    async def delete(self, document_id: DocumentId) -> bool:
        ...
    
    async def search(
        self,
        query_embedding: VectorEmbedding,
        top_k: int,
        min_score: float,
    ) -> list[SearchResult]:
        ...


class EmbeddingService(Protocol):
    """埋め込み生成サービスインターフェース"""
    
    async def embed(self, text: str) -> VectorEmbedding:
        ...
    
    async def embed_batch(self, texts: list[str]) -> list[VectorEmbedding]:
        ...


# ============================================================================
# Commands
# ============================================================================

@dataclass(frozen=True)
class IndexDocumentCommand:
    """ドキュメントインデックスコマンド"""
    content: str
    metadata: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class DeleteDocumentCommand:
    """ドキュメント削除コマンド"""
    document_id: str


# ============================================================================
# Queries
# ============================================================================

@dataclass(frozen=True)
class SearchDocumentsQuery:
    """ドキュメント検索クエリ"""
    query: str
    top_k: int = 10
    min_score: float = 0.0
    metadata_filter: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class GetDocumentQuery:
    """ドキュメント取得クエリ"""
    document_id: str


# ============================================================================
# Results
# ============================================================================

@dataclass
class IndexResult:
    """インデックス結果"""
    document_id: str
    content_length: int


@dataclass
class SearchResultDto:
    """検索結果 DTO"""
    results: list[dict[str, Any]]
    total_count: int
    query: str


# ============================================================================
# Handlers
# ============================================================================

class IndexHandler:
    """ドキュメントインデックスハンドラ"""
    
    def __init__(
        self,
        repository: DocumentRepository,
        embedding_service: EmbeddingService,
    ):
        self._repository = repository
        self._embedding_service = embedding_service
    
    async def handle(self, command: IndexDocumentCommand) -> IndexResult:
        """ドキュメントをインデックス"""
        # 1. ドキュメント作成
        document = Document.create(
            content=command.content,
            metadata=command.metadata,
        )
        
        # 2. 埋め込みベクトル生成
        embedding = await self._embedding_service.embed(command.content)
        document.set_embedding(embedding)
        
        # 3. 保存
        await self._repository.save(document)
        
        return IndexResult(
            document_id=str(document.id),
            content_length=document.content_length,
        )


class SearchHandler:
    """ドキュメント検索ハンドラ"""
    
    def __init__(
        self,
        repository: DocumentRepository,
        embedding_service: EmbeddingService,
    ):
        self._repository = repository
        self._embedding_service = embedding_service
    
    async def handle(self, query: SearchDocumentsQuery) -> SearchResultDto:
        """ドキュメントを検索"""
        # 1. クエリの埋め込みベクトル生成
        query_embedding = await self._embedding_service.embed(query.query)
        
        # 2. ベクトル検索実行
        results = await self._repository.search(
            query_embedding=query_embedding,
            top_k=query.top_k,
            min_score=query.min_score,
        )
        
        return SearchResultDto(
            results=[r.to_dict() for r in results],
            total_count=len(results),
            query=query.query,
        )


class GetDocumentHandler:
    """ドキュメント取得ハンドラ"""
    
    def __init__(self, repository: DocumentRepository):
        self._repository = repository
    
    async def handle(self, query: GetDocumentQuery) -> Optional[dict[str, Any]]:
        """ドキュメントを取得"""
        document = await self._repository.find_by_id(
            DocumentId.from_string(query.document_id)
        )
        
        if document is None:
            return None
        
        return document.to_dict()


class DeleteHandler:
    """ドキュメント削除ハンドラ"""
    
    def __init__(self, repository: DocumentRepository):
        self._repository = repository
    
    async def handle(self, command: DeleteDocumentCommand) -> bool:
        """ドキュメントを削除"""
        return await self._repository.delete(
            DocumentId.from_string(command.document_id)
        )
