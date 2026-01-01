"""
環境非依存の抽象化インターフェース

ローカル環境とAWS本番環境で同一インターフェースを使用し、
環境変数による切り替えを実現する。
"""

from .storage import (
    VectorStore,
    KnowledgeBase,
    MemoryStore,
    GraphStore,
    VectorRecord,
    SearchResult,
    MemoryEvent,
    MemoryRecord,
    GraphNode,
    GraphEdge,
)

__all__ = [
    # Protocols
    "VectorStore",
    "KnowledgeBase",
    "MemoryStore",
    "GraphStore",
    # Data Classes
    "VectorRecord",
    "SearchResult",
    "MemoryEvent",
    "MemoryRecord",
    "GraphNode",
    "GraphEdge",
]

