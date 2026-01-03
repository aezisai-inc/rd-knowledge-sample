"""
Session Entity Unit Tests

TDD Red-Green-Refactor サイクルで実装。
"""

import pytest
from datetime import datetime
from uuid import UUID

# テスト対象のインポート
import sys
sys.path.insert(0, str(__file__).replace('/tests/unit/domain/test_session.py', ''))

from shared.domain.value_objects.entity_id import (
    SessionId,
    ActorId,
    SessionType,
    Role,
    Content,
)
from services.memory.domain.entities.session import Session, MemoryEvent


class TestSession:
    """Session 集約のテスト"""
    
    # =========================================================================
    # Creation Tests
    # =========================================================================
    
    def test_create_session_should_generate_id(self):
        """セッション作成時にIDが生成される"""
        # Arrange
        actor_id = ActorId.generate()
        session_type = SessionType.memory()
        
        # Act
        session = Session.create(actor_id, session_type)
        
        # Assert
        assert session.id is not None
        assert isinstance(session.id, SessionId)
    
    def test_create_session_should_set_actor_id(self):
        """セッション作成時にアクターIDが設定される"""
        # Arrange
        actor_id = ActorId.generate()
        session_type = SessionType.memory()
        
        # Act
        session = Session.create(actor_id, session_type)
        
        # Assert
        assert session.actor_id == actor_id
    
    def test_create_session_should_set_session_type(self):
        """セッション作成時にセッションタイプが設定される"""
        # Arrange
        actor_id = ActorId.generate()
        session_type = SessionType.multimodal()
        
        # Act
        session = Session.create(actor_id, session_type)
        
        # Assert
        assert session.session_type == session_type
    
    def test_create_session_should_raise_session_started_event(self):
        """セッション作成時に SessionStarted イベントが発行される"""
        # Arrange
        actor_id = ActorId.generate()
        session_type = SessionType.voice()
        
        # Act
        session = Session.create(actor_id, session_type)
        events = session.collect_domain_events()
        
        # Assert
        assert len(events) == 1
        assert events[0].event_type == "SessionStarted"
        assert events[0].actor_id == str(actor_id)
        assert events[0].session_type == "voice"
    
    def test_create_session_should_have_zero_events(self):
        """作成直後のセッションはイベントが0件"""
        # Arrange
        actor_id = ActorId.generate()
        session_type = SessionType.memory()
        
        # Act
        session = Session.create(actor_id, session_type)
        
        # Assert
        assert session.event_count == 0
        assert len(session.events) == 0
    
    # =========================================================================
    # Add Event Tests
    # =========================================================================
    
    def test_add_event_should_increase_event_count(self):
        """イベント追加時にカウントが増加する"""
        # Arrange
        session = Session.create(ActorId.generate(), SessionType.memory())
        session.collect_domain_events()  # 作成イベントをクリア
        
        # Act
        session.add_event(Role.user(), Content("Hello"))
        
        # Assert
        assert session.event_count == 1
    
    def test_add_event_should_return_memory_event(self):
        """イベント追加時に MemoryEvent が返される"""
        # Arrange
        session = Session.create(ActorId.generate(), SessionType.memory())
        
        # Act
        event = session.add_event(Role.user(), Content("Hello"))
        
        # Assert
        assert isinstance(event, MemoryEvent)
        assert str(event.content) == "Hello"
        assert event.role.is_user()
    
    def test_add_event_should_raise_memory_event_created(self):
        """イベント追加時に MemoryEventCreated イベントが発行される"""
        # Arrange
        session = Session.create(ActorId.generate(), SessionType.memory())
        session.collect_domain_events()  # 作成イベントをクリア
        
        # Act
        session.add_event(Role.assistant(), Content("Hi there!"))
        events = session.collect_domain_events()
        
        # Assert
        assert len(events) == 1
        assert events[0].event_type == "MemoryEventCreated"
        assert events[0].role == "ASSISTANT"
        assert events[0].content == "Hi there!"
    
    def test_add_event_to_ended_session_should_raise_error(self):
        """終了済みセッションへのイベント追加はエラー"""
        # Arrange
        session = Session.create(ActorId.generate(), SessionType.memory())
        session.end()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot add events to an ended session"):
            session.add_event(Role.user(), Content("Hello"))
    
    # =========================================================================
    # End Session Tests
    # =========================================================================
    
    def test_end_session_should_set_ended_at(self):
        """セッション終了時に ended_at が設定される"""
        # Arrange
        session = Session.create(ActorId.generate(), SessionType.memory())
        
        # Act
        session.end()
        
        # Assert
        assert session.ended_at is not None
        assert isinstance(session.ended_at, datetime)
    
    def test_end_session_should_set_is_ended_to_true(self):
        """セッション終了時に is_ended が True になる"""
        # Arrange
        session = Session.create(ActorId.generate(), SessionType.memory())
        
        # Act
        session.end()
        
        # Assert
        assert session.is_ended is True
    
    def test_end_already_ended_session_should_raise_error(self):
        """既に終了済みのセッションを終了するとエラー"""
        # Arrange
        session = Session.create(ActorId.generate(), SessionType.memory())
        session.end()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Session is already ended"):
            session.end()
    
    def test_end_session_should_raise_session_ended_event(self):
        """セッション終了時に SessionEnded イベントが発行される"""
        # Arrange
        session = Session.create(ActorId.generate(), SessionType.memory())
        session.add_event(Role.user(), Content("Hello"))
        session.add_event(Role.assistant(), Content("Hi"))
        session.collect_domain_events()  # 既存イベントをクリア
        
        # Act
        session.end()
        events = session.collect_domain_events()
        
        # Assert
        assert len(events) == 1
        assert events[0].event_type == "SessionEnded"
        assert events[0].event_count == 2
    
    # =========================================================================
    # Query Tests
    # =========================================================================
    
    def test_get_events_by_role_should_filter_correctly(self):
        """ロールでフィルタしたイベントが取得できる"""
        # Arrange
        session = Session.create(ActorId.generate(), SessionType.memory())
        session.add_event(Role.user(), Content("Q1"))
        session.add_event(Role.assistant(), Content("A1"))
        session.add_event(Role.user(), Content("Q2"))
        
        # Act
        user_events = session.get_events_by_role(Role.user())
        assistant_events = session.get_events_by_role(Role.assistant())
        
        # Assert
        assert len(user_events) == 2
        assert len(assistant_events) == 1
        assert all(e.role.is_user() for e in user_events)
    
    def test_get_recent_events_should_return_last_n(self):
        """最新N件のイベントが取得できる"""
        # Arrange
        session = Session.create(ActorId.generate(), SessionType.memory())
        for i in range(5):
            session.add_event(Role.user(), Content(f"Message {i}"))
        
        # Act
        recent = session.get_recent_events(limit=3)
        
        # Assert
        assert len(recent) == 3
        assert str(recent[0].content) == "Message 2"
        assert str(recent[2].content) == "Message 4"
    
    # =========================================================================
    # Version Tests
    # =========================================================================
    
    def test_version_should_increment_on_each_event(self):
        """イベント発行ごとにバージョンが増加する"""
        # Arrange
        session = Session.create(ActorId.generate(), SessionType.memory())
        initial_version = session.version
        
        # Act
        session.add_event(Role.user(), Content("Hello"))
        
        # Assert
        assert session.version == initial_version + 1
    
    def test_collect_domain_events_should_clear_events(self):
        """collect_domain_events 後はイベントがクリアされる"""
        # Arrange
        session = Session.create(ActorId.generate(), SessionType.memory())
        
        # Act
        events1 = session.collect_domain_events()
        events2 = session.collect_domain_events()
        
        # Assert
        assert len(events1) == 1
        assert len(events2) == 0


class TestMemoryEvent:
    """MemoryEvent エンティティのテスト"""
    
    def test_create_should_generate_id(self):
        """作成時にIDが生成される"""
        # Arrange
        session_id = SessionId.generate()
        actor_id = ActorId.generate()
        
        # Act
        event = MemoryEvent.create(
            session_id=session_id,
            actor_id=actor_id,
            role=Role.user(),
            content=Content("Test"),
        )
        
        # Assert
        assert event.id is not None
    
    def test_create_should_set_timestamp(self):
        """作成時にタイムスタンプが設定される"""
        # Arrange
        session_id = SessionId.generate()
        actor_id = ActorId.generate()
        
        # Act
        event = MemoryEvent.create(
            session_id=session_id,
            actor_id=actor_id,
            role=Role.user(),
            content=Content("Test"),
        )
        
        # Assert
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)
    
    def test_to_dict_should_return_serializable_dict(self):
        """to_dict はシリアライズ可能な辞書を返す"""
        # Arrange
        session_id = SessionId.generate()
        actor_id = ActorId.generate()
        event = MemoryEvent.create(
            session_id=session_id,
            actor_id=actor_id,
            role=Role.assistant(),
            content=Content("Response"),
            metadata={"key": "value"},
        )
        
        # Act
        result = event.to_dict()
        
        # Assert
        assert "id" in result
        assert "session_id" in result
        assert "actor_id" in result
        assert "role" in result
        assert result["role"] == "ASSISTANT"
        assert result["content"] == "Response"
        assert result["metadata"] == {"key": "value"}


class TestValueObjects:
    """値オブジェクトのテスト"""
    
    def test_role_user_should_be_valid(self):
        """USER ロールは有効"""
        role = Role.user()
        assert role.is_user()
        assert role.value == "USER"
    
    def test_role_invalid_should_raise_error(self):
        """無効なロールはエラー"""
        with pytest.raises(ValueError, match="Invalid role"):
            Role("INVALID")
    
    def test_session_type_memory_should_be_valid(self):
        """memory セッションタイプは有効"""
        st = SessionType.memory()
        assert st.value == "memory"
    
    def test_session_type_invalid_should_raise_error(self):
        """無効なセッションタイプはエラー"""
        with pytest.raises(ValueError, match="Invalid session type"):
            SessionType("invalid")
    
    def test_content_empty_should_raise_error(self):
        """空のコンテンツはエラー"""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            Content("")
    
    def test_content_whitespace_only_should_raise_error(self):
        """空白のみのコンテンツはエラー"""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            Content("   ")
    
    def test_content_truncate_should_work(self):
        """コンテンツの切り詰めが動作する"""
        content = Content("Hello, World!")
        assert content.truncate(5) == "He..."
        assert content.truncate(100) == "Hello, World!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
