"""
Query Handlers - CQRS Read Side

クエリを受け取り、リポジトリからデータを取得して
読み取り最適化されたレスポンスを返す。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Protocol

from shared.domain.value_objects.entity_id import SessionId, Role
from services.memory.domain.entities.session import Session
from services.memory.application.queries.session_queries import (
    GetSessionQuery,
    GetSessionEventsQuery,
    SearchSessionsQuery,
)


# ============================================================================
# Repository Protocol
# ============================================================================

class SessionReadRepository(Protocol):
    """Session 読み取り用リポジトリインターフェース"""
    
    async def find_by_id(self, session_id: SessionId) -> Session | None:
        ...
    
    async def find_by_actor_id(self, actor_id: str) -> list[Session]:
        ...


# ============================================================================
# Query Results (Read Models)
# ============================================================================

@dataclass
class SessionDto:
    """セッション DTO"""
    session_id: str
    actor_id: str
    session_type: str
    started_at: datetime
    ended_at: Optional[datetime]
    title: Optional[str]
    tags: list[str]
    event_count: int
    is_ended: bool
    duration_seconds: float


@dataclass
class SessionEventsDto:
    """セッションイベント DTO"""
    session_id: str
    events: list[dict[str, Any]]
    total_count: int


# ============================================================================
# Query Handlers
# ============================================================================

class GetSessionHandler:
    """GetSessionQuery ハンドラ"""
    
    def __init__(self, repository: SessionReadRepository):
        self._repository = repository
    
    async def handle(self, query: GetSessionQuery) -> SessionDto:
        """セッションを取得"""
        session_id = SessionId.from_string(query.session_id)
        session = await self._repository.find_by_id(session_id)
        
        if session is None:
            raise ValueError(f"Session not found: {query.session_id}")
        
        return SessionDto(
            session_id=str(session.id),
            actor_id=str(session.actor_id),
            session_type=str(session.session_type),
            started_at=session.started_at,
            ended_at=session.ended_at,
            title=session.title,
            tags=session.tags,
            event_count=session.event_count,
            is_ended=session.is_ended,
            duration_seconds=session.duration_seconds,
        )


class GetSessionEventsHandler:
    """GetSessionEventsQuery ハンドラ"""
    
    def __init__(self, repository: SessionReadRepository):
        self._repository = repository
    
    async def handle(self, query: GetSessionEventsQuery) -> SessionEventsDto:
        """セッションのイベントを取得"""
        session_id = SessionId.from_string(query.session_id)
        session = await self._repository.find_by_id(session_id)
        
        if session is None:
            raise ValueError(f"Session not found: {query.session_id}")
        
        # イベント取得
        events = session.events
        
        # ロールフィルター
        if query.role_filter:
            role = Role(query.role_filter)
            events = [e for e in events if e.role == role]
        
        # 件数制限
        if query.limit:
            events = events[-query.limit:]
        
        return SessionEventsDto(
            session_id=str(session.id),
            events=[e.to_dict() for e in events],
            total_count=session.event_count,
        )
