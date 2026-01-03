"""
In-Memory Document Repository

テスト・開発用のインメモリ実装。
本番では S3 Vector Store に置き換え。
"""

import asyncio
from typing import Optional

from services.search.domain.entities.document import (
    Document,
    DocumentId,
    SearchResult,
)
from shared.domain.value_objects.entity_id import VectorEmbedding


class InMemoryDocumentRepository:
    """
    Document リポジトリのインメモリ実装
    
    コサイン類似度によるベクトル検索を実装。
    """
    
    def __init__(self):
        self._documents: dict[str, Document] = {}
        self._lock = asyncio.Lock()
    
    async def save(self, document: Document) -> None:
        """ドキュメントを保存"""
        async with self._lock:
            self._documents[str(document.id)] = document
    
    async def find_by_id(self, document_id: DocumentId) -> Optional[Document]:
        """ID でドキュメントを取得"""
        return self._documents.get(str(document_id))
    
    async def delete(self, document_id: DocumentId) -> bool:
        """ドキュメントを削除"""
        async with self._lock:
            key = str(document_id)
            if key in self._documents:
                del self._documents[key]
                return True
            return False
    
    async def search(
        self,
        query_embedding: VectorEmbedding,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """ベクトル検索"""
        results: list[tuple[Document, float]] = []
        
        for document in self._documents.values():
            if document.embedding is None:
                continue
            
            # コサイン類似度計算
            score = query_embedding.cosine_similarity(document.embedding)
            
            if score >= min_score:
                results.append((document, score))
        
        # スコア順にソート
        results.sort(key=lambda x: x[1], reverse=True)
        
        # top_k 件を返す
        return [
            SearchResult(
                document=doc,
                score=score,
                highlights=[doc.content[:100]],
            )
            for doc, score in results[:top_k]
        ]
    
    async def count(self) -> int:
        """ドキュメント数を取得"""
        return len(self._documents)
    
    async def clear(self) -> None:
        """全ドキュメントを削除（テスト用）"""
        async with self._lock:
            self._documents.clear()
