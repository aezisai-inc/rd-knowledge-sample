"""
Agent Session Entity - Agent Bounded Context

AI エージェント対話セッション。
StrandsAgents + Bedrock Nova API を使用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class AgentType(Enum):
    """エージェントタイプ"""
    MULTIMODAL = "multimodal"  # Nova Vision + Canvas + Reel
    VOICE = "voice"            # Nova Sonic


@dataclass(frozen=True)
class AgentSessionId:
    """エージェントセッション識別子"""
    
    value: str
    
    @classmethod
    def generate(cls) -> AgentSessionId:
        return cls(str(uuid4()))
    
    @classmethod
    def from_string(cls, value: str) -> AgentSessionId:
        return cls(value)
    
    def __str__(self) -> str:
        return self.value


@dataclass
class AgentResponse:
    """エージェントレスポンス"""
    
    message: Optional[str] = None
    images: list[dict[str, Any]] = field(default_factory=list)
    videos: list[dict[str, Any]] = field(default_factory=list)
    audio: Optional[str] = None  # Base64
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "images": self.images,
            "videos": self.videos,
            "audio": self.audio,
            "metadata": self.metadata,
        }


@dataclass
class ToolCall:
    """ツール呼び出し記録"""
    
    tool_name: str
    input_data: dict[str, Any]
    output_data: Optional[dict[str, Any]] = None
    called_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: Optional[int] = None


@dataclass
class AgentSession:
    """
    エージェント対話セッション
    
    StrandsAgents ベースのエージェントセッション。
    Memory Context の Session と連携。
    """
    
    id: AgentSessionId
    agent_type: AgentType
    memory_session_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    model_id: str = "amazon.nova-pro-v1:0"
    _domain_events: list[Any] = field(default_factory=list)
    
    @classmethod
    def create(
        cls,
        agent_type: AgentType,
        memory_session_id: str,
        model_id: Optional[str] = None,
    ) -> AgentSession:
        """ファクトリメソッド: 新しいエージェントセッションを作成"""
        session = cls(
            id=AgentSessionId.generate(),
            agent_type=agent_type,
            memory_session_id=memory_session_id,
            started_at=datetime.now(timezone.utc),
            model_id=model_id or cls._default_model(agent_type),
        )
        return session
    
    @staticmethod
    def _default_model(agent_type: AgentType) -> str:
        """デフォルトモデルを取得"""
        return {
            AgentType.MULTIMODAL: "amazon.nova-pro-v1:0",
            AgentType.VOICE: "amazon.nova-sonic-v1:0",
        }.get(agent_type, "amazon.nova-pro-v1:0")
    
    @property
    def is_active(self) -> bool:
        """セッションがアクティブか"""
        return self.ended_at is None
    
    @property
    def tool_call_count(self) -> int:
        """ツール呼び出し回数"""
        return len(self.tool_calls)
    
    @property
    def duration_seconds(self) -> float:
        """セッション継続時間（秒）"""
        end = self.ended_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()
    
    def record_tool_call(
        self,
        tool_name: str,
        input_data: dict[str, Any],
        output_data: Optional[dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ) -> ToolCall:
        """ツール呼び出しを記録"""
        if not self.is_active:
            raise ValueError("Cannot record tool calls on inactive session")
        
        tool_call = ToolCall(
            tool_name=tool_name,
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms,
        )
        self.tool_calls.append(tool_call)
        return tool_call
    
    def end(self) -> None:
        """セッションを終了"""
        if not self.is_active:
            raise ValueError("Session is already ended")
        
        self.ended_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict[str, Any]:
        """シリアライズ可能な辞書に変換"""
        return {
            "id": str(self.id),
            "agent_type": self.agent_type.value,
            "memory_session_id": self.memory_session_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "model_id": self.model_id,
            "tool_call_count": self.tool_call_count,
            "duration_seconds": self.duration_seconds,
        }


# ============================================================================
# Domain Events
# ============================================================================

@dataclass(frozen=True)
class AgentInvoked:
    """エージェント呼び出しイベント"""
    session_id: str
    agent_type: str
    prompt: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AgentCompleted:
    """エージェント完了イベント"""
    session_id: str
    response_type: str  # "text", "image", "video", "audio"
    latency_ms: int
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ToolExecuted:
    """ツール実行イベント"""
    session_id: str
    tool_name: str
    success: bool
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Export
__all__ = [
    "AgentSession",
    "AgentSessionId",
    "AgentType",
    "AgentResponse",
    "ToolCall",
    "AgentInvoked",
    "AgentCompleted",
    "ToolExecuted",
]
