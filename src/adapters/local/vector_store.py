"""
ローカル VectorStore アダプタ

FAISS または In-memory による VectorStore Protocol 実装。
LocalStack S3 との連携もオプションでサポート。

Usage:
    store = LocalVectorStore()
    store.create_index("my-index", dimension=1024)
    
    store.put_vectors("my-index", [
        VectorRecord(key="doc-1", vector=[0.1, 0.2, ...], metadata={"title": "Doc 1"})
    ])
    
    results = store.query_vectors("my-index", query_vector, top_k=10)
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from ...interfaces import SearchResult, VectorRecord

logger = logging.getLogger(__name__)


class LocalVectorStore:
    """
    ローカル VectorStore 実装 (In-memory + NumPy)

    本番環境では S3 Vectors を使用。
    ローカルでは NumPy による cosine similarity 計算で代替。
    """

    def __init__(
        self,
        endpoint: str | None = None,
        persist_dir: str | None = None,
    ):
        """
        Args:
            endpoint: LocalStack エンドポイント（将来の拡張用）
            persist_dir: 永続化ディレクトリ（None の場合は In-memory）
        """
        self.endpoint = endpoint
        self.persist_dir = Path(persist_dir) if persist_dir else None

        # インデックス管理 {index_name: {"dimension": int, "metric": str, "vectors": {key: VectorRecord}}}
        self._indices: dict[str, dict[str, Any]] = {}

        # 永続化ディレクトリがあれば読み込み
        if self.persist_dir:
            self._load_from_disk()

        logger.info(f"LocalVectorStore initialized (persist_dir={persist_dir})")

    def create_index(
        self,
        index_name: str,
        dimension: int,
        distance_metric: str = "cosine",
    ) -> str:
        """インデックス作成"""
        if index_name in self._indices:
            logger.warning(f"Index '{index_name}' already exists")
            return index_name

        self._indices[index_name] = {
            "dimension": dimension,
            "metric": distance_metric,
            "vectors": {},
        }

        logger.info(f"Created index '{index_name}' (dimension={dimension}, metric={distance_metric})")
        self._persist_to_disk()
        return index_name

    def delete_index(self, index_name: str) -> bool:
        """インデックス削除"""
        if index_name not in self._indices:
            logger.warning(f"Index '{index_name}' not found")
            return False

        del self._indices[index_name]
        logger.info(f"Deleted index '{index_name}'")
        self._persist_to_disk()
        return True

    def put_vectors(
        self,
        index_name: str,
        vectors: list[VectorRecord],
    ) -> int:
        """ベクトル挿入"""
        if index_name not in self._indices:
            raise ValueError(f"Index '{index_name}' not found")

        index = self._indices[index_name]
        expected_dim = index["dimension"]
        count = 0

        for vec in vectors:
            if len(vec.vector) != expected_dim:
                logger.error(
                    f"Vector dimension mismatch: expected {expected_dim}, got {len(vec.vector)}"
                )
                continue

            # キーがなければ生成
            key = vec.key or str(uuid.uuid4())
            index["vectors"][key] = VectorRecord(
                key=key,
                vector=vec.vector,
                metadata=vec.metadata,
                namespace=vec.namespace,
            )
            count += 1

        logger.info(f"Inserted {count} vectors into '{index_name}'")
        self._persist_to_disk()
        return count

    def query_vectors(
        self,
        index_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """ベクトル検索 (Cosine Similarity)"""
        if index_name not in self._indices:
            raise ValueError(f"Index '{index_name}' not found")

        index = self._indices[index_name]
        vectors_dict = index["vectors"]

        if not vectors_dict:
            return []

        # NumPy 配列に変換
        query_np = np.array(query_vector)
        query_norm = np.linalg.norm(query_np)
        if query_norm == 0:
            logger.warning("Query vector has zero norm")
            return []

        results = []
        for key, record in vectors_dict.items():
            # メタデータフィルタ
            if filter:
                if not self._match_filter(record.metadata, filter):
                    continue

            # Cosine Similarity
            vec_np = np.array(record.vector)
            vec_norm = np.linalg.norm(vec_np)
            if vec_norm == 0:
                continue

            similarity = float(np.dot(query_np, vec_np) / (query_norm * vec_norm))
            results.append(
                SearchResult(
                    key=key,
                    score=similarity,
                    metadata=record.metadata,
                )
            )

        # スコア降順でソート
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def delete_vectors(
        self,
        index_name: str,
        keys: list[str],
    ) -> int:
        """ベクトル削除"""
        if index_name not in self._indices:
            raise ValueError(f"Index '{index_name}' not found")

        vectors_dict = self._indices[index_name]["vectors"]
        count = 0

        for key in keys:
            if key in vectors_dict:
                del vectors_dict[key]
                count += 1

        logger.info(f"Deleted {count} vectors from '{index_name}'")
        self._persist_to_disk()
        return count

    def get_vector(
        self,
        index_name: str,
        key: str,
    ) -> VectorRecord | None:
        """単一ベクトル取得"""
        if index_name not in self._indices:
            raise ValueError(f"Index '{index_name}' not found")

        return self._indices[index_name]["vectors"].get(key)

    # =========================================================================
    # Private Methods
    # =========================================================================

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

        for index_name, index_data in self._indices.items():
            index_file = self.persist_dir / f"{index_name}.json"
            serializable = {
                "dimension": index_data["dimension"],
                "metric": index_data["metric"],
                "vectors": {
                    k: {
                        "key": v.key,
                        "vector": v.vector,
                        "metadata": v.metadata,
                        "namespace": v.namespace,
                    }
                    for k, v in index_data["vectors"].items()
                },
            }
            index_file.write_text(json.dumps(serializable, ensure_ascii=False, indent=2))

    def _load_from_disk(self) -> None:
        """ディスクから読み込み"""
        if not self.persist_dir or not self.persist_dir.exists():
            return

        for index_file in self.persist_dir.glob("*.json"):
            try:
                data = json.loads(index_file.read_text())
                index_name = index_file.stem
                self._indices[index_name] = {
                    "dimension": data["dimension"],
                    "metric": data["metric"],
                    "vectors": {
                        k: VectorRecord(
                            key=v["key"],
                            vector=v["vector"],
                            metadata=v["metadata"],
                            namespace=v.get("namespace"),
                        )
                        for k, v in data["vectors"].items()
                    },
                }
                logger.info(f"Loaded index '{index_name}' from disk")
            except Exception as e:
                logger.error(f"Failed to load index from {index_file}: {e}")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def list_indices(self) -> list[str]:
        """インデックス一覧"""
        return list(self._indices.keys())

    def get_index_stats(self, index_name: str) -> dict[str, Any]:
        """インデックス統計"""
        if index_name not in self._indices:
            raise ValueError(f"Index '{index_name}' not found")

        index = self._indices[index_name]
        return {
            "name": index_name,
            "dimension": index["dimension"],
            "metric": index["metric"],
            "vector_count": len(index["vectors"]),
        }

