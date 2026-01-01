"""
AWS MemoryStore アダプタ

boto3 bedrock-agentcore による AgentCore Memory 実装。
MEMORY_ARCHITECTURE_DESIGN.md の 05_agentcore_memory.py パターンを使用。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ...interfaces import MemoryEvent, MemoryRecord

logger = logging.getLogger(__name__)


class AWSMemoryStore:
    """
    AWS MemoryStore 実装 (AgentCore Memory)

    Usage:
        memory = AWSMemoryStore(region="us-east-1", memory_id="mem-123")
        memory.create_event([MemoryEvent(...)])
        records = memory.retrieve_records(actor_id="user-1", query="過去の会話")
    """

    def __init__(
        self,
        region: str = "us-east-1",
        memory_id: str = "",
    ):
        """
        Args:
            region: AWS リージョン
            memory_id: Memory ID
        """
        import boto3

        self.region = region
        self.memory_id = memory_id

        # AgentCore データクライアント
        self._data_client = boto3.client("bedrock-agentcore", region_name=region)

        # AgentCore コントロールクライアント（Memory作成用）
        self._control_client = boto3.client("bedrock-agentcore-control", region_name=region)

        logger.info(f"AWSMemoryStore initialized (memory_id={memory_id})")

    def create_event(
        self,
        events: list[MemoryEvent],
    ) -> str:
        """イベント保存（Short-term Memory）"""
        # 会話形式のペイロードを構築
        payload = []
        for event in events:
            payload.append(
                {
                    "conversational": {
                        "content": {"text": event.content},
                        "role": event.role,
                    }
                }
            )

        # 最初のイベントからメタデータを取得
        first_event = events[0]

        response = self._data_client.create_event(
            memoryId=self.memory_id,
            actorId=first_event.actor_id,
            sessionId=first_event.session_id,
            eventTimestamp=first_event.timestamp,
            payload=payload,
        )

        event_id = response.get("eventId", "")
        logger.info(f"Created event {event_id}")
        return event_id

    def retrieve_records(
        self,
        actor_id: str,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
    ) -> list[MemoryRecord]:
        """メモリ検索（セマンティック検索）"""
        response = self._data_client.retrieve_memory_records(
            memoryId=self.memory_id,
            actorId=actor_id,
            query=query,
            maxResults=limit,
        )

        results = []
        for record in response.get("memoryRecords", []):
            # メモリタイプでフィルタ
            record_type = record.get("memoryType", "episodic")
            if memory_types and record_type not in memory_types:
                continue

            results.append(
                MemoryRecord(
                    record_id=record.get("recordId", ""),
                    content=record.get("content", ""),
                    memory_type=record_type,
                    timestamp=datetime.fromisoformat(
                        record.get("timestamp", datetime.now().isoformat())
                    ),
                    score=record.get("relevanceScore", 0.0),
                    metadata=record.get("metadata", {}),
                )
            )

        return results

    def get_session_history(
        self,
        actor_id: str,
        session_id: str,
        limit: int = 50,
    ) -> list[MemoryEvent]:
        """セッション履歴取得"""
        response = self._data_client.list_events(
            memoryId=self.memory_id,
            actorId=actor_id,
            sessionId=session_id,
            maxResults=limit,
        )

        events = []
        for event in response.get("events", []):
            payload = event.get("payload", [])
            for item in payload:
                if "conversational" in item:
                    conv = item["conversational"]
                    events.append(
                        MemoryEvent(
                            actor_id=actor_id,
                            session_id=session_id,
                            role=conv.get("role", "USER"),
                            content=conv.get("content", {}).get("text", ""),
                            timestamp=datetime.fromisoformat(
                                event.get("eventTimestamp", datetime.now().isoformat())
                            ),
                        )
                    )

        return events

    def delete_actor_memory(
        self,
        actor_id: str,
    ) -> bool:
        """アクターのメモリ全削除"""
        try:
            self._data_client.delete_actor_memory(
                memoryId=self.memory_id,
                actorId=actor_id,
            )
            logger.info(f"Deleted memory for actor '{actor_id}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete actor memory: {e}")
            return False

    # =========================================================================
    # Memory Management
    # =========================================================================

    def create_memory(
        self,
        name: str,
        description: str = "",
        event_expiry_days: int = 90,
    ) -> str:
        """
        Memory リソース作成

        Returns:
            作成された Memory ID
        """
        response = self._control_client.create_memory(
            name=name,
            description=description,
            eventExpiryDuration=event_expiry_days,
            memoryStrategies=[
                {
                    "summaryMemoryStrategy": {
                        "name": "SessionSummarizer",
                        "namespaces": ["/summaries/{actorId}/{sessionId}"],
                    }
                },
                {
                    "userPreferenceMemoryStrategy": {
                        "name": "PreferenceLearner",
                        "namespaces": ["/preferences/{actorId}"],
                    }
                },
                {
                    "semanticMemoryStrategy": {
                        "name": "FactExtractor",
                        "namespaces": ["/facts/{actorId}"],
                    }
                },
            ],
        )

        memory_id = response["memory"]["id"]
        self.memory_id = memory_id
        logger.info(f"Created memory: {memory_id}")
        return memory_id

