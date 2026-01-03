"""
CreateSession Command

CQRS パターンの Command 側。
状態変更を伴う操作を定義。
"""

from dataclasses import dataclass
from typing import Any

from shared.domain.value_objects.entity_id import ActorId, SessionType
from services.memory.domain.entities.session import Session
from services.memory.domain.repositories.memory_repository import (
    SessionRepository,
    EventStore,
    EventPublisher,
)


@dataclass(frozen=True)
class CreateSessionCommand:
    """セッション作成コマンド"""
    actor_id: str
    session_type: str  # memory, multimodal, voice
    metadata: dict[str, Any] | None = None


@dataclass
class CreateSessionResult:
    """セッション作成結果"""
    session_id: str
    actor_id: str
    session_type: str
    created_at: str


class CreateSessionHandler:
    """
    CreateSession コマンドハンドラー
    
    TDD: Red-Green-Refactor サイクルで実装
    1. テストを書く（Red）
    2. 最小限の実装（Green）
    3. リファクタリング（Refactor）
    """
    
    def __init__(
        self,
        session_repository: SessionRepository,
        event_store: EventStore,
        event_publisher: EventPublisher | None = None,
    ):
        self._session_repository = session_repository
        self._event_store = event_store
        self._event_publisher = event_publisher
    
    async def handle(self, command: CreateSessionCommand) -> CreateSessionResult:
        """
        コマンドを実行
        
        1. バリデーション
        2. ドメインロジック実行（Session.create）
        3. イベントストアに保存
        4. イベント配信（オプショナル）
        5. 結果を返却
        """
        # 1. バリデーション
        actor_id = ActorId.from_string(command.actor_id)
        session_type = SessionType(command.session_type)
        
        # 2. ドメインロジック実行
        session = Session.create(
            actor_id=actor_id,
            session_type=session_type,
        )
        
        # 3. ドメインイベントを収集
        domain_events = session.collect_domain_events()
        
        # 4. イベントストアに保存
        await self._event_store.append(
            stream_id=f"session-{session.id}",
            events=domain_events,
        )
        
        # 5. リポジトリに保存（Read Model 更新）
        await self._session_repository.save(session)
        
        # 6. イベント配信（オプショナル）
        if self._event_publisher:
            await self._event_publisher.publish_batch(domain_events)
        
        # 7. 結果を返却
        return CreateSessionResult(
            session_id=str(session.id),
            actor_id=str(session.actor_id),
            session_type=session.session_type.value,
            created_at=session.created_at.isoformat(),
        )


@dataclass(frozen=True)
class CreateMemoryEventCommand:
    """メモリイベント作成コマンド"""
    session_id: str
    role: str  # USER, ASSISTANT, SYSTEM
    content: str
    metadata: dict[str, Any] | None = None


@dataclass
class CreateMemoryEventResult:
    """メモリイベント作成結果"""
    event_id: str
    session_id: str
    role: str
    content: str
    timestamp: str


class CreateMemoryEventHandler:
    """CreateMemoryEvent コマンドハンドラー"""
    
    def __init__(
        self,
        session_repository: SessionRepository,
        event_store: EventStore,
        event_publisher: EventPublisher | None = None,
    ):
        self._session_repository = session_repository
        self._event_store = event_store
        self._event_publisher = event_publisher
    
    async def handle(self, command: CreateMemoryEventCommand) -> CreateMemoryEventResult:
        """コマンドを実行"""
        from shared.domain.value_objects.entity_id import SessionId, Role, Content
        
        # 1. セッションを取得
        session_id = SessionId.from_string(command.session_id)
        session = await self._session_repository.get_by_id(session_id)
        
        if session is None:
            raise ValueError(f"Session not found: {command.session_id}")
        
        # 2. バリデーション
        role = Role(command.role)
        content = Content(command.content)
        
        # 3. ドメインロジック実行
        memory_event = session.add_event(
            role=role,
            content=content,
            metadata=command.metadata,
        )
        
        # 4. ドメインイベントを収集
        domain_events = session.collect_domain_events()
        
        # 5. イベントストアに保存
        await self._event_store.append(
            stream_id=f"session-{session.id}",
            events=domain_events,
            expected_version=session.version - len(domain_events),
        )
        
        # 6. リポジトリに保存
        await self._session_repository.save(session)
        
        # 7. イベント配信
        if self._event_publisher:
            await self._event_publisher.publish_batch(domain_events)
        
        return CreateMemoryEventResult(
            event_id=str(memory_event.id),
            session_id=str(memory_event.session_id),
            role=memory_event.role.value,
            content=str(memory_event.content),
            timestamp=memory_event.timestamp.isoformat(),
        )


@dataclass(frozen=True)
class EndSessionCommand:
    """セッション終了コマンド"""
    session_id: str


@dataclass
class EndSessionResult:
    """セッション終了結果"""
    session_id: str
    ended_at: str
    event_count: int


class EndSessionHandler:
    """EndSession コマンドハンドラー"""
    
    def __init__(
        self,
        session_repository: SessionRepository,
        event_store: EventStore,
        event_publisher: EventPublisher | None = None,
    ):
        self._session_repository = session_repository
        self._event_store = event_store
        self._event_publisher = event_publisher
    
    async def handle(self, command: EndSessionCommand) -> EndSessionResult:
        """コマンドを実行"""
        from shared.domain.value_objects.entity_id import SessionId
        
        # 1. セッションを取得
        session_id = SessionId.from_string(command.session_id)
        session = await self._session_repository.get_by_id(session_id)
        
        if session is None:
            raise ValueError(f"Session not found: {command.session_id}")
        
        # 2. ドメインロジック実行
        session.end()
        
        # 3. ドメインイベントを収集
        domain_events = session.collect_domain_events()
        
        # 4. イベントストアに保存
        await self._event_store.append(
            stream_id=f"session-{session.id}",
            events=domain_events,
        )
        
        # 5. リポジトリに保存
        await self._session_repository.save(session)
        
        # 6. イベント配信
        if self._event_publisher:
            await self._event_publisher.publish_batch(domain_events)
        
        return EndSessionResult(
            session_id=str(session.id),
            ended_at=session.ended_at.isoformat() if session.ended_at else "",
            event_count=session.event_count,
        )
