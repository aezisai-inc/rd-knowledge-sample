"""
AWS KnowledgeBase アダプタ

boto3 bedrock-agent / bedrock-agent-runtime による Bedrock Knowledge Base 実装。
MEMORY_ARCHITECTURE_DESIGN.md の 02_bedrock_kb_with_s3vectors.py パターンを使用。
"""

from __future__ import annotations

import logging
from typing import Any

from ...interfaces import SearchResult

logger = logging.getLogger(__name__)


class AWSKnowledgeBase:
    """
    AWS KnowledgeBase 実装 (Bedrock Knowledge Base)

    Usage:
        kb = AWSKnowledgeBase(region="us-west-2", knowledge_base_id="KB123")
        results = kb.retrieve("質問内容", top_k=5)
        answer = kb.retrieve_and_generate("質問内容")
    """

    def __init__(
        self,
        region: str = "us-west-2",
        knowledge_base_id: str = "",
        generation_model_arn: str = "",
    ):
        """
        Args:
            region: AWS リージョン
            knowledge_base_id: Knowledge Base ID
            generation_model_arn: 回答生成モデルARN
        """
        import boto3

        self.region = region
        self.knowledge_base_id = knowledge_base_id
        self.generation_model_arn = generation_model_arn or (
            f"arn:aws:bedrock:{region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
        )

        # Bedrock Agent Runtime クライアント
        self._runtime = boto3.client("bedrock-agent-runtime", region_name=region)

        # Bedrock Agent クライアント（KB管理用）
        self._agent = boto3.client("bedrock-agent", region_name=region)

        logger.info(f"AWSKnowledgeBase initialized (kb_id={knowledge_base_id})")

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """ドキュメント検索"""
        retrieval_config = {
            "vectorSearchConfiguration": {
                "numberOfResults": top_k,
            }
        }

        if filter:
            retrieval_config["vectorSearchConfiguration"]["filter"] = filter

        response = self._runtime.retrieve(
            knowledgeBaseId=self.knowledge_base_id,
            retrievalQuery={"text": query},
            retrievalConfiguration=retrieval_config,
        )

        results = []
        for result in response.get("retrievalResults", []):
            content = result.get("content", {}).get("text", "")
            metadata = result.get("metadata", {})
            score = result.get("score", 0.0)
            location = result.get("location", {})

            # メタデータにロケーション情報を追加
            if location:
                metadata["source"] = location.get("s3Location", {}).get("uri", "")

            results.append(
                SearchResult(
                    key=metadata.get("source", ""),
                    score=score,
                    metadata=metadata,
                    content=content,
                )
            )

        return results

    def retrieve_and_generate(
        self,
        query: str,
        model_id: str | None = None,
        top_k: int = 5,
    ) -> str:
        """検索 + 回答生成 (RAG)"""
        response = self._runtime.retrieve_and_generate(
            input={"text": query},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": self.knowledge_base_id,
                    "modelArn": model_id or self.generation_model_arn,
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": {
                            "numberOfResults": top_k,
                        }
                    },
                },
            },
        )

        return response.get("output", {}).get("text", "")

    def ingest_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> int:
        """
        ドキュメント取り込み

        Note:
            Bedrock KB では S3 データソースを使用するため、
            このメソッドは Ingestion Job をトリガーする。
        """
        # データソースIDを取得
        data_sources = self._agent.list_data_sources(
            knowledgeBaseId=self.knowledge_base_id,
        ).get("dataSourceSummaries", [])

        if not data_sources:
            logger.warning("No data sources found for KB")
            return 0

        # Ingestion Job を開始
        data_source_id = data_sources[0]["dataSourceId"]
        self._agent.start_ingestion_job(
            knowledgeBaseId=self.knowledge_base_id,
            dataSourceId=data_source_id,
        )

        logger.info(f"Started ingestion job for KB {self.knowledge_base_id}")
        return len(documents)

    def list_documents(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """ドキュメント一覧（データソース一覧を返す）"""
        data_sources = self._agent.list_data_sources(
            knowledgeBaseId=self.knowledge_base_id,
            maxResults=limit,
        ).get("dataSourceSummaries", [])

        return [
            {
                "id": ds["dataSourceId"],
                "name": ds.get("name", ""),
                "status": ds.get("status", ""),
            }
            for ds in data_sources
        ]

