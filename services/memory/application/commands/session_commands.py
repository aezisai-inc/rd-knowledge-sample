"""
Session Commands - CQRS Command Definitions

Write 操作のコマンドオブジェクト。
不変で自己文書化された意図を表現。
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CreateSessionCommand:
    """セッション作成コマンド"""
    
    actor_id: str
    session_type: str
    title: Optional[str] = None
    tags: Optional[list[str]] = None
    
    def __post_init__(self):
        if not self.actor_id:
            raise ValueError("actor_id is required")
        if not self.session_type:
            raise ValueError("session_type is required")


@dataclass(frozen=True)
class AddEventCommand:
    """イベント追加コマンド"""
    
    session_id: str
    role: str
    content: str
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.role:
            raise ValueError("role is required")
        if not self.content:
            raise ValueError("content is required")


@dataclass(frozen=True)
class EndSessionCommand:
    """セッション終了コマンド"""
    
    session_id: str
    
    def __post_init__(self):
        if not self.session_id:
            raise ValueError("session_id is required")


@dataclass(frozen=True)
class UpdateSessionTitleCommand:
    """セッションタイトル更新コマンド"""
    
    session_id: str
    title: str


@dataclass(frozen=True)
class AddSessionTagCommand:
    """セッションタグ追加コマンド"""
    
    session_id: str
    tag: str


@dataclass(frozen=True)
class RemoveSessionTagCommand:
    """セッションタグ削除コマンド"""
    
    session_id: str
    tag: str
