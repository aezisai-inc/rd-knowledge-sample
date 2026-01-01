"""
ローカル KnowledgeBase アダプタ

Ollama + ChromaDB / または Mock による KnowledgeBase Protocol 実装。
本番環境では Bedrock Knowledge Base を使用。

Usage:
    # Mock モード（外部依存なし）
    kb = LocalKnowledgeBase(mode="mock")
    
    # Ollama + ChromaDB モード
    kb = LocalKnowledgeBase(
        mode="ollama",
        ollama_base_url="http://localhost:11434",
        model="llama3.2",
        embedding_model="nomic-embed-text",
    )
    
    kb.ingest_documents([{"content": "...", "metadata": {...}}])
    results = kb.retrieve("検索クエリ", top_k=5)
    answer = kb.retrieve_and_generate("質問")
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ...interfaces import SearchResult

logger = logging.getLogger(__name__)


class LocalKnowledgeBase:
    """
    ローカル KnowledgeBase 実装

    モード:
    - "mock": 外部依存なしのモック実装（開発・テスト用）
    - "ollama": Ollama + ChromaDB による本格実装
    """

    def __init__(
        self,
        mode: str = "mock",
        ollama_base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        embedding_model: str = "nomic-embed-text",
        persist_dir: str | None = None,
        chroma_host: str = "localhost",
        chroma_port: int = 8000,
    ):
        """
        Args:
            mode: "mock" または "ollama"
            ollama_base_url: Ollama API エンドポイント
            model: 生成用モデル名
            embedding_model: Embedding モデル名
            persist_dir: ドキュメント永続化ディレクトリ
            chroma_host: ChromaDB ホスト
            chroma_port: ChromaDB ポート
        """
        self.mode = mode
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.embedding_model = embedding_model
        self.persist_dir = Path(persist_dir) if persist_dir else None
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port

        # Mock モード用のドキュメントストア
        self._documents: dict[str, dict[str, Any]] = {}
        self._embeddings: dict[str, list[float]] = {}

        # ChromaDB クライアント（Ollama モード時）
        self._chroma_client = None
        self._chroma_collection = None

        if mode == "ollama":
            self._init_ollama_mode()
        else:
            logger.info("LocalKnowledgeBase initialized in mock mode")

        # 永続化ディレクトリから読み込み
        if self.persist_dir:
            self._load_from_disk()

    def _init_ollama_mode(self) -> None:
        """Ollama + ChromaDB モードの初期化"""
        try:
            import chromadb
            from chromadb.config import Settings

            self._chroma_client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port,
                settings=Settings(anonymized_telemetry=False),
            )
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name="local_knowledge_base",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"LocalKnowledgeBase initialized with Ollama ({self.ollama_base_url}) + ChromaDB"
            )
        except ImportError:
            logger.warning("chromadb not installed, falling back to mock mode")
            self.mode = "mock"
        except Exception as e:
            logger.warning(f"ChromaDB connection failed: {e}, falling back to mock mode")
            self.mode = "mock"

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """ドキュメント検索"""
        if self.mode == "ollama" and self._chroma_collection:
            return self._retrieve_ollama(query, top_k, filter)
        return self._retrieve_mock(query, top_k, filter)

    def _retrieve_mock(
        self,
        query: str,
        top_k: int,
        filter: dict[str, Any] | None,
    ) -> list[SearchResult]:
        """Mock モードの検索（キーワードマッチング）"""
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for doc_id, doc in self._documents.items():
            content = doc.get("content", "").lower()
            metadata = doc.get("metadata", {})

            # フィルタチェック
            if filter:
                if not self._match_filter(metadata, filter):
                    continue

            # 簡易スコアリング（単語マッチ数）
            content_words = set(content.split())
            match_count = len(query_words & content_words)

            if match_count > 0:
                score = match_count / len(query_words)
                results.append(
                    SearchResult(
                        key=doc_id,
                        score=score,
                        metadata=metadata,
                        content=doc.get("content", "")[:500],  # 最初の500文字
                    )
                )

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def _retrieve_ollama(
        self,
        query: str,
        top_k: int,
        filter: dict[str, Any] | None,
    ) -> list[SearchResult]:
        """Ollama + ChromaDB モードの検索"""
        try:
            # クエリの埋め込み取得
            query_embedding = self._get_embedding(query)

            # ChromaDB で検索
            where_filter = filter if filter else None
            results = self._chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            search_results = []
            if results and results["ids"]:
                for i, doc_id in enumerate(results["ids"][0]):
                    # distance を similarity に変換（cosine: 1 - distance）
                    distance = results["distances"][0][i] if results["distances"] else 0
                    score = 1 - distance

                    search_results.append(
                        SearchResult(
                            key=doc_id,
                            score=score,
                            metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                            content=results["documents"][0][i] if results["documents"] else "",
                        )
                    )

            return search_results

        except Exception as e:
            logger.error(f"ChromaDB query failed: {e}")
            return self._retrieve_mock(query, top_k, filter)

    def retrieve_and_generate(
        self,
        query: str,
        model_id: str | None = None,
        top_k: int = 5,
    ) -> str:
        """検索 + 回答生成 (RAG)"""
        # コンテキスト取得
        results = self.retrieve(query, top_k=top_k)
        context = "\n\n".join([r.content or "" for r in results if r.content])

        if self.mode == "ollama":
            return self._generate_ollama(query, context, model_id)
        return self._generate_mock(query, context)

    def _generate_mock(self, query: str, context: str) -> str:
        """Mock モードの回答生成"""
        if not context:
            return f"[Mock Response] No relevant documents found for: {query}"

        return f"""[Mock Response]
Query: {query}

Based on the following context:
{context[:500]}...

This is a mock response. In production, Bedrock KB would generate a proper answer.
"""

    def _generate_ollama(
        self,
        query: str,
        context: str,
        model_id: str | None,
    ) -> str:
        """Ollama モードの回答生成"""
        try:
            import httpx

            model = model_id or self.model
            prompt = f"""以下のコンテキストを参考に、質問に回答してください。

コンテキスト:
{context}

質問: {query}

回答:"""

            response = httpx.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json().get("response", "")

        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return self._generate_mock(query, context)

    def ingest_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> int:
        """ドキュメント取り込み"""
        count = 0

        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            doc_id = doc.get("id") or self._generate_doc_id(content)

            # Mock モード用にローカル保存
            self._documents[doc_id] = {
                "content": content,
                "metadata": metadata,
                "ingested_at": datetime.now().isoformat(),
            }

            # Ollama モードの場合は ChromaDB にも追加
            if self.mode == "ollama" and self._chroma_collection:
                try:
                    embedding = self._get_embedding(content)
                    self._chroma_collection.add(
                        ids=[doc_id],
                        documents=[content],
                        embeddings=[embedding],
                        metadatas=[metadata],
                    )
                except Exception as e:
                    logger.error(f"Failed to add document to ChromaDB: {e}")

            count += 1

        logger.info(f"Ingested {count} documents")
        self._persist_to_disk()
        return count

    def list_documents(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """ドキュメント一覧"""
        docs = []
        for doc_id, doc in list(self._documents.items())[:limit]:
            docs.append(
                {
                    "id": doc_id,
                    "content": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                    "metadata": doc.get("metadata", {}),
                    "ingested_at": doc.get("ingested_at"),
                }
            )
        return docs

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _get_embedding(self, text: str) -> list[float]:
        """Ollama で埋め込みベクトル取得"""
        try:
            import httpx

            response = httpx.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json().get("embedding", [])

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # フォールバック: 簡易ハッシュベクトル（デモ用）
            return self._generate_mock_embedding(text)

    def _generate_mock_embedding(self, text: str, dimension: int = 384) -> list[float]:
        """Mock 埋め込みベクトル生成"""
        import hashlib

        hash_bytes = hashlib.sha256(text.encode()).digest()
        # ハッシュを正規化した浮動小数点配列に変換
        return [float(b) / 255.0 for b in (hash_bytes * (dimension // len(hash_bytes) + 1))[:dimension]]

    def _generate_doc_id(self, content: str) -> str:
        """ドキュメント ID 生成"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"doc-{content_hash}-{uuid.uuid4().hex[:8]}"

    def _match_filter(self, metadata: dict[str, Any], filter: dict[str, Any]) -> bool:
        """メタデータフィルタマッチング"""
        for key, value in filter.items():
            if key not in metadata:
                return False
            if metadata[key] != value:
                return False
        return True

    def _persist_to_disk(self) -> None:
        """ディスクに永続化"""
        if not self.persist_dir:
            return

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        docs_file = self.persist_dir / "documents.json"
        docs_file.write_text(json.dumps(self._documents, ensure_ascii=False, indent=2))

    def _load_from_disk(self) -> None:
        """ディスクから読み込み"""
        if not self.persist_dir:
            return

        docs_file = self.persist_dir / "documents.json"
        if docs_file.exists():
            try:
                self._documents = json.loads(docs_file.read_text())
                logger.info(f"Loaded {len(self._documents)} documents from disk")
            except Exception as e:
                logger.error(f"Failed to load documents: {e}")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        """統計情報取得"""
        return {
            "mode": self.mode,
            "document_count": len(self._documents),
            "model": self.model,
            "embedding_model": self.embedding_model,
        }

    def clear(self) -> None:
        """全ドキュメント削除"""
        self._documents.clear()
        self._embeddings.clear()

        if self.mode == "ollama" and self._chroma_client:
            try:
                self._chroma_client.delete_collection("local_knowledge_base")
                self._chroma_collection = self._chroma_client.get_or_create_collection(
                    name="local_knowledge_base",
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                logger.error(f"Failed to clear ChromaDB collection: {e}")

        self._persist_to_disk()
        logger.info("Cleared all documents")
