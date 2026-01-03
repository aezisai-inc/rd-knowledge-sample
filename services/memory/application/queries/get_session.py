"""
GetSession Query

CQRS パターンの Query 側。
読み取り専用操作を定義。Command とは別のモデルを使用可能。
"""

from dataclasses import dataclass
from typing import Any

from shared.domain.value_objects.entity_id import SessionId, ActorId
from services.memory.domain.repositories.memory_repository import (
    SessionRepository,
    MemoryEventRepository,
)


# ============================================================================
# Query DTOs (Data Transfer Objects)
# ============================================================================

@dataclass(frozen=True)
class GetSessionQuery:
    """セッション取得クエリ"""
    session_id: str


@dataclass(frozen=True)
class GetSessionsByActorQuery:
    """アクター別セッション一覧取得クエリ"""
    actor_id: str
    limit: int = 10


@dataclass(frozen=True)
class GetMemoryEventsQuery:
    """メモリイベント一覧取得クエリ"""
    session_id: str
    limit: int | None = None


@dataclass(frozen=True)
class SearchMemoryQuery:
    """メモリ検索クエリ"""
    query: str
    session_id: str | None = None
    limit: int = 10


# ============================================================================
# Response DTOs
# ============================================================================

@dataclass
class MemoryEventDTO:
    """メモリイベント DTO"""
    id: str
    session_id: str
    actor_id: str
    role: str
    content: str
    timestamp: str
    metadata: dict[str, Any]


@dataclass
class SessionDTO:
    """セッション DTO"""
    id: str
    actor_id: str
    session_type: str
    created_at: str
    ended_at: str | None
    event_count: int
    events: list[MemoryEventDTO]


@dataclass
class SessionListDTO:
    """セッション一覧 DTO"""
    sessions: list[SessionDTO]
    total_count: int


@dataclass
class MemoryEventListDTO:
    """メモリイベント一覧 DTO"""
    events: list[MemoryEventDTO]
    total_count: int


# ============================================================================
# Query Handlers
# ============================================================================

class GetSessionHandler:
    """
    GetSession クエリハンドラー
    
    Read Model を使用して高速に読み取り。
    """
    
    def __init__(self, session_repository: SessionRepository):
        self._session_repository = session_repository
    
    async def handle(self, query: GetSessionQuery) -> SessionDTO | None:
        """クエリを実行"""
        session_id = SessionId.from_string(query.session_id)
        session = await self._session_repository.get_by_id(session_id)
        
        if session is None:
            return None
        
        return SessionDTO(
            id=str(session.id),
            actor_id=str(session.actor_id),
            session_type=session.session_type.value,
            created_at=session.created_at.isoformat(),
            ended_at=session.ended_at.isoformat() if session.ended_at else None,
            event_count=session.event_count,
            events=[
                MemoryEventDTO(
                    id=str(e.id),
                    session_id=str(e.session_id),
                    actor_id=str(e.actor_id),
                    role=e.role.value,
                    content=str(e.content),
                    timestamp=e.timestamp.isoformat(),
                    metadata=e.metadata,
                )
                for e in session.events
            ],
        )


class GetSessionsByActorHandler:
    """GetSessionsByActor クエリハンドラー"""
    
    def __init__(self, session_repository: SessionRepository):
        self._session_repository = session_repository
    
    async def handle(self, query: GetSessionsByActorQuery) -> SessionListDTO:
        """クエリを実行"""
        actor_id = ActorId.from_string(query.actor_id)
        sessions = await self._session_repository.get_by_actor(
            actor_id=actor_id,
            limit=query.limit,
        )
        
        return SessionListDTO(
            sessions=[
                SessionDTO(
                    id=str(s.id),
                    actor_id=str(s.actor_id),
                    session_type=s.session_type.value,
                    created_at=s.created_at.isoformat(),
                    ended_at=s.ended_at.isoformat() if s.ended_at else None,
                    event_count=s.event_count,
                    events=[],  # 一覧では events は含めない（N+1 対策）
                )
                for s in sessions
            ],
            total_count=len(sessions),
        )


class GetMemoryEventsHandler:
    """GetMemoryEvents クエリハンドラー"""
    
    def __init__(self, event_repository: MemoryEventRepository):
        self._event_repository = event_repository
    
    async def handle(self, query: GetMemoryEventsQuery) -> MemoryEventListDTO:
        """クエリを実行"""
        session_id = SessionId.from_string(query.session_id)
        events = await self._event_repository.get_by_session(
            session_id=session_id,
            limit=query.limit,
        )
        
        return MemoryEventListDTO(
            events=[
                MemoryEventDTO(
                    id=str(e.id),
                    session_id=str(e.session_id),
                    actor_id=str(e.actor_id),
                    role=e.role.value,
                    content=str(e.content),
                    timestamp=e.timestamp.isoformat(),
                    metadata=e.metadata,
                )
                for e in events
            ],
            total_count=len(events),
        )


class SearchMemoryHandler:
    """SearchMemory クエリハンドラー"""
    
    def __init__(self, event_repository: MemoryEventRepository):
        self._event_repository = event_repository
    
    async def handle(self, query: SearchMemoryQuery) -> MemoryEventListDTO:
        """クエリを実行"""
        session_id = None
        if query.session_id:
            session_id = SessionId.from_string(query.session_id)
        
        events = await self._event_repository.search(
            query=query.query,
            session_id=session_id,
            limit=query.limit,
        )
        
        return MemoryEventListDTO(
            events=[
                MemoryEventDTO(
                    id=str(e.id),
                    session_id=str(e.session_id),
                    actor_id=str(e.actor_id),
                    role=e.role.value,
                    content=str(e.content),
                    timestamp=e.timestamp.isoformat(),
                    metadata=e.metadata,
                )
                for e in events
            ],
            total_count=len(events),
        )
