"""
ローカル Graph アダプタ

Neo4j Docker / NetworkX による GraphStore Protocol 実装。
本番環境では Neptune Serverless を使用。

Usage:
    # Neo4j モード
    graph = LocalGraphStore(
        mode="neo4j",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password"
    )
    
    # NetworkX モード（In-memory）
    graph = LocalGraphStore(mode="networkx")
    
    # ノード作成
    graph.create_node(GraphNode(node_id="user-1", node_type="User", properties={"name": "Alice"}))
    
    # エッジ作成
    graph.create_edge(GraphEdge(
        edge_id="e-1",
        source_id="user-1",
        target_id="doc-1",
        edge_type="OWNS"
    ))
    
    # クエリ実行
    results = graph.query("MATCH (n:User) RETURN n")
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ...interfaces import GraphEdge, GraphNode

logger = logging.getLogger(__name__)


class LocalGraphStore:
    """
    ローカル GraphStore 実装

    モード:
    - "networkx": NetworkX による In-memory グラフ
    - "neo4j": Neo4j Docker による永続グラフ
    """

    def __init__(
        self,
        mode: str = "networkx",
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        persist_dir: str | None = None,
    ):
        """
        Args:
            mode: "networkx" または "neo4j"
            neo4j_uri: Neo4j 接続URI
            neo4j_user: Neo4j ユーザー名
            neo4j_password: Neo4j パスワード
            persist_dir: NetworkX グラフの永続化ディレクトリ
        """
        self.mode = mode
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.persist_dir = Path(persist_dir) if persist_dir else None

        # NetworkX グラフ
        self._graph = None

        # Neo4j ドライバー
        self._neo4j_driver = None

        if mode == "neo4j":
            self._init_neo4j()
        else:
            self._init_networkx()

    def _init_networkx(self) -> None:
        """NetworkX 初期化"""
        try:
            import networkx as nx

            self._graph = nx.DiGraph()

            # 永続化データ読み込み
            if self.persist_dir:
                self._load_from_disk()

            logger.info("LocalGraphStore initialized with NetworkX")

        except ImportError:
            logger.error("networkx not installed")
            raise

    def _init_neo4j(self) -> None:
        """Neo4j 初期化"""
        try:
            from neo4j import GraphDatabase

            self._neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
            )
            # 接続テスト
            with self._neo4j_driver.session() as session:
                session.run("RETURN 1")

            logger.info(f"LocalGraphStore initialized with Neo4j ({self.neo4j_uri})")

        except ImportError:
            logger.warning("neo4j package not installed, falling back to networkx mode")
            self.mode = "networkx"
            self._init_networkx()
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}, falling back to networkx mode")
            self.mode = "networkx"
            self._init_networkx()

    def create_node(
        self,
        node: GraphNode,
    ) -> str:
        """ノード作成"""
        node_id = node.node_id or str(uuid.uuid4())

        if self.mode == "neo4j" and self._neo4j_driver:
            return self._create_node_neo4j(node_id, node)
        return self._create_node_networkx(node_id, node)

    def _create_node_networkx(self, node_id: str, node: GraphNode) -> str:
        """NetworkX でノード作成"""
        self._graph.add_node(
            node_id,
            node_type=node.node_type,
            properties=node.properties,
            embedding=node.embedding,
            created_at=datetime.now().isoformat(),
        )
        self._persist_to_disk()
        logger.debug(f"Created node: {node_id} ({node.node_type})")
        return node_id

    def _create_node_neo4j(self, node_id: str, node: GraphNode) -> str:
        """Neo4j でノード作成"""
        with self._neo4j_driver.session() as session:
            # プロパティをフラット化
            props = {"id": node_id, **node.properties}
            if node.embedding:
                props["embedding"] = node.embedding

            query = f"""
            CREATE (n:{node.node_type} $props)
            RETURN n
            """
            session.run(query, props=props)

        logger.debug(f"Created node in Neo4j: {node_id} ({node.node_type})")
        return node_id

    def get_node(
        self,
        node_id: str,
    ) -> GraphNode | None:
        """ノード取得"""
        if self.mode == "neo4j" and self._neo4j_driver:
            return self._get_node_neo4j(node_id)
        return self._get_node_networkx(node_id)

    def _get_node_networkx(self, node_id: str) -> GraphNode | None:
        """NetworkX からノード取得"""
        if node_id not in self._graph.nodes:
            return None

        data = self._graph.nodes[node_id]
        return GraphNode(
            node_id=node_id,
            node_type=data.get("node_type", ""),
            properties=data.get("properties", {}),
            embedding=data.get("embedding"),
        )

    def _get_node_neo4j(self, node_id: str) -> GraphNode | None:
        """Neo4j からノード取得"""
        with self._neo4j_driver.session() as session:
            result = session.run(
                "MATCH (n {id: $id}) RETURN n, labels(n) as labels",
                id=node_id,
            )
            record = result.single()

            if not record:
                return None

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
        if self.mode == "neo4j" and self._neo4j_driver:
            return self._update_node_neo4j(node_id, properties)
        return self._update_node_networkx(node_id, properties)

    def _update_node_networkx(self, node_id: str, properties: dict[str, Any]) -> bool:
        """NetworkX でノード更新"""
        if node_id not in self._graph.nodes:
            return False

        current_props = self._graph.nodes[node_id].get("properties", {})
        current_props.update(properties)
        self._graph.nodes[node_id]["properties"] = current_props
        self._graph.nodes[node_id]["updated_at"] = datetime.now().isoformat()
        self._persist_to_disk()
        return True

    def _update_node_neo4j(self, node_id: str, properties: dict[str, Any]) -> bool:
        """Neo4j でノード更新"""
        with self._neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (n {id: $id})
                SET n += $props
                RETURN n
                """,
                id=node_id,
                props=properties,
            )
            return result.single() is not None

    def delete_node(
        self,
        node_id: str,
    ) -> bool:
        """ノード削除"""
        if self.mode == "neo4j" and self._neo4j_driver:
            return self._delete_node_neo4j(node_id)
        return self._delete_node_networkx(node_id)

    def _delete_node_networkx(self, node_id: str) -> bool:
        """NetworkX でノード削除"""
        if node_id not in self._graph.nodes:
            return False

        self._graph.remove_node(node_id)
        self._persist_to_disk()
        return True

    def _delete_node_neo4j(self, node_id: str) -> bool:
        """Neo4j でノード削除"""
        with self._neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (n {id: $id})
                DETACH DELETE n
                RETURN count(n) as deleted
                """,
                id=node_id,
            )
            record = result.single()
            return record and record["deleted"] > 0

    def create_edge(
        self,
        edge: GraphEdge,
    ) -> str:
        """エッジ作成"""
        edge_id = edge.edge_id or str(uuid.uuid4())

        if self.mode == "neo4j" and self._neo4j_driver:
            return self._create_edge_neo4j(edge_id, edge)
        return self._create_edge_networkx(edge_id, edge)

    def _create_edge_networkx(self, edge_id: str, edge: GraphEdge) -> str:
        """NetworkX でエッジ作成"""
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            edge_id=edge_id,
            edge_type=edge.edge_type,
            properties=edge.properties,
            valid_from=edge.valid_from.isoformat() if edge.valid_from else None,
            valid_to=edge.valid_to.isoformat() if edge.valid_to else None,
            created_at=datetime.now().isoformat(),
        )
        self._persist_to_disk()
        logger.debug(f"Created edge: {edge.source_id} -[{edge.edge_type}]-> {edge.target_id}")
        return edge_id

    def _create_edge_neo4j(self, edge_id: str, edge: GraphEdge) -> str:
        """Neo4j でエッジ作成"""
        with self._neo4j_driver.session() as session:
            props = {
                "id": edge_id,
                **edge.properties,
            }
            if edge.valid_from:
                props["valid_from"] = edge.valid_from.isoformat()
            if edge.valid_to:
                props["valid_to"] = edge.valid_to.isoformat()

            query = f"""
            MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
            CREATE (a)-[r:{edge.edge_type} $props]->(b)
            RETURN r
            """
            session.run(query, source_id=edge.source_id, target_id=edge.target_id, props=props)

        return edge_id

    def get_edges(
        self,
        node_id: str,
        direction: str = "both",
        edge_type: str | None = None,
    ) -> list[GraphEdge]:
        """エッジ取得"""
        if self.mode == "neo4j" and self._neo4j_driver:
            return self._get_edges_neo4j(node_id, direction, edge_type)
        return self._get_edges_networkx(node_id, direction, edge_type)

    def _get_edges_networkx(
        self,
        node_id: str,
        direction: str,
        edge_type: str | None,
    ) -> list[GraphEdge]:
        """NetworkX からエッジ取得"""
        edges = []

        if direction in ("out", "both"):
            for _, target, data in self._graph.out_edges(node_id, data=True):
                if edge_type and data.get("edge_type") != edge_type:
                    continue
                edges.append(self._edge_data_to_graph_edge(node_id, target, data))

        if direction in ("in", "both"):
            for source, _, data in self._graph.in_edges(node_id, data=True):
                if edge_type and data.get("edge_type") != edge_type:
                    continue
                edges.append(self._edge_data_to_graph_edge(source, node_id, data))

        return edges

    def _edge_data_to_graph_edge(
        self,
        source_id: str,
        target_id: str,
        data: dict[str, Any],
    ) -> GraphEdge:
        """エッジデータを GraphEdge に変換"""
        valid_from = None
        valid_to = None

        if data.get("valid_from"):
            valid_from = datetime.fromisoformat(data["valid_from"])
        if data.get("valid_to"):
            valid_to = datetime.fromisoformat(data["valid_to"])

        return GraphEdge(
            edge_id=data.get("edge_id", ""),
            source_id=source_id,
            target_id=target_id,
            edge_type=data.get("edge_type", ""),
            properties=data.get("properties", {}),
            valid_from=valid_from,
            valid_to=valid_to,
        )

    def _get_edges_neo4j(
        self,
        node_id: str,
        direction: str,
        edge_type: str | None,
    ) -> list[GraphEdge]:
        """Neo4j からエッジ取得"""
        edges = []
        type_filter = f":{edge_type}" if edge_type else ""

        with self._neo4j_driver.session() as session:
            if direction in ("out", "both"):
                result = session.run(
                    f"""
                    MATCH (a {{id: $id}})-[r{type_filter}]->(b)
                    RETURN a.id as source, b.id as target, type(r) as type, properties(r) as props
                    """,
                    id=node_id,
                )
                for record in result:
                    edges.append(self._neo4j_record_to_edge(record))

            if direction in ("in", "both"):
                result = session.run(
                    f"""
                    MATCH (a)-[r{type_filter}]->(b {{id: $id}})
                    RETURN a.id as source, b.id as target, type(r) as type, properties(r) as props
                    """,
                    id=node_id,
                )
                for record in result:
                    edges.append(self._neo4j_record_to_edge(record))

        return edges

    def _neo4j_record_to_edge(self, record) -> GraphEdge:
        """Neo4j レコードを GraphEdge に変換"""
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
        if self.mode == "neo4j" and self._neo4j_driver:
            return self._delete_edge_neo4j(edge_id)
        return self._delete_edge_networkx(edge_id)

    def _delete_edge_networkx(self, edge_id: str) -> bool:
        """NetworkX でエッジ削除"""
        for u, v, data in list(self._graph.edges(data=True)):
            if data.get("edge_id") == edge_id:
                self._graph.remove_edge(u, v)
                self._persist_to_disk()
                return True
        return False

    def _delete_edge_neo4j(self, edge_id: str) -> bool:
        """Neo4j でエッジ削除"""
        with self._neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH ()-[r {id: $id}]->()
                DELETE r
                RETURN count(r) as deleted
                """,
                id=edge_id,
            )
            record = result.single()
            return record and record["deleted"] > 0

    def query(
        self,
        query_string: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """クエリ実行（Cypher）"""
        if self.mode == "neo4j" and self._neo4j_driver:
            return self._query_neo4j(query_string, parameters)
        return self._query_networkx(query_string, parameters)

    def _query_networkx(
        self,
        query_string: str,
        parameters: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """NetworkX での簡易クエリ（限定的なサポート）"""
        # 簡易的な実装：全ノードを返す
        logger.warning("NetworkX mode only supports basic queries")
        results = []

        for node_id in self._graph.nodes:
            data = self._graph.nodes[node_id]
            results.append({
                "id": node_id,
                "type": data.get("node_type"),
                "properties": data.get("properties", {}),
            })

        return results

    def _query_neo4j(
        self,
        query_string: str,
        parameters: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Neo4j でクエリ実行"""
        with self._neo4j_driver.session() as session:
            result = session.run(query_string, parameters or {})
            return [dict(record) for record in result]

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> list[GraphNode] | None:
        """最短パス検索"""
        if self.mode == "neo4j" and self._neo4j_driver:
            return self._find_path_neo4j(source_id, target_id, max_depth)
        return self._find_path_networkx(source_id, target_id, max_depth)

    def _find_path_networkx(
        self,
        source_id: str,
        target_id: str,
        max_depth: int,
    ) -> list[GraphNode] | None:
        """NetworkX で最短パス検索"""
        import networkx as nx

        try:
            path = nx.shortest_path(
                self._graph,
                source=source_id,
                target=target_id,
            )

            if len(path) > max_depth + 1:
                return None

            return [self._get_node_networkx(node_id) for node_id in path]

        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound:
            return None

    def _find_path_neo4j(
        self,
        source_id: str,
        target_id: str,
        max_depth: int,
    ) -> list[GraphNode] | None:
        """Neo4j で最短パス検索"""
        with self._neo4j_driver.session() as session:
            result = session.run(
                f"""
                MATCH path = shortestPath((a {{id: $source}})-[*..{max_depth}]->(b {{id: $target}}))
                RETURN nodes(path) as nodes
                """,
                source=source_id,
                target=target_id,
            )
            record = result.single()

            if not record:
                return None

            nodes = []
            for node in record["nodes"]:
                node_data = dict(node)
                node_id = node_data.pop("id", "")
                labels = list(node.labels)
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
        if self.mode == "neo4j" and self._neo4j_driver:
            return self._get_neighbors_neo4j(node_id, depth, edge_types)
        return self._get_neighbors_networkx(node_id, depth, edge_types)

    def _get_neighbors_networkx(
        self,
        node_id: str,
        depth: int,
        edge_types: list[str] | None,
    ) -> list[GraphNode]:
        """NetworkX で隣接ノード取得"""
        import networkx as nx

        visited = set()
        current_level = {node_id}

        for _ in range(depth):
            next_level = set()
            for n in current_level:
                # 出エッジ
                for _, target, data in self._graph.out_edges(n, data=True):
                    if edge_types and data.get("edge_type") not in edge_types:
                        continue
                    if target not in visited and target != node_id:
                        next_level.add(target)

                # 入エッジ
                for source, _, data in self._graph.in_edges(n, data=True):
                    if edge_types and data.get("edge_type") not in edge_types:
                        continue
                    if source not in visited and source != node_id:
                        next_level.add(source)

            visited.update(next_level)
            current_level = next_level

        return [self._get_node_networkx(n) for n in visited if n]

    def _get_neighbors_neo4j(
        self,
        node_id: str,
        depth: int,
        edge_types: list[str] | None,
    ) -> list[GraphNode]:
        """Neo4j で隣接ノード取得"""
        type_filter = ""
        if edge_types:
            type_filter = ":" + "|".join(edge_types)

        with self._neo4j_driver.session() as session:
            result = session.run(
                f"""
                MATCH (a {{id: $id}})-[{type_filter}*1..{depth}]-(b)
                WHERE a <> b
                RETURN DISTINCT b, labels(b) as labels
                """,
                id=node_id,
            )

            neighbors = []
            for record in result:
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
    # Private Methods
    # =========================================================================

    def _persist_to_disk(self) -> None:
        """ディスクに永続化（NetworkX モード）"""
        if not self.persist_dir or self.mode != "networkx":
            return

        import networkx as nx

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        graph_file = self.persist_dir / "graph.json"

        data = nx.node_link_data(self._graph)
        graph_file.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))

    def _load_from_disk(self) -> None:
        """ディスクから読み込み（NetworkX モード）"""
        if not self.persist_dir:
            return

        import networkx as nx

        graph_file = self.persist_dir / "graph.json"
        if graph_file.exists():
            try:
                data = json.loads(graph_file.read_text())
                self._graph = nx.node_link_graph(data, directed=True)
                logger.info(f"Loaded graph from disk ({len(self._graph.nodes)} nodes)")
            except Exception as e:
                logger.error(f"Failed to load graph: {e}")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        """統計情報取得"""
        if self.mode == "neo4j" and self._neo4j_driver:
            with self._neo4j_driver.session() as session:
                node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
                edge_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
        else:
            node_count = self._graph.number_of_nodes()
            edge_count = self._graph.number_of_edges()

        return {
            "mode": self.mode,
            "node_count": node_count,
            "edge_count": edge_count,
        }

    def clear(self) -> None:
        """全データ削除"""
        if self.mode == "neo4j" and self._neo4j_driver:
            with self._neo4j_driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
        else:
            self._graph.clear()
            self._persist_to_disk()

        logger.info("Cleared all graph data")

    def close(self) -> None:
        """接続クローズ"""
        if self._neo4j_driver:
            self._neo4j_driver.close()
            self._neo4j_driver = None
