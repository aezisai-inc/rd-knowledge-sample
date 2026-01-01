"""
pytest 共通設定

フィクスチャと設定を定義。
環境変数 ENVIRONMENT で local/aws を切り替え。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Generator

import pytest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# 環境設定
# =============================================================================


def pytest_configure(config):
    """pytest 設定"""
    # デフォルトはローカル環境
    if "ENVIRONMENT" not in os.environ:
        os.environ["ENVIRONMENT"] = "local"


@pytest.fixture(scope="session")
def environment() -> str:
    """現在の環境を取得"""
    return os.getenv("ENVIRONMENT", "local")


@pytest.fixture(scope="session")
def is_local(environment: str) -> bool:
    """ローカル環境かどうか"""
    return environment == "local"


@pytest.fixture(scope="session")
def is_aws(environment: str) -> bool:
    """AWS 環境かどうか"""
    return environment == "aws"


# =============================================================================
# VectorStore フィクスチャ
# =============================================================================


@pytest.fixture(scope="function")
def vector_store(environment: str):
    """VectorStore インスタンス"""
    from src.config import get_vector_store

    store = get_vector_store()
    yield store

    # クリーンアップ
    if environment == "local":
        # ローカルの場合はインデックスを削除
        try:
            for index_name in store.list_indices():
                if index_name.startswith("test-"):
                    store.delete_index(index_name)
        except Exception:
            pass


# =============================================================================
# KnowledgeBase フィクスチャ
# =============================================================================


@pytest.fixture(scope="function")
def knowledge_base(environment: str):
    """KnowledgeBase インスタンス"""
    from src.config import get_knowledge_base

    kb = get_knowledge_base()
    yield kb

    # クリーンアップ
    if environment == "local":
        try:
            kb.clear()
        except Exception:
            pass


# =============================================================================
# MemoryStore フィクスチャ
# =============================================================================


@pytest.fixture(scope="function")
def memory_store(environment: str):
    """MemoryStore インスタンス"""
    from src.config import get_memory_store

    memory = get_memory_store()
    yield memory

    # クリーンアップ
    if environment == "local":
        try:
            # テスト用アクターのメモリを削除
            memory.delete_actor_memory("test-actor")
        except Exception:
            pass


# =============================================================================
# GraphStore フィクスチャ
# =============================================================================


@pytest.fixture(scope="function")
def graph_store(environment: str):
    """GraphStore インスタンス"""
    from src.config import get_graph_store

    graph = get_graph_store()
    yield graph

    # クリーンアップ
    if environment == "local":
        try:
            graph.clear()
        except Exception:
            pass


# =============================================================================
# テストデータ
# =============================================================================


@pytest.fixture
def sample_vectors():
    """サンプルベクトルデータ"""
    return [
        {"key": "doc-1", "vector": [0.1] * 128, "metadata": {"title": "Document 1", "category": "tech"}},
        {"key": "doc-2", "vector": [0.2] * 128, "metadata": {"title": "Document 2", "category": "tech"}},
        {"key": "doc-3", "vector": [0.3] * 128, "metadata": {"title": "Document 3", "category": "business"}},
    ]


@pytest.fixture
def sample_documents():
    """サンプルドキュメントデータ"""
    return [
        {
            "id": "doc-1",
            "content": "Amazon S3 Vectors is a new feature for storing and querying vector embeddings.",
            "metadata": {"source": "aws-docs", "topic": "s3-vectors"},
        },
        {
            "id": "doc-2",
            "content": "Amazon Bedrock provides foundation models for building generative AI applications.",
            "metadata": {"source": "aws-docs", "topic": "bedrock"},
        },
        {
            "id": "doc-3",
            "content": "Amazon Neptune is a graph database service for building knowledge graphs.",
            "metadata": {"source": "aws-docs", "topic": "neptune"},
        },
    ]


@pytest.fixture
def sample_events():
    """サンプルメモリイベント"""
    from datetime import datetime

    from src.interfaces import MemoryEvent

    return [
        MemoryEvent(
            actor_id="test-actor",
            session_id="session-1",
            role="USER",
            content="Hello, how are you?",
            timestamp=datetime.now(),
        ),
        MemoryEvent(
            actor_id="test-actor",
            session_id="session-1",
            role="ASSISTANT",
            content="I'm doing well, thank you for asking!",
            timestamp=datetime.now(),
        ),
    ]


@pytest.fixture
def sample_graph_nodes():
    """サンプルグラフノード"""
    from src.interfaces import GraphNode

    return [
        GraphNode(node_id="user-1", node_type="User", properties={"name": "Alice", "email": "alice@example.com"}),
        GraphNode(node_id="user-2", node_type="User", properties={"name": "Bob", "email": "bob@example.com"}),
        GraphNode(node_id="doc-1", node_type="Document", properties={"title": "Project Plan", "version": "1.0"}),
    ]


@pytest.fixture
def sample_graph_edges():
    """サンプルグラフエッジ"""
    from src.interfaces import GraphEdge

    return [
        GraphEdge(edge_id="e-1", source_id="user-1", target_id="doc-1", edge_type="OWNS"),
        GraphEdge(edge_id="e-2", source_id="user-1", target_id="user-2", edge_type="KNOWS"),
    ]
