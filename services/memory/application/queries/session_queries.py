"""
Session Queries - CQRS Query Definitions

Read 操作のクエリオブジェクト。
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GetSessionQuery:
    """セッション取得クエリ"""
    
    session_id: str


@dataclass(frozen=True)
class GetSessionEventsQuery:
    """セッションイベント取得クエリ"""
    
    session_id: str
    limit: Optional[int] = None
    role_filter: Optional[str] = None


@dataclass(frozen=True)
class SearchSessionsQuery:
    """セッション検索クエリ"""
    
    actor_id: Optional[str] = None
    session_type: Optional[str] = None
    tags: Optional[list[str]] = None
    include_ended: bool = True
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetRecentSessionsQuery:
    """最近のセッション取得クエリ"""
    
    actor_id: str
    limit: int = 10


@dataclass(frozen=True)
class GetSessionSummaryQuery:
    """セッションサマリー取得クエリ"""
    
    session_id: str
