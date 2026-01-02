"""
環境設定・アダプタ切り替え

環境変数 ENVIRONMENT で local/aws を切り替え。
各サービスのアダプタを動的にロードする。

Usage:
    from src.config import get_vector_store, get_knowledge_base, get_memory_store, get_graph_store
    
    # 環境変数に基づいて適切なアダプタを取得
    vector_store = get_vector_store()
    kb = get_knowledge_base()
    memory = get_memory_store()
    graph = get_graph_store()
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .interfaces import GraphStore, KnowledgeBase, MemoryStore, VectorStore


# =============================================================================
# 環境設定
# =============================================================================


@dataclass
class LocalConfig:
    """ローカル環境設定"""

    # LocalStack
    localstack_endpoint: str = "http://localhost:4566"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # SQLite
    sqlite_path: str = ":memory:"


@dataclass
class AWSConfig:
    """AWS本番環境設定"""

    # 共通
    region: str = "ap-northeast-1"

    # S3 Vectors
    vector_bucket_name: str = ""
    vector_region: str = "ap-northeast-1"

    # Bedrock Knowledge Base
    knowledge_base_id: str = ""
    embedding_model_arn: str = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
    generation_model_arn: str = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"

    # AgentCore Memory
    memory_id: str = ""
    memory_region: str = "us-east-1"

    # Neo4j (Neptune廃止)
    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"


@lru_cache
def get_environment() -> str:
    """現在の環境を取得"""
    return os.getenv("ENVIRONMENT", "local")


@lru_cache
def get_local_config() -> LocalConfig:
    """ローカル設定を取得"""
    return LocalConfig(
        localstack_endpoint=os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566"),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "password"),
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        sqlite_path=os.getenv("SQLITE_PATH", ":memory:"),
    )


@lru_cache
def get_aws_config() -> AWSConfig:
    """AWS設定を取得"""
    return AWSConfig(
        region=os.getenv("AWS_REGION", "ap-northeast-1"),
        vector_bucket_name=os.getenv("VECTOR_BUCKET_NAME", "rd-knowledge-vectors-dev"),
        vector_region=os.getenv("VECTOR_REGION", "ap-northeast-1"),
        knowledge_base_id=os.getenv("KNOWLEDGE_BASE_ID", ""),
        embedding_model_arn=os.getenv(
            "EMBEDDING_MODEL_ARN",
            "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0",
        ),
        generation_model_arn=os.getenv(
            "GENERATION_MODEL_ARN",
            "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
        ),
        memory_id=os.getenv("MEMORY_ID", "rdKnowledgeMemoryDev-gJ7WAs96sJ"),
        memory_region=os.getenv("MEMORY_REGION", "us-east-1"),
        neo4j_uri=os.getenv("NEO4J_URI", ""),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", ""),
        neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )


# =============================================================================
# アダプタファクトリ
# =============================================================================


def get_vector_store() -> "VectorStore":
    """
    VectorStore アダプタを取得

    Returns:
        VectorStore: 環境に応じたアダプタ
            - local: LocalVectorStore (FAISS/In-memory)
            - aws: AWSVectorStore (S3 Vectors)
    """
    env = get_environment()

    if env == "local":
        from .adapters.local.vector_store import LocalVectorStore

        config = get_local_config()
        return LocalVectorStore(endpoint=config.localstack_endpoint)
    else:
        from .adapters.aws.vector_store import AWSVectorStore

        config = get_aws_config()
        return AWSVectorStore(
            region=config.vector_region,  # S3 Vectors は ap-northeast-1 で作成済み
            bucket_name=config.vector_bucket_name,
        )


def get_knowledge_base() -> "KnowledgeBase":
    """
    KnowledgeBase アダプタを取得

    Returns:
        KnowledgeBase: 環境に応じたアダプタ
            - local: LocalKnowledgeBase (Ollama + ChromaDB)
            - aws: AWSKnowledgeBase (Bedrock KB)
    """
    env = get_environment()

    if env == "local":
        from .adapters.local.knowledge_base import LocalKnowledgeBase

        config = get_local_config()
        return LocalKnowledgeBase(
            ollama_url=config.ollama_base_url,
            model=config.ollama_model,
        )
    else:
        from .adapters.aws.knowledge_base import AWSKnowledgeBase

        config = get_aws_config()
        return AWSKnowledgeBase(
            region=config.region,
            knowledge_base_id=config.knowledge_base_id,
            generation_model_arn=config.generation_model_arn,
        )


def get_memory_store() -> "MemoryStore":
    """
    MemoryStore アダプタを取得

    Returns:
        MemoryStore: 環境に応じたアダプタ
            - local: LocalMemoryStore (SQLite)
            - aws: AWSMemoryStore (AgentCore Memory)
    """
    env = get_environment()

    if env == "local":
        from .adapters.local.memory_store import LocalMemoryStore

        config = get_local_config()
        return LocalMemoryStore(db_path=config.sqlite_path)
    else:
        from .adapters.aws.memory_store import AWSMemoryStore

        config = get_aws_config()
        return AWSMemoryStore(
            region=config.memory_region,  # Memory は us-east-1 で作成済み
            memory_id=config.memory_id,
        )


def get_graph_store() -> "GraphStore":
    """
    GraphStore アダプタを取得

    Returns:
        GraphStore: 環境に応じたアダプタ
            - local: LocalGraphStore (Neo4j)
            - aws: AWSGraphStore (Neo4j AuraDB / EC2 Neo4j)
    """
    env = get_environment()

    if env == "local":
        from .adapters.local.graph_store import LocalGraphStore

        config = get_local_config()
        return LocalGraphStore(
            uri=config.neo4j_uri,
            user=config.neo4j_user,
            password=config.neo4j_password,
        )
    else:
        from .adapters.aws.graph_store import AWSGraphStore

        config = get_aws_config()
        return AWSGraphStore(
            uri=config.neo4j_uri,
            user=config.neo4j_user,
            password=config.neo4j_password,
            database=config.neo4j_database,
        )


# =============================================================================
# 環境情報表示
# =============================================================================


def print_environment_info() -> None:
    """現在の環境情報を表示"""
    env = get_environment()
    print(f"🌍 Environment: {env}")

    if env == "local":
        config = get_local_config()
        print(f"  📦 LocalStack: {config.localstack_endpoint}")
        print(f"  🕸️  Neo4j: {config.neo4j_uri}")
        print(f"  🔴 Redis: {config.redis_host}:{config.redis_port}")
        print(f"  🦙 Ollama: {config.ollama_base_url} ({config.ollama_model})")
    else:
        config = get_aws_config()
        print(f"  🌐 Region: {config.region}")
        print(f"  🗄️  Vector Bucket: {config.vector_bucket_name or '(not set)'} ({config.vector_region})")
        print(f"  📚 Knowledge Base: {config.knowledge_base_id or '(not set)'}")
        print(f"  🧠 Memory ID: {config.memory_id or '(not set)'} ({config.memory_region})")
        print(f"  🕸️  Neo4j: {config.neo4j_uri or '(not set)'}")

