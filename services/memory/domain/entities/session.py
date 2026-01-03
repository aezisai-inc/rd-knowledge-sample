"""
Session Aggregate Root - Memory Bounded Context

DDD 集約ルート。Session とその MemoryEvent を管理。
Event Sourcing パターンに対応したドメインイベント発行。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from shared.domain.value_objects.entity_id import (
    SessionId,
    ActorId,
    EventId,
    SessionType,
    Role,
    Content,
)


# ============================================================================
# Domain Events
# ============================================================================

@dataclass(frozen=True)
class DomainEvent:
    """ドメインイベント基底クラス"""
    
    event_id: str
    event_type: str
    occurred_at: datetime
    aggregate_id: str
    version: int
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": self.aggregate_id,
            "version": self.version,
        }


@dataclass(frozen=True)
class SessionStarted(DomainEvent):
    """セッション開始イベント"""
    
    actor_id: str
    session_type: str
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["actor_id"] = self.actor_id
        base["session_type"] = self.session_type
        return base


@dataclass(frozen=True)
class SessionEnded(DomainEvent):
    """セッション終了イベント"""
    
    event_count: int
    duration_seconds: float
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["event_count"] = self.event_count
        base["duration_seconds"] = self.duration_seconds
        return base


@dataclass(frozen=True)
class MemoryEventCreated(DomainEvent):
    """メモリイベント作成イベント"""
    
    event_id_created: str
    role: str
    content: str
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["event_id_created"] = self.event_id_created
        base["role"] = self.role
        base["content"] = self.content
        return base


# ============================================================================
# Entities
# ============================================================================

@dataclass
class MemoryEvent:
    """
    Memory Event Entity
    
    セッション内の個々のやり取り（発話、行動、思考）を表現。
    """
    
    id: EventId
    session_id: SessionId
    actor_id: ActorId
    role: Role
    content: Content
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        session_id: SessionId,
        actor_id: ActorId,
        role: Role,
        content: Content,
        metadata: Optional[dict[str, Any]] = None,
    ) -> MemoryEvent:
        """ファクトリメソッド: 新しい MemoryEvent を作成"""
        return cls(
            id=EventId.generate(),
            session_id=session_id,
            actor_id=actor_id,
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )
    
    def to_dict(self) -> dict[str, Any]:
        """シリアライズ可能な辞書に変換"""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "actor_id": str(self.actor_id),
            "role": str(self.role),
            "content": str(self.content),
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEvent:
        """辞書から MemoryEvent を復元"""
        return cls(
            id=EventId.from_string(data["id"]),
            session_id=SessionId.from_string(data["session_id"]),
            actor_id=ActorId.from_string(data["actor_id"]),
            role=Role(data["role"]),
            content=Content(data["content"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Session:
    """
    Session Aggregate Root
    
    会話セッションを管理する集約ルート。
    - セッションの開始/終了
    - MemoryEvent の追加
    - ドメインイベントの発行
    """
    
    id: SessionId
    actor_id: ActorId
    session_type: SessionType
    started_at: datetime
    ended_at: Optional[datetime] = None
    title: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    _events: list[MemoryEvent] = field(default_factory=list)
    _domain_events: list[DomainEvent] = field(default_factory=list)
    _version: int = 0
    
    @classmethod
    def create(
        cls,
        actor_id: ActorId,
        session_type: SessionType,
        title: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Session:
        """
        ファクトリメソッド: 新しい Session を作成
        
        SessionStarted ドメインイベントを発行。
        """
        session_id = SessionId.generate()
        session = cls(
            id=session_id,
            actor_id=actor_id,
            session_type=session_type,
            started_at=datetime.utcnow(),
            title=title,
            tags=tags or [],
        )
        
        # SessionStarted イベント発行
        session._raise_event(
            SessionStarted(
                event_id=str(EventId.generate()),
                event_type="SessionStarted",
                occurred_at=datetime.utcnow(),
                aggregate_id=str(session_id),
                version=session._version,
                actor_id=str(actor_id),
                session_type=str(session_type),
            )
        )
        
        return session
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def is_ended(self) -> bool:
        """セッションが終了しているか"""
        return self.ended_at is not None
    
    @property
    def event_count(self) -> int:
        """セッション内のイベント数"""
        return len(self._events)
    
    @property
    def events(self) -> list[MemoryEvent]:
        """セッション内のイベント（読み取り専用コピー）"""
        return list(self._events)
    
    @property
    def version(self) -> int:
        """集約のバージョン（楽観的ロック用）"""
        return self._version
    
    @property
    def duration_seconds(self) -> float:
        """セッションの継続時間（秒）"""
        end = self.ended_at or datetime.utcnow()
        return (end - self.started_at).total_seconds()
    
    # =========================================================================
    # Commands
    # =========================================================================
    
    def add_event(
        self,
        role: Role,
        content: Content,
        metadata: Optional[dict[str, Any]] = None,
    ) -> MemoryEvent:
        """
        新しい MemoryEvent を追加
        
        Args:
            role: メッセージの送信者ロール
            content: メッセージ内容
            metadata: 追加のメタデータ
        
        Returns:
            作成された MemoryEvent
        
        Raises:
            ValueError: セッションが終了している場合
        """
        if self.is_ended:
            raise ValueError("Cannot add events to an ended session")
        
        event = MemoryEvent.create(
            session_id=self.id,
            actor_id=self.actor_id,
            role=role,
            content=content,
            metadata=metadata,
        )
        self._events.append(event)
        
        # MemoryEventCreated イベント発行
        self._raise_event(
            MemoryEventCreated(
                event_id=str(EventId.generate()),
                event_type="MemoryEventCreated",
                occurred_at=datetime.utcnow(),
                aggregate_id=str(self.id),
                version=self._version,
                event_id_created=str(event.id),
                role=str(role),
                content=str(content),
            )
        )
        
        return event
    
    def end(self) -> None:
        """
        セッションを終了
        
        Raises:
            ValueError: 既に終了している場合
        """
        if self.is_ended:
            raise ValueError("Session is already ended")
        
        self.ended_at = datetime.utcnow()
        
        # SessionEnded イベント発行
        self._raise_event(
            SessionEnded(
                event_id=str(EventId.generate()),
                event_type="SessionEnded",
                occurred_at=datetime.utcnow(),
                aggregate_id=str(self.id),
                version=self._version,
                event_count=self.event_count,
                duration_seconds=self.duration_seconds,
            )
        )
    
    def add_tag(self, tag: str) -> None:
        """タグを追加"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """タグを削除"""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def set_title(self, title: str) -> None:
        """タイトルを設定"""
        self.title = title
    
    # =========================================================================
    # Queries
    # =========================================================================
    
    def get_events_by_role(self, role: Role) -> list[MemoryEvent]:
        """指定ロールのイベントを取得"""
        return [e for e in self._events if e.role == role]
    
    def get_recent_events(self, limit: int = 10) -> list[MemoryEvent]:
        """最新のイベントを取得"""
        return self._events[-limit:] if limit < len(self._events) else self._events
    
    def get_conversation_pairs(self) -> list[tuple[MemoryEvent, MemoryEvent]]:
        """ユーザー/アシスタントの会話ペアを取得"""
        pairs = []
        i = 0
        while i < len(self._events) - 1:
            if (
                self._events[i].role.is_user()
                and self._events[i + 1].role.is_assistant()
            ):
                pairs.append((self._events[i], self._events[i + 1]))
                i += 2
            else:
                i += 1
        return pairs
    
    # =========================================================================
    # Domain Events
    # =========================================================================
    
    def collect_domain_events(self) -> list[DomainEvent]:
        """
        未処理のドメインイベントを収集してクリア
        
        Event Sourcing / Event-driven architecture で使用。
        """
        events = list(self._domain_events)
        self._domain_events.clear()
        return events
    
    def _raise_event(self, event: DomainEvent) -> None:
        """ドメインイベントを発行（内部使用）"""
        self._domain_events.append(event)
        self._version += 1
    
    # =========================================================================
    # Serialization
    # =========================================================================
    
    def to_dict(self) -> dict[str, Any]:
        """シリアライズ可能な辞書に変換"""
        return {
            "id": str(self.id),
            "actor_id": str(self.actor_id),
            "session_type": str(self.session_type),
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "title": self.title,
            "tags": self.tags,
            "event_count": self.event_count,
            "version": self._version,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any], events: list[MemoryEvent] = None) -> Session:
        """辞書から Session を復元"""
        session = cls(
            id=SessionId.from_string(data["id"]),
            actor_id=ActorId.from_string(data["actor_id"]),
            session_type=SessionType(data["session_type"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            title=data.get("title"),
            tags=data.get("tags", []),
        )
        session._events = events or []
        session._version = data.get("version", 0)
        return session


# Export
__all__ = [
    "Session",
    "MemoryEvent",
    "DomainEvent",
    "SessionStarted",
    "SessionEnded",
    "MemoryEventCreated",
]
