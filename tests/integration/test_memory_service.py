"""
Memory Service Integration Tests

CQRS パターンの Command/Query ハンドラの統合テスト。
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

import sys
sys.path.insert(0, str(__file__).replace('/tests/integration/test_memory_service.py', ''))

from shared.domain.value_objects.entity_id import (
    SessionId,
    ActorId,
    SessionType,
    Role,
    Content,
)
from services.memory.domain.entities.session import Session, MemoryEvent
from services.memory.application.commands.session_commands import (
    CreateSessionCommand,
    AddEventCommand,
    EndSessionCommand,
)
from services.memory.application.queries.session_queries import (
    GetSessionQuery,
    GetSessionEventsQuery,
    SearchSessionsQuery,
)
from services.memory.application.handlers.command_handlers import (
    CreateSessionHandler,
    AddEventHandler,
    EndSessionHandler,
)
from services.memory.application.handlers.query_handlers import (
    GetSessionHandler,
    GetSessionEventsHandler,
)
from services.memory.infrastructure.repositories.in_memory_session_repository import (
    InMemorySessionRepository,
)


class TestMemoryServiceIntegration:
    """Memory サービス統合テスト"""
    
    @pytest.fixture
    def repository(self):
        """インメモリリポジトリ"""
        return InMemorySessionRepository()
    
    @pytest.fixture
    def create_handler(self, repository):
        return CreateSessionHandler(repository)
    
    @pytest.fixture
    def add_event_handler(self, repository):
        return AddEventHandler(repository)
    
    @pytest.fixture
    def end_handler(self, repository):
        return EndSessionHandler(repository)
    
    @pytest.fixture
    def get_session_handler(self, repository):
        return GetSessionHandler(repository)
    
    @pytest.fixture
    def get_events_handler(self, repository):
        return GetSessionEventsHandler(repository)
    
    # =========================================================================
    # Command Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_create_session_command_should_persist_session(
        self, create_handler, repository
    ):
        """CreateSessionCommand がセッションを永続化する"""
        # Arrange
        command = CreateSessionCommand(
            actor_id=str(ActorId.generate()),
            session_type="memory",
            title="Test Session",
            tags=["test", "integration"],
        )
        
        # Act
        result = await create_handler.handle(command)
        
        # Assert
        assert result.session_id is not None
        saved = await repository.find_by_id(SessionId.from_string(result.session_id))
        assert saved is not None
        assert saved.title == "Test Session"
    
    @pytest.mark.asyncio
    async def test_add_event_command_should_add_event_to_session(
        self, create_handler, add_event_handler, repository
    ):
        """AddEventCommand がイベントを追加する"""
        # Arrange: セッション作成
        create_cmd = CreateSessionCommand(
            actor_id=str(ActorId.generate()),
            session_type="memory",
        )
        create_result = await create_handler.handle(create_cmd)
        
        # Act: イベント追加
        add_cmd = AddEventCommand(
            session_id=create_result.session_id,
            role="USER",
            content="Hello, AI!",
        )
        event_result = await add_event_handler.handle(add_cmd)
        
        # Assert
        assert event_result.event_id is not None
        session = await repository.find_by_id(
            SessionId.from_string(create_result.session_id)
        )
        assert session.event_count == 1
    
    @pytest.mark.asyncio
    async def test_end_session_command_should_end_session(
        self, create_handler, end_handler, repository
    ):
        """EndSessionCommand がセッションを終了する"""
        # Arrange
        create_cmd = CreateSessionCommand(
            actor_id=str(ActorId.generate()),
            session_type="memory",
        )
        create_result = await create_handler.handle(create_cmd)
        
        # Act
        end_cmd = EndSessionCommand(session_id=create_result.session_id)
        end_result = await end_handler.handle(end_cmd)
        
        # Assert
        assert end_result.ended_at is not None
        session = await repository.find_by_id(
            SessionId.from_string(create_result.session_id)
        )
        assert session.is_ended is True
    
    # =========================================================================
    # Query Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_get_session_query_should_return_session(
        self, create_handler, get_session_handler
    ):
        """GetSessionQuery がセッションを取得する"""
        # Arrange
        create_cmd = CreateSessionCommand(
            actor_id=str(ActorId.generate()),
            session_type="multimodal",
            title="Test Query",
        )
        create_result = await create_handler.handle(create_cmd)
        
        # Act
        query = GetSessionQuery(session_id=create_result.session_id)
        result = await get_session_handler.handle(query)
        
        # Assert
        assert result.session_id == create_result.session_id
        assert result.title == "Test Query"
        assert result.session_type == "multimodal"
    
    @pytest.mark.asyncio
    async def test_get_session_events_query_should_return_events(
        self, create_handler, add_event_handler, get_events_handler
    ):
        """GetSessionEventsQuery がイベントリストを取得する"""
        # Arrange
        create_cmd = CreateSessionCommand(
            actor_id=str(ActorId.generate()),
            session_type="memory",
        )
        create_result = await create_handler.handle(create_cmd)
        
        # イベント追加
        for i in range(3):
            await add_event_handler.handle(
                AddEventCommand(
                    session_id=create_result.session_id,
                    role="USER" if i % 2 == 0 else "ASSISTANT",
                    content=f"Message {i}",
                )
            )
        
        # Act
        query = GetSessionEventsQuery(session_id=create_result.session_id)
        result = await get_events_handler.handle(query)
        
        # Assert
        assert len(result.events) == 3
        assert result.events[0]["content"] == "Message 0"
    
    # =========================================================================
    # Workflow Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_complete_session_workflow(
        self, create_handler, add_event_handler, end_handler, get_session_handler
    ):
        """完全なセッションワークフロー"""
        # 1. セッション作成
        create_result = await create_handler.handle(
            CreateSessionCommand(
                actor_id=str(ActorId.generate()),
                session_type="voice",
                title="Voice Test",
            )
        )
        
        # 2. 会話イベント追加
        await add_event_handler.handle(
            AddEventCommand(
                session_id=create_result.session_id,
                role="USER",
                content="こんにちは",
            )
        )
        await add_event_handler.handle(
            AddEventCommand(
                session_id=create_result.session_id,
                role="ASSISTANT",
                content="こんにちは！何かお手伝いできますか？",
            )
        )
        
        # 3. セッション終了
        end_result = await end_handler.handle(
            EndSessionCommand(session_id=create_result.session_id)
        )
        
        # 4. 最終状態確認
        final_session = await get_session_handler.handle(
            GetSessionQuery(session_id=create_result.session_id)
        )
        
        # Assert
        assert final_session.is_ended is True
        assert final_session.event_count == 2
        assert final_session.duration_seconds > 0


class TestConcurrentAccess:
    """並行アクセステスト"""
    
    @pytest.fixture
    def repository(self):
        return InMemorySessionRepository()
    
    @pytest.mark.asyncio
    async def test_concurrent_event_addition(self, repository):
        """並行してイベントを追加しても整合性が保たれる"""
        import asyncio
        
        # Arrange
        handler = CreateSessionHandler(repository)
        add_handler = AddEventHandler(repository)
        
        result = await handler.handle(
            CreateSessionCommand(
                actor_id=str(ActorId.generate()),
                session_type="memory",
            )
        )
        
        # Act: 並行して10個のイベントを追加
        tasks = [
            add_handler.handle(
                AddEventCommand(
                    session_id=result.session_id,
                    role="USER",
                    content=f"Concurrent message {i}",
                )
            )
            for i in range(10)
        ]
        await asyncio.gather(*tasks)
        
        # Assert
        session = await repository.find_by_id(
            SessionId.from_string(result.session_id)
        )
        assert session.event_count == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
