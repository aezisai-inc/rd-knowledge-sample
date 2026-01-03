"""
In-Memory Agent Session Repository

テスト・開発用のインメモリ実装。
"""

import asyncio
from typing import Optional

from services.agent.domain.entities.agent_session import (
    AgentSession,
    AgentSessionId,
)


class InMemoryAgentSessionRepository:
    """
    Agent Session リポジトリのインメモリ実装
    """
    
    def __init__(self):
        self._sessions: dict[str, AgentSession] = {}
        self._lock = asyncio.Lock()
    
    async def save(self, session: AgentSession) -> None:
        """セッションを保存"""
        async with self._lock:
            self._sessions[str(session.id)] = session
    
    async def find_by_id(self, session_id: AgentSessionId) -> Optional[AgentSession]:
        """ID でセッションを取得"""
        return self._sessions.get(str(session_id))
    
    async def find_by_memory_session_id(self, memory_session_id: str) -> list[AgentSession]:
        """Memory セッション ID でセッションを検索"""
        return [
            s for s in self._sessions.values()
            if s.memory_session_id == memory_session_id
        ]
    
    async def count(self) -> int:
        """セッション数を取得"""
        return len(self._sessions)
    
    async def clear(self) -> None:
        """全セッションを削除（テスト用）"""
        async with self._lock:
            self._sessions.clear()
