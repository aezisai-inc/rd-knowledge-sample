"""
Value Objects for Entity IDs and Domain Primitives

Clean Architecture + DDD 値オブジェクト。
不変性、自己検証、等価性を保証。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class EntityId:
    """Entity ID の基底クラス"""
    
    value: str
    
    def __post_init__(self):
        if not self.value:
            raise ValueError("Entity ID cannot be empty")
        # UUID 形式の検証
        try:
            uuid.UUID(self.value)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {self.value}")
    
    @classmethod
    def generate(cls) -> EntityId:
        """新しい ID を生成"""
        return cls(str(uuid.uuid4()))
    
    @classmethod
    def from_string(cls, value: str) -> EntityId:
        """文字列から ID を生成"""
        return cls(value)
    
    def __str__(self) -> str:
        return self.value
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EntityId):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class SessionId(EntityId):
    """Session Entity の ID"""
    pass


@dataclass(frozen=True)
class ActorId(EntityId):
    """Actor (User/Agent) の ID"""
    pass


@dataclass(frozen=True)
class EventId(EntityId):
    """Memory Event の ID"""
    pass


@dataclass(frozen=True)
class GraphId(EntityId):
    """Graph Node/Edge の ID"""
    pass


# ============================================================================
# Domain Primitives (Value Objects)
# ============================================================================

@dataclass(frozen=True)
class SessionType:
    """Session の種類を表す値オブジェクト"""
    
    value: str
    
    VALID_TYPES = {"memory", "multimodal", "voice", "graph"}
    
    def __post_init__(self):
        if self.value not in self.VALID_TYPES:
            raise ValueError(
                f"Invalid session type: {self.value}. "
                f"Must be one of: {self.VALID_TYPES}"
            )
    
    @classmethod
    def memory(cls) -> SessionType:
        return cls("memory")
    
    @classmethod
    def multimodal(cls) -> SessionType:
        return cls("multimodal")
    
    @classmethod
    def voice(cls) -> SessionType:
        return cls("voice")
    
    @classmethod
    def graph(cls) -> SessionType:
        return cls("graph")
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Role:
    """メッセージの送信者ロール"""
    
    value: str
    
    VALID_ROLES = {"USER", "ASSISTANT", "SYSTEM", "TOOL"}
    
    def __post_init__(self):
        if self.value not in self.VALID_ROLES:
            raise ValueError(
                f"Invalid role: {self.value}. "
                f"Must be one of: {self.VALID_ROLES}"
            )
    
    @classmethod
    def user(cls) -> Role:
        return cls("USER")
    
    @classmethod
    def assistant(cls) -> Role:
        return cls("ASSISTANT")
    
    @classmethod
    def system(cls) -> Role:
        return cls("SYSTEM")
    
    @classmethod
    def tool(cls) -> Role:
        return cls("TOOL")
    
    def is_user(self) -> bool:
        return self.value == "USER"
    
    def is_assistant(self) -> bool:
        return self.value == "ASSISTANT"
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Content:
    """メッセージコンテンツ"""
    
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Content cannot be empty")
    
    def truncate(self, max_length: int = 100) -> str:
        """コンテンツを指定長に切り詰め"""
        if len(self.value) <= max_length:
            return self.value
        return self.value[:max_length - 3] + "..."
    
    def word_count(self) -> int:
        """単語数をカウント"""
        return len(self.value.split())
    
    def __str__(self) -> str:
        return self.value
    
    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class Timestamp:
    """タイムスタンプ値オブジェクト"""
    
    value: datetime
    
    @classmethod
    def now(cls) -> Timestamp:
        return cls(datetime.utcnow())
    
    @classmethod
    def from_iso(cls, iso_string: str) -> Timestamp:
        return cls(datetime.fromisoformat(iso_string))
    
    def to_iso(self) -> str:
        return self.value.isoformat()
    
    def __str__(self) -> str:
        return self.to_iso()


@dataclass(frozen=True)
class ModelId:
    """AI Model の識別子"""
    
    provider: str
    model_name: str
    
    VALID_PROVIDERS = {"bedrock", "openai", "anthropic"}
    
    def __post_init__(self):
        if self.provider not in self.VALID_PROVIDERS:
            raise ValueError(f"Invalid provider: {self.provider}")
        if not self.model_name:
            raise ValueError("Model name cannot be empty")
    
    @classmethod
    def bedrock_nova(cls, variant: str = "lite") -> ModelId:
        """Bedrock Nova モデル"""
        model_map = {
            "lite": "amazon.nova-lite-v1:0",
            "pro": "amazon.nova-pro-v1:0",
            "vision": "us.amazon.nova-canvas-v1:0",
            "sonic": "us.amazon.nova-sonic-v1:0",
            "reel": "us.amazon.nova-reel-v1:0",
        }
        return cls("bedrock", model_map.get(variant, model_map["lite"]))
    
    def __str__(self) -> str:
        return f"{self.provider}:{self.model_name}"


@dataclass(frozen=True)
class VectorEmbedding:
    """ベクトル埋め込み"""
    
    values: tuple[float, ...]
    dimensions: int
    
    def __post_init__(self):
        if len(self.values) != self.dimensions:
            raise ValueError(
                f"Vector dimension mismatch: expected {self.dimensions}, "
                f"got {len(self.values)}"
            )
    
    @classmethod
    def from_list(cls, values: list[float]) -> VectorEmbedding:
        return cls(tuple(values), len(values))
    
    def cosine_similarity(self, other: VectorEmbedding) -> float:
        """コサイン類似度を計算"""
        if self.dimensions != other.dimensions:
            raise ValueError("Dimension mismatch for cosine similarity")
        
        dot_product = sum(a * b for a, b in zip(self.values, other.values))
        norm_a = sum(a ** 2 for a in self.values) ** 0.5
        norm_b = sum(b ** 2 for b in other.values) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


# Export all
__all__ = [
    "EntityId",
    "SessionId",
    "ActorId", 
    "EventId",
    "GraphId",
    "SessionType",
    "Role",
    "Content",
    "Timestamp",
    "ModelId",
    "VectorEmbedding",
]
