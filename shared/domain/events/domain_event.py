"""
Domain Event Base Classes

Event Sourcing の基盤となるドメインイベント定義。
すべてのドメインイベントはこのクラスを継承する。
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent(ABC):
    """
    ドメインイベント基底クラス
    
    Event Sourcing パターンにおける不変イベント。
    一度作成されたイベントは変更されない（immutable）。
    """
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: str = ""
    aggregate_type: str = ""
    version: int = 1
    
    @property
    def event_type(self) -> str:
        """イベントタイプ名を返す"""
        return self.__class__.__name__
    
    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換（シリアライズ用）"""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "version": self.version,
            "payload": self._get_payload(),
        }
    
    def _get_payload(self) -> dict[str, Any]:
        """サブクラス固有のペイロードを返す"""
        # dataclass のフィールドを取得（基底クラスのフィールドを除外）
        base_fields = {"event_id", "occurred_at", "aggregate_id", "aggregate_type", "version"}
        return {
            k: v for k, v in self.__dict__.items()
            if k not in base_fields
        }


@dataclass(frozen=True)
class IntegrationEvent(DomainEvent):
    """
    統合イベント
    
    境界付けられたコンテキスト間で共有されるイベント。
    EventBridge などの外部イベントバスで配信される。
    """
    source_context: str = ""
    correlation_id: str = ""


# Memory Context Events
@dataclass(frozen=True)
class SessionStarted(DomainEvent):
    """セッション開始イベント"""
    actor_id: str = ""
    session_type: str = ""  # memory, multimodal, voice
    aggregate_type: str = "Session"


@dataclass(frozen=True)
class SessionEnded(DomainEvent):
    """セッション終了イベント"""
    duration_ms: int = 0
    event_count: int = 0
    aggregate_type: str = "Session"


@dataclass(frozen=True)
class MemoryEventCreated(DomainEvent):
    """メモリイベント作成イベント"""
    session_id: str = ""
    actor_id: str = ""
    role: str = ""  # USER, ASSISTANT, SYSTEM
    content: str = ""
    aggregate_type: str = "MemoryEvent"


@dataclass(frozen=True)
class MemoryRetrieved(DomainEvent):
    """メモリ取得イベント"""
    session_id: str = ""
    event_count: int = 0
    aggregate_type: str = "Memory"


# Vector Context Events
@dataclass(frozen=True)
class VectorIndexed(DomainEvent):
    """ベクトルインデックス作成イベント"""
    document_id: str = ""
    content_length: int = 0
    aggregate_type: str = "VectorStore"


@dataclass(frozen=True)
class VectorSearched(DomainEvent):
    """ベクトル検索実行イベント"""
    query: str = ""
    top_k: int = 0
    result_count: int = 0
    aggregate_type: str = "VectorStore"


# Graph Context Events
@dataclass(frozen=True)
class GraphNodeCreated(DomainEvent):
    """グラフノード作成イベント"""
    node_id: str = ""
    labels: tuple[str, ...] = ()
    aggregate_type: str = "GraphStore"


@dataclass(frozen=True)
class GraphEdgeCreated(DomainEvent):
    """グラフエッジ作成イベント"""
    edge_id: str = ""
    edge_type: str = ""
    source_id: str = ""
    target_id: str = ""
    aggregate_type: str = "GraphStore"


@dataclass(frozen=True)
class GraphQueried(DomainEvent):
    """グラフクエリ実行イベント"""
    query: str = ""
    node_count: int = 0
    edge_count: int = 0
    aggregate_type: str = "GraphStore"


# Agent Context Events
@dataclass(frozen=True)
class AgentInvoked(DomainEvent):
    """エージェント呼び出しイベント"""
    agent_type: str = ""  # multimodal, voice
    session_id: str = ""
    input_type: str = ""  # text, image, video, audio
    aggregate_type: str = "Agent"


@dataclass(frozen=True)
class ImageGenerated(DomainEvent):
    """画像生成イベント"""
    session_id: str = ""
    prompt: str = ""
    seed: int = 0
    aggregate_type: str = "Agent"


@dataclass(frozen=True)
class VideoGenerated(DomainEvent):
    """動画生成イベント"""
    session_id: str = ""
    job_id: str = ""
    aggregate_type: str = "Agent"


@dataclass(frozen=True)
class VoiceProcessed(DomainEvent):
    """音声処理イベント"""
    session_id: str = ""
    input_duration_ms: int = 0
    output_duration_ms: int = 0
    aggregate_type: str = "Agent"
