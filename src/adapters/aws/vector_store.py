"""
AWS VectorStore アダプタ

boto3 s3vectors クライアントによる S3 Vectors 実装。
MEMORY_ARCHITECTURE_DESIGN.md の 01_s3_vectors_direct.py パターンを使用。

Note:
    S3 Vectors は 2024年12月時点で Preview 版。
    us-east-1, us-west-2 リージョンで利用可能。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ...interfaces import SearchResult, VectorRecord

logger = logging.getLogger(__name__)


class AWSVectorStore:
    """
    AWS VectorStore 実装 (S3 Vectors)

    Usage:
        store = AWSVectorStore(region="us-west-2", bucket_name="my-vector-bucket")
        store.create_index("products", dimension=1024)
        store.put_vectors("products", [VectorRecord(...)])
        results = store.query_vectors("products", query_vector, top_k=10)
    """

    def __init__(
        self,
        region: str = "us-west-2",
        bucket_name: str = "",
    ):
        """
        Args:
            region: AWS リージョン
            bucket_name: Vector Bucket 名
        """
        import boto3

        self.region = region
        self.bucket_name = bucket_name

        # S3 Vectors クライアント
        self._client = boto3.client("s3vectors", region_name=region)

        # Bedrock Runtime (埋め込み生成用)
        self._bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)

        logger.info(f"AWSVectorStore initialized (region={region}, bucket={bucket_name})")

    def create_index(
        self,
        index_name: str,
        dimension: int,
        distance_metric: str = "cosine",
    ) -> str:
        """インデックス作成"""
        # Vector Bucket が未作成の場合は作成
        if not self.bucket_name:
            self.bucket_name = f"vector-bucket-{index_name}"
            self._client.create_vector_bucket(vectorBucketName=self.bucket_name)
            logger.info(f"Created vector bucket: {self.bucket_name}")

        # インデックス作成
        self._client.create_index(
            vectorBucketName=self.bucket_name,
            indexName=index_name,
            dimension=dimension,
            distanceMetric=distance_metric,
        )

        logger.info(f"Created index '{index_name}' (dimension={dimension})")
        return index_name

    def delete_index(self, index_name: str) -> bool:
        """インデックス削除"""
        try:
            self._client.delete_index(
                vectorBucketName=self.bucket_name,
                indexName=index_name,
            )
            logger.info(f"Deleted index '{index_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index '{index_name}': {e}")
            return False

    def put_vectors(
        self,
        index_name: str,
        vectors: list[VectorRecord],
    ) -> int:
        """ベクトル挿入"""
        s3_vectors = []
        for vec in vectors:
            s3_vectors.append(
                {
                    "key": vec.key,
                    "data": {"float32": vec.vector},
                    "metadata": vec.metadata,
                }
            )

        self._client.put_vectors(
            vectorBucketName=self.bucket_name,
            indexName=index_name,
            vectors=s3_vectors,
        )

        logger.info(f"Inserted {len(vectors)} vectors into '{index_name}'")
        return len(vectors)

    def query_vectors(
        self,
        index_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """ベクトル検索"""
        response = self._client.query_vectors(
            vectorBucketName=self.bucket_name,
            indexName=index_name,
            queryVector={"float32": query_vector},
            topK=top_k,
            filter=filter or {},
            returnMetadata=True,
        )

        results = []
        for vec in response.get("vectors", []):
            results.append(
                SearchResult(
                    key=vec["key"],
                    score=vec.get("score", 0.0),
                    metadata=vec.get("metadata", {}),
                )
            )

        return results

    def delete_vectors(
        self,
        index_name: str,
        keys: list[str],
    ) -> int:
        """ベクトル削除"""
        self._client.delete_vectors(
            vectorBucketName=self.bucket_name,
            indexName=index_name,
            keys=keys,
        )
        logger.info(f"Deleted {len(keys)} vectors from '{index_name}'")
        return len(keys)

    def get_vector(
        self,
        index_name: str,
        key: str,
    ) -> VectorRecord | None:
        """単一ベクトル取得"""
        try:
            response = self._client.get_vectors(
                vectorBucketName=self.bucket_name,
                indexName=index_name,
                keys=[key],
                returnMetadata=True,
            )
            vectors = response.get("vectors", [])
            if vectors:
                vec = vectors[0]
                return VectorRecord(
                    key=vec["key"],
                    vector=vec["data"]["float32"],
                    metadata=vec.get("metadata", {}),
                )
        except Exception as e:
            logger.error(f"Failed to get vector '{key}': {e}")
        return None

    # =========================================================================
    # Embedding Helper
    # =========================================================================

    def get_embedding(self, text: str, model_id: str = "amazon.titan-embed-text-v2:0") -> list[float]:
        """テキストから埋め込みベクトルを生成"""
        response = self._bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps({"inputText": text}),
        )
        result = json.loads(response["body"].read())
        return result["embedding"]

