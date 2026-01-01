"""
AWS GraphStore アダプタ（Neo4j AuraDB 対応）

Neptune を廃止し、Neo4j AuraDB（マネージドクラウド）を使用。
ローカル Neo4j Docker とも互換性あり。

Neo4j AuraDB は AWS に依存しない、クラウドネイティブなグラフデータベース。
Free Tier あり（開発/検証向け）。

GRAPHITI_INTEGRATION_DESIGN.md のパターンを参考。
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any

from ...interfaces import GraphEdge, GraphNode

logger = logging.getLogger(__name__)


class AWSGraphStore:
    """
    AWS GraphStore 実装 (Neo4j AuraDB)

    Neptune ではなく Neo4j AuraDB を使用することで:
    - AWS 依存を排除
    - Graphiti との親和性向上
    - コスト削減（Free Tier あり）
    - Cypher クエリ言語の利用

    Usage:
        # 環境変数から自動設定
        graph = AWSGraphStore()

        # 明示的に指定
        graph = AWSGraphStore(
            uri="neo4j+s://xxxxx.databases.neo4j.io",
            user="neo4j",
            password="your-password"
        )

        # ノード作成
        graph.create_node(GraphNode(node_id="agent-1", node_type="Agent", properties={"name": "CMS"}))

        # エッジ作成
        graph.create_edge(GraphEdge(source_id="agent-1", target_id="task-1", edge_type="EXECUTES"))
    """

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str = "neo4j",
    ):
        """
        Args:
            uri: Neo4j 接続 URI (neo4j+s://xxx for AuraDB, bolt://xxx for local)
            user: Neo4j ユーザー名
            password: Neo4j パスワード
            database: データベース名（デフォルト: neo4j）
        """
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "password")
        self.database = database

        self._driver = None
        self._connect()

        logger.info(f"AWSGraphStore initialized (uri={self._mask_uri(self.uri)})")

    def _mask_uri(self, uri: str) -> str:
        """URI をマスク（ログ用）"""
        if "@" in uri:
            # neo4j+s://user:pass@host の形式
            parts = uri.split("@")
            return f"***@{parts[-1]}"
        return uri

    def _connect(self) -> None:
        """Neo4j に接続"""
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            # 接続テスト
            with self._driver.session(database=self.database) as session:
                session.run("RETURN 1")

            logger.info("Connected to Neo4j")

        except ImportError:
            logger.error("neo4j package not installed. Run: pip install neo4j")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def _execute(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Cypher クエリ実行"""
        if not self._driver:
            raise RuntimeError("Neo4j not connected")

        with self._driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def create_node(
        self,
        node: GraphNode,
    ) -> str:
        """ノード作成"""
        node_id = node.node_id or str(uuid.uuid4())

        props = {"id": node_id, **node.properties}
        if node.embedding:
            props["embedding"] = node.embedding

        query = f"""
        CREATE (n:{node.node_type} $props)
        RETURN n
        """
        self._execute(query, {"props": props})

        logger.debug(f"Created node: {node_id} ({node.node_type})")
        return node_id

    def get_node(
        self,
        node_id: str,
    ) -> GraphNode | None:
        """ノード取得"""
        results = self._execute(
            "MATCH (n {id: $id}) RETURN n, labels(n) as labels",
            {"id": node_id},
        )

        if not results:
            return None

        record = results[0]
        node_data = dict(record["n"])
        labels = record["labels"]
        node_type = labels[0] if labels else ""

        embedding = node_data.pop("embedding", None)
        node_data.pop("id", None)

        return GraphNode(
            node_id=node_id,
            node_type=node_type,
            properties=node_data,
            embedding=embedding,
        )

    def update_node(
        self,
        node_id: str,
        properties: dict[str, Any],
    ) -> bool:
        """ノード更新"""
        results = self._execute(
            """
            MATCH (n {id: $id})
            SET n += $props
            RETURN n
            """,
            {"id": node_id, "props": properties},
        )
        return len(results) > 0

    def delete_node(
        self,
        node_id: str,
    ) -> bool:
        """ノード削除"""
        results = self._execute(
            """
            MATCH (n {id: $id})
            DETACH DELETE n
            RETURN count(n) as deleted
            """,
            {"id": node_id},
        )
        return results[0]["deleted"] > 0 if results else False

    def create_edge(
        self,
        edge: GraphEdge,
    ) -> str:
        """エッジ作成"""
        edge_id = edge.edge_id or str(uuid.uuid4())

        props = {"id": edge_id, **edge.properties}
        if edge.valid_from:
            props["valid_from"] = edge.valid_from.isoformat()
        if edge.valid_to:
            props["valid_to"] = edge.valid_to.isoformat()

        # Cypher は動的リレーションシップタイプに APOC が必要
        # 静的に生成するか、APOC を使う
        query = f"""
        MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
        CREATE (a)-[r:{edge.edge_type} $props]->(b)
        RETURN r
        """
        self._execute(
            query,
            {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "props": props,
            },
        )

        logger.debug(f"Created edge: {edge.source_id} -[{edge.edge_type}]-> {edge.target_id}")
        return edge_id

    def get_edges(
        self,
        node_id: str,
        direction: str = "both",
        edge_type: str | None = None,
    ) -> list[GraphEdge]:
        """エッジ取得"""
        edges = []
        type_filter = f":{edge_type}" if edge_type else ""

        if direction in ("out", "both"):
            results = self._execute(
                f"""
                MATCH (a {{id: $id}})-[r{type_filter}]->(b)
                RETURN a.id as source, b.id as target, type(r) as type, properties(r) as props
                """,
                {"id": node_id},
            )
            for record in results:
                edges.append(self._record_to_edge(record))

        if direction in ("in", "both"):
            results = self._execute(
                f"""
                MATCH (a)-[r{type_filter}]->(b {{id: $id}})
                RETURN a.id as source, b.id as target, type(r) as type, properties(r) as props
                """,
                {"id": node_id},
            )
            for record in results:
                edges.append(self._record_to_edge(record))

        return edges

    def _record_to_edge(self, record: dict[str, Any]) -> GraphEdge:
        """レコードを GraphEdge に変換"""
        props = dict(record["props"])
        edge_id = props.pop("id", str(uuid.uuid4()))

        valid_from = None
        valid_to = None
        if props.get("valid_from"):
            valid_from = datetime.fromisoformat(props.pop("valid_from"))
        if props.get("valid_to"):
            valid_to = datetime.fromisoformat(props.pop("valid_to"))

        return GraphEdge(
            edge_id=edge_id,
            source_id=record["source"],
            target_id=record["target"],
            edge_type=record["type"],
            properties=props,
            valid_from=valid_from,
            valid_to=valid_to,
        )

    def delete_edge(
        self,
        edge_id: str,
    ) -> bool:
        """エッジ削除"""
        results = self._execute(
            """
            MATCH ()-[r {id: $id}]->()
            DELETE r
            RETURN count(r) as deleted
            """,
            {"id": edge_id},
        )
        return results[0]["deleted"] > 0 if results else False

    def query(
        self,
        query_string: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Cypher クエリ実行"""
        return self._execute(query_string, parameters)

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> list[GraphNode] | None:
        """最短パス検索"""
        results = self._execute(
            f"""
            MATCH path = shortestPath((a {{id: $source}})-[*..{max_depth}]-(b {{id: $target}}))
            RETURN nodes(path) as nodes
            """,
            {"source": source_id, "target": target_id},
        )

        if not results:
            return None

        nodes = []
        for node in results[0]["nodes"]:
            node_data = dict(node)
            node_id = node_data.pop("id", "")
            labels = list(node.labels) if hasattr(node, "labels") else []
            node_type = labels[0] if labels else ""
            embedding = node_data.pop("embedding", None)

            nodes.append(
                GraphNode(
                    node_id=node_id,
                    node_type=node_type,
                    properties=node_data,
                    embedding=embedding,
                )
            )

        return nodes

    def get_neighbors(
        self,
        node_id: str,
        depth: int = 1,
        edge_types: list[str] | None = None,
    ) -> list[GraphNode]:
        """隣接ノード取得"""
        type_filter = ""
        if edge_types:
            type_filter = ":" + "|".join(edge_types)

        results = self._execute(
            f"""
            MATCH (a {{id: $id}})-[{type_filter}*1..{depth}]-(b)
            WHERE a <> b
            RETURN DISTINCT b, labels(b) as labels
            """,
            {"id": node_id},
        )

        neighbors = []
        for record in results:
            node_data = dict(record["b"])
            neighbor_id = node_data.pop("id", "")
            labels = record["labels"]
            node_type = labels[0] if labels else ""
            embedding = node_data.pop("embedding", None)

            neighbors.append(
                GraphNode(
                    node_id=neighbor_id,
                    node_type=node_type,
                    properties=node_data,
                    embedding=embedding,
                )
            )

        return neighbors

    # =========================================================================
    # Graphiti 互換メソッド
    # =========================================================================

    def add_episode(
        self,
        episode_id: str,
        content: str,
        timestamp: datetime,
        source: str = "conversation",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        エピソード（時系列イベント）を追加

        Graphiti の dual-temporal model に対応:
        - event_time: イベント発生時刻
        - ingestion_time: データ取り込み時刻
        """
        props = {
            "content": content,
            "event_time": timestamp.isoformat(),
            "ingestion_time": datetime.now().isoformat(),
            "source": source,
            **(metadata or {}),
        }

        return self.create_node(
            GraphNode(
                node_id=episode_id,
                node_type="Episode",
                properties=props,
            )
        )

    def extract_entities(
        self,
        episode_id: str,
        entities: list[dict[str, Any]],
    ) -> list[str]:
        """
        エピソードからエンティティを抽出・リンク

        Args:
            episode_id: エピソードID
            entities: [{"id": "...", "type": "Person", "name": "..."}]
        """
        entity_ids = []

        for entity in entities:
            entity_id = entity.get("id", str(uuid.uuid4()))
            entity_type = entity.get("type", "Entity")
            entity_name = entity.get("name", "")

            # MERGE でエンティティを upsert
            self._execute(
                f"""
                MERGE (e:{entity_type} {{id: $id}})
                ON CREATE SET e.name = $name, e.created_at = $now
                ON MATCH SET e.updated_at = $now
                RETURN e
                """,
                {
                    "id": entity_id,
                    "name": entity_name,
                    "now": datetime.now().isoformat(),
                },
            )

            # エピソードとエンティティをリンク
            self.create_edge(
                GraphEdge(
                    source_id=episode_id,
                    target_id=entity_id,
                    edge_type="MENTIONS",
                    properties={"extracted_at": datetime.now().isoformat()},
                )
            )

            entity_ids.append(entity_id)

        return entity_ids

    def search_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        node_types: list[str] | None = None,
    ) -> list[GraphNode]:
        """
        時間範囲でノードを検索

        Graphiti の temporal query に対応
        """
        type_filter = ""
        if node_types:
            type_filter = ":" + ":".join(node_types)

        results = self._execute(
            f"""
            MATCH (n{type_filter})
            WHERE n.event_time >= $start AND n.event_time <= $end
            RETURN n, labels(n) as labels
            ORDER BY n.event_time DESC
            """,
            {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
        )

        nodes = []
        for record in results:
            node_data = dict(record["n"])
            node_id = node_data.pop("id", "")
            labels = record["labels"]
            node_type = labels[0] if labels else ""
            embedding = node_data.pop("embedding", None)

            nodes.append(
                GraphNode(
                    node_id=node_id,
                    node_type=node_type,
                    properties=node_data,
                    embedding=embedding,
                )
            )

        return nodes

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        """統計情報取得"""
        node_result = self._execute("MATCH (n) RETURN count(n) as count")
        edge_result = self._execute("MATCH ()-[r]->() RETURN count(r) as count")

        return {
            "backend": "neo4j",
            "uri": self._mask_uri(self.uri),
            "node_count": node_result[0]["count"] if node_result else 0,
            "edge_count": edge_result[0]["count"] if edge_result else 0,
        }

    def clear(self) -> None:
        """全データ削除（注意: 本番では使用禁止）"""
        self._execute("MATCH (n) DETACH DELETE n")
        logger.warning("Cleared all graph data")

    def close(self) -> None:
        """接続クローズ"""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")
