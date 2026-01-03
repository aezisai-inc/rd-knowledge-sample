"""
In-Memory Session Repository

テスト・開発用のインメモリ実装。
本番では AgentCore Memory や S3Vector 実装に置き換え。
"""

import asyncio
from typing import Optional

from shared.domain.value_objects.entity_id import SessionId, ActorId
from services.memory.domain.entities.session import Session


class InMemorySessionRepository:
    """
    Session リポジトリのインメモリ実装
    
    テスト・開発用。スレッドセーフな実装。
    """
    
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()
    
    async def save(self, session: Session) -> None:
        """セッションを保存"""
        async with self._lock:
            self._sessions[str(session.id)] = session
    
    async def find_by_id(self, session_id: SessionId) -> Optional[Session]:
        """ID でセッションを取得"""
        return self._sessions.get(str(session_id))
    
    async def find_by_actor_id(self, actor_id: str) -> list[Session]:
        """アクター ID でセッションを検索"""
        return [
            s for s in self._sessions.values()
            if str(s.actor_id) == actor_id
        ]
    
    async def find_active_sessions(self, actor_id: Optional[str] = None) -> list[Session]:
        """アクティブなセッションを検索"""
        sessions = [s for s in self._sessions.values() if not s.is_ended]
        if actor_id:
            sessions = [s for s in sessions if str(s.actor_id) == actor_id]
        return sessions
    
    async def find_by_tags(self, tags: list[str]) -> list[Session]:
        """タグでセッションを検索"""
        return [
            s for s in self._sessions.values()
            if any(tag in s.tags for tag in tags)
        ]
    
    async def delete(self, session_id: SessionId) -> bool:
        """セッションを削除"""
        async with self._lock:
            key = str(session_id)
            if key in self._sessions:
                del self._sessions[key]
                return True
            return False
    
    async def count(self) -> int:
        """セッション数を取得"""
        return len(self._sessions)
    
    async def clear(self) -> None:
        """全セッションを削除（テスト用）"""
        async with self._lock:
            self._sessions.clear()
