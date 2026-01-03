"""
Memory Repository Interface

依存性逆転の原則 (DIP) に従い、ドメイン層でインターフェースを定義。
具体的な実装はインフラ層で提供する。
"""

from abc import ABC, abstractmethod
from typing import Protocol

from shared.domain.events.domain_event import DomainEvent
from shared.domain.value_objects.entity_id import SessionId, ActorId, MemoryEventId
from services.memory.domain.entities.session import Session, MemoryEvent


class SessionRepository(ABC):
    """
    セッションリポジトリ インターフェース
    
    集約ルートの永続化を担当。
    Event Sourcing パターンでは、イベントストリームとして保存。
    """
    
    @abstractmethod
    async def save(self, session: Session) -> None:
        """
        セッションを保存
        
        Event Sourcing: 発行されたドメインイベントをイベントストアに追記
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, session_id: SessionId) -> Session | None:
        """
        IDでセッションを取得
        
        Event Sourcing: イベントストリームから集約を再構築
        """
        pass
    
    @abstractmethod
    async def get_by_actor(
        self,
        actor_id: ActorId,
        limit: int = 10,
    ) -> list[Session]:
        """アクターIDでセッション一覧を取得"""
        pass
    
    @abstractmethod
    async def delete(self, session_id: SessionId) -> bool:
        """
        セッションを削除
        
        Event Sourcing: 削除イベントを追記（論理削除）
        """
        pass


class MemoryEventRepository(ABC):
    """
    メモリイベントリポジトリ インターフェース
    
    CQRS の Read Model 用。
    クエリ最適化のため、イベントを非正規化して保存。
    """
    
    @abstractmethod
    async def get_by_session(
        self,
        session_id: SessionId,
        limit: int | None = None,
    ) -> list[MemoryEvent]:
        """セッションIDでイベント一覧を取得"""
        pass
    
    @abstractmethod
    async def get_by_id(self, event_id: MemoryEventId) -> MemoryEvent | None:
        """IDでイベントを取得"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        session_id: SessionId | None = None,
        limit: int = 10,
    ) -> list[MemoryEvent]:
        """コンテンツで検索"""
        pass


class EventStore(ABC):
    """
    イベントストア インターフェース
    
    Event Sourcing パターンの永続化層。
    すべてのドメインイベントを追記のみで保存。
    """
    
    @abstractmethod
    async def append(
        self,
        stream_id: str,
        events: list[DomainEvent],
        expected_version: int | None = None,
    ) -> None:
        """
        イベントをストリームに追記
        
        expected_version: 楽観的ロック用のバージョン（オプショナル）
        """
        pass
    
    @abstractmethod
    async def get_stream(
        self,
        stream_id: str,
        from_version: int = 0,
    ) -> list[DomainEvent]:
        """
        イベントストリームを取得
        
        from_version: 指定バージョン以降のイベントのみ取得
        """
        pass
    
    @abstractmethod
    async def get_all_events(
        self,
        event_types: list[str] | None = None,
        limit: int = 100,
    ) -> list[DomainEvent]:
        """
        全イベントを取得（プロジェクション用）
        
        event_types: フィルタするイベントタイプ
        """
        pass


class EventPublisher(Protocol):
    """
    イベントパブリッシャー プロトコル
    
    ドメインイベントを外部に配信するためのインターフェース。
    EventBridge、SNS、AppSync Subscriptions など。
    """
    
    async def publish(self, event: DomainEvent) -> None:
        """イベントを配信"""
        ...
    
    async def publish_batch(self, events: list[DomainEvent]) -> None:
        """複数イベントを配信"""
        ...
