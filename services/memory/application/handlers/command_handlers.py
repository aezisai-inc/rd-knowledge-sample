"""
Command Handlers - CQRS Write Side

コマンドを受け取り、ドメインロジックを実行し、
リポジトリに永続化する。
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from shared.domain.value_objects.entity_id import (
    SessionId,
    ActorId,
    SessionType,
    Role,
    Content,
)
from services.memory.domain.entities.session import Session
from services.memory.application.commands.session_commands import (
    CreateSessionCommand,
    AddEventCommand,
    EndSessionCommand,
)


# ============================================================================
# Repository Protocol (依存性逆転)
# ============================================================================

class SessionRepository(Protocol):
    """Session リポジトリインターフェース"""
    
    async def save(self, session: Session) -> None:
        """セッションを保存"""
        ...
    
    async def find_by_id(self, session_id: SessionId) -> Session | None:
        """ID でセッションを取得"""
        ...


# ============================================================================
# Command Results
# ============================================================================

@dataclass
class CreateSessionResult:
    """セッション作成結果"""
    session_id: str
    started_at: datetime


@dataclass
class AddEventResult:
    """イベント追加結果"""
    event_id: str
    timestamp: datetime


@dataclass
class EndSessionResult:
    """セッション終了結果"""
    session_id: str
    ended_at: datetime
    duration_seconds: float
    event_count: int


# ============================================================================
# Command Handlers
# ============================================================================

class CreateSessionHandler:
    """CreateSessionCommand ハンドラ"""
    
    def __init__(self, repository: SessionRepository):
        self._repository = repository
    
    async def handle(self, command: CreateSessionCommand) -> CreateSessionResult:
        """セッションを作成"""
        # ドメインオブジェクト作成
        session = Session.create(
            actor_id=ActorId.from_string(command.actor_id),
            session_type=SessionType(command.session_type),
            title=command.title,
            tags=command.tags,
        )
        
        # 永続化
        await self._repository.save(session)
        
        # ドメインイベント収集（Event Bus への発行用）
        domain_events = session.collect_domain_events()
        
        # 結果を返す
        return CreateSessionResult(
            session_id=str(session.id),
            started_at=session.started_at,
        )


class AddEventHandler:
    """AddEventCommand ハンドラ"""
    
    def __init__(self, repository: SessionRepository):
        self._repository = repository
    
    async def handle(self, command: AddEventCommand) -> AddEventResult:
        """セッションにイベントを追加"""
        # セッション取得
        session_id = SessionId.from_string(command.session_id)
        session = await self._repository.find_by_id(session_id)
        
        if session is None:
            raise ValueError(f"Session not found: {command.session_id}")
        
        # イベント追加
        event = session.add_event(
            role=Role(command.role),
            content=Content(command.content),
            metadata=command.metadata,
        )
        
        # 永続化
        await self._repository.save(session)
        
        # ドメインイベント収集
        domain_events = session.collect_domain_events()
        
        return AddEventResult(
            event_id=str(event.id),
            timestamp=event.timestamp,
        )


class EndSessionHandler:
    """EndSessionCommand ハンドラ"""
    
    def __init__(self, repository: SessionRepository):
        self._repository = repository
    
    async def handle(self, command: EndSessionCommand) -> EndSessionResult:
        """セッションを終了"""
        # セッション取得
        session_id = SessionId.from_string(command.session_id)
        session = await self._repository.find_by_id(session_id)
        
        if session is None:
            raise ValueError(f"Session not found: {command.session_id}")
        
        # セッション終了
        session.end()
        
        # 永続化
        await self._repository.save(session)
        
        # ドメインイベント収集
        domain_events = session.collect_domain_events()
        
        return EndSessionResult(
            session_id=str(session.id),
            ended_at=session.ended_at,
            duration_seconds=session.duration_seconds,
            event_count=session.event_count,
        )
