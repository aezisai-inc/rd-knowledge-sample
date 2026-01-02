"""
AgentCore Configuration

StrandsAgents + AgentCore の設定とセッション管理。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bedrock_agentcore.memory.integrations.strands.session_manager import (
        AgentCoreMemorySessionManager,
    )

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Dataclasses
# =============================================================================

@dataclass
class AgentCoreConfig:
    """AgentCore 共通設定"""

    region: str = field(
        default_factory=lambda: os.environ.get("AWS_REGION", "ap-northeast-1")
    )
    memory_id: str = field(
        default_factory=lambda: os.environ.get("AGENTCORE_MEMORY_ID", "")
    )
    memory_name: str = field(
        default_factory=lambda: os.environ.get("AGENTCORE_MEMORY_NAME", "rd-knowledge-memory")
    )
    output_bucket: str = field(
        default_factory=lambda: os.environ.get("OUTPUT_BUCKET", "rd-knowledge-multimodal-output")
    )


@dataclass
class SessionConfig:
    """セッション設定"""

    actor_id: str = field(default="")
    session_id: str = field(default="")

    def __post_init__(self) -> None:
        """セッションID/アクターIDを自動生成"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        if not self.actor_id:
            self.actor_id = f"actor_{timestamp}"
        if not self.session_id:
            self.session_id = f"session_{timestamp}"


# =============================================================================
# Memory Strategies
# =============================================================================

DEFAULT_MEMORY_STRATEGIES = [
    # セッション要約: 会話を要約して保存
    {
        "summaryMemoryStrategy": {
            "name": "SessionSummarizer",
            "namespaces": ["/summaries/{actorId}/{sessionId}"],
        }
    },
    # ユーザー嗜好: 好みや設定を学習
    {
        "userPreferenceMemoryStrategy": {
            "name": "PreferenceLearner",
            "namespaces": ["/preferences/{actorId}"],
        }
    },
    # セマンティック記憶: 事実や知識を抽出
    {
        "semanticMemoryStrategy": {
            "name": "FactExtractor",
            "namespaces": ["/facts/{actorId}"],
        }
    },
]


# =============================================================================
# Memory Manager
# =============================================================================

class AgentCoreMemoryManager:
    """
    AgentCore Memory の管理クラス

    Memory の作成、取得、セッション管理を担当。
    """

    def __init__(self, config: AgentCoreConfig | None = None):
        """
        Args:
            config: AgentCore 設定（省略時はデフォルト）
        """
        self.config = config or AgentCoreConfig()
        self._client = None
        self._memory_id: str | None = None

    @property
    def client(self):
        """MemoryClient を取得（遅延初期化）"""
        if self._client is None:
            from bedrock_agentcore.memory import MemoryClient

            self._client = MemoryClient(region_name=self.config.region)
            logger.info(f"MemoryClient initialized: region={self.config.region}")
        return self._client

    def get_or_create_memory(
        self,
        name: str | None = None,
        description: str = "AI Agent Memory for rd-knowledge-sample",
        strategies: list | None = None,
    ) -> str:
        """
        Memory を取得または作成

        Args:
            name: Memory 名（省略時は config.memory_name）
            description: Memory 説明
            strategies: Memory 戦略（省略時はデフォルト）

        Returns:
            Memory ID
        """
        # 既存の memory_id が設定されている場合はそれを使用
        if self.config.memory_id:
            logger.info(f"Using existing memory: {self.config.memory_id}")
            return self.config.memory_id

        # 新規作成
        name = name or self.config.memory_name
        strategies = strategies or DEFAULT_MEMORY_STRATEGIES

        logger.info(f"Creating new memory: name={name}")

        try:
            memory = self.client.create_memory_and_wait(
                name=name,
                description=description,
                strategies=strategies,
            )
            self._memory_id = memory.get("id", "")
            logger.info(f"Memory created: id={self._memory_id}")
            return self._memory_id

        except Exception as e:
            # 既に存在する場合は取得を試みる
            logger.warning(f"Failed to create memory: {e}")
            return self._find_existing_memory(name)

    def _find_existing_memory(self, name: str) -> str:
        """既存の Memory を検索"""
        try:
            memories = self.client.list_memories()
            for memory in memories.get("memories", []):
                if memory.get("name") == name:
                    self._memory_id = memory.get("id", "")
                    logger.info(f"Found existing memory: id={self._memory_id}")
                    return self._memory_id

            raise ValueError(f"Memory not found: {name}")

        except Exception as e:
            logger.exception(f"Failed to find memory: {e}")
            raise

    def create_session_manager(
        self,
        session_config: SessionConfig | None = None,
    ) -> AgentCoreMemorySessionManager:
        """
        セッションマネージャを作成

        Args:
            session_config: セッション設定（省略時は自動生成）

        Returns:
            AgentCoreMemorySessionManager インスタンス
        """
        from bedrock_agentcore.memory.integrations.strands.config import (
            AgentCoreMemoryConfig,
        )
        from bedrock_agentcore.memory.integrations.strands.session_manager import (
            AgentCoreMemorySessionManager,
        )

        session = session_config or SessionConfig()
        memory_id = self.get_or_create_memory()

        agentcore_memory_config = AgentCoreMemoryConfig(
            memory_id=memory_id,
            session_id=session.session_id,
            actor_id=session.actor_id,
        )

        session_manager = AgentCoreMemorySessionManager(
            agentcore_memory_config=agentcore_memory_config,
            region_name=self.config.region,
        )

        logger.info(
            f"Session manager created: memory_id={memory_id}, "
            f"actor_id={session.actor_id}, session_id={session.session_id}"
        )

        return session_manager


# =============================================================================
# Global Instance
# =============================================================================

_memory_manager: AgentCoreMemoryManager | None = None


def get_memory_manager() -> AgentCoreMemoryManager:
    """グローバルな MemoryManager を取得"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = AgentCoreMemoryManager()
    return _memory_manager


def create_session_manager(
    actor_id: str = "",
    session_id: str = "",
) -> AgentCoreMemorySessionManager:
    """
    便利関数: セッションマネージャを作成

    Args:
        actor_id: アクターID（省略時は自動生成）
        session_id: セッションID（省略時は自動生成）

    Returns:
        AgentCoreMemorySessionManager インスタンス

    Example:
        >>> session_manager = create_session_manager(actor_id="user-123")
        >>> agent = Agent(session_manager=session_manager, ...)
    """
    manager = get_memory_manager()
    session_config = SessionConfig(actor_id=actor_id, session_id=session_id)
    return manager.create_session_manager(session_config)

