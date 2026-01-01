"""
共通インターフェース(Protocol)定義

ローカル環境(LocalStack/FAISS/SQLite/Neo4j)と
AWS本番環境(S3 Vectors/Bedrock KB/AgentCore Memory/Neptune)で
同一インターフェースを使用するための抽象化層。

Usage:
    # 環境変数で切り替え
    ENV = os.getenv("ENVIRONMENT", "local")
    
    if ENV == "local":
        vector_store = LocalVectorStore()
    else:
        vector_store = AWSVectorStore(region="us-west-2")
    
    # 同一インターフェースで操作
    vector_store.put_vectors([...])
    results = vector_store.query_vectors(query_vector, top_k=10)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


# =============================================================================
# データクラス定義
# =============================================================================


@dataclass
class VectorRecord:
    """ベクトルレコード"""

    key: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    namespace: str | None = None


@dataclass
class SearchResult:
    """検索結果"""

    key: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    content: str | None = None


@dataclass
class MemoryEvent:
    """メモリイベント（会話履歴）"""

    actor_id: str
    session_id: str
    role: str  # "USER" | "ASSISTANT"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryRecord:
    """メモリレコード（検索結果）"""

    record_id: str
    content: str
    memory_type: str  # "episodic" | "semantic" | "reflection"
    timestamp: datetime
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphNode:
    """グラフノード"""

    node_id: str
    node_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


@dataclass
class GraphEdge:
    """グラフエッジ"""

    edge_id: str
    source_id: str
    target_id: str
    edge_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    valid_from: datetime | None = None
    valid_to: datetime | None = None


# =============================================================================
# Protocol定義
# =============================================================================


@runtime_checkable
class VectorStore(Protocol):
    """
    ベクトルストア Protocol

    実装:
    - Local: FAISS / In-memory / LocalStack S3
    - AWS: S3 Vectors (boto3.client("s3vectors"))
    """

    def create_index(
        self,
        index_name: str,
        dimension: int,
        distance_metric: str = "cosine",
    ) -> str:
        """インデックス作成"""
        ...

    def delete_index(self, index_name: str) -> bool:
        """インデックス削除"""
        ...

    def put_vectors(
        self,
        index_name: str,
        vectors: list[VectorRecord],
    ) -> int:
        """ベクトル挿入（返り値: 挿入件数）"""
        ...

    def query_vectors(
        self,
        index_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """ベクトル検索"""
        ...

    def delete_vectors(
        self,
        index_name: str,
        keys: list[str],
    ) -> int:
        """ベクトル削除（返り値: 削除件数）"""
        ...

    def get_vector(
        self,
        index_name: str,
        key: str,
    ) -> VectorRecord | None:
        """単一ベクトル取得"""
        ...


@runtime_checkable
class KnowledgeBase(Protocol):
    """
    ナレッジベース Protocol (RAG)

    実装:
    - Local: Ollama + ChromaDB / Mock
    - AWS: Bedrock Knowledge Base (boto3.client("bedrock-agent-runtime"))
    """

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """ドキュメント検索"""
        ...

    def retrieve_and_generate(
        self,
        query: str,
        model_id: str | None = None,
        top_k: int = 5,
    ) -> str:
        """検索 + 回答生成 (RAG)"""
        ...

    def ingest_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> int:
        """ドキュメント取り込み（返り値: 取り込み件数）"""
        ...

    def list_documents(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """ドキュメント一覧"""
        ...


@runtime_checkable
class MemoryStore(Protocol):
    """
    メモリストア Protocol (Agent Memory)

    実装:
    - Local: SQLite + In-memory / Redis
    - AWS: AgentCore Memory (boto3.client("bedrock-agentcore"))

    メモリタイプ:
    - Short-term: セッション中のコンテキスト
    - Episodic: 会話の要約
    - Semantic: 学習した事実・知識
    - Reflections: ユーザーの好み・傾向
    """

    def create_event(
        self,
        events: list[MemoryEvent],
    ) -> str:
        """イベント保存（Short-term Memory）"""
        ...

    def retrieve_records(
        self,
        actor_id: str,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
    ) -> list[MemoryRecord]:
        """メモリ検索（セマンティック検索）"""
        ...

    def get_session_history(
        self,
        actor_id: str,
        session_id: str,
        limit: int = 50,
    ) -> list[MemoryEvent]:
        """セッション履歴取得"""
        ...

    def delete_actor_memory(
        self,
        actor_id: str,
    ) -> bool:
        """アクターのメモリ全削除"""
        ...


@runtime_checkable
class GraphStore(Protocol):
    """
    グラフストア Protocol (Knowledge Graph)

    実装:
    - Local: Neo4j (Docker) / NetworkX
    - AWS: Neptune Serverless / Neptune Analytics

    クエリ言語:
    - Local: Cypher
    - AWS: Gremlin / openCypher / SPARQL
    """

    def create_node(
        self,
        node: GraphNode,
    ) -> str:
        """ノード作成"""
        ...

    def get_node(
        self,
        node_id: str,
    ) -> GraphNode | None:
        """ノード取得"""
        ...

    def update_node(
        self,
        node_id: str,
        properties: dict[str, Any],
    ) -> bool:
        """ノード更新"""
        ...

    def delete_node(
        self,
        node_id: str,
    ) -> bool:
        """ノード削除"""
        ...

    def create_edge(
        self,
        edge: GraphEdge,
    ) -> str:
        """エッジ作成"""
        ...

    def get_edges(
        self,
        node_id: str,
        direction: str = "both",  # "in" | "out" | "both"
        edge_type: str | None = None,
    ) -> list[GraphEdge]:
        """エッジ取得"""
        ...

    def delete_edge(
        self,
        edge_id: str,
    ) -> bool:
        """エッジ削除"""
        ...

    def query(
        self,
        query_string: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """クエリ実行（Cypher/Gremlin）"""
        ...

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> list[GraphNode] | None:
        """最短パス検索"""
        ...

    def get_neighbors(
        self,
        node_id: str,
        depth: int = 1,
        edge_types: list[str] | None = None,
    ) -> list[GraphNode]:
        """隣接ノード取得"""
        ...


# =============================================================================
# 型エイリアス
# =============================================================================

# 環境設定用の型
EnvironmentType = str  # "local" | "aws"

# ベクトル型
Vector = list[float]

# メタデータ型
Metadata = dict[str, Any]

