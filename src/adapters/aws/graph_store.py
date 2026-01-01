"""
AWS GraphStore アダプタ

Neptune Serverless + Gremlin による Graph 実装。
GRAPHITI_INTEGRATION_DESIGN.md のパターンを参考。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ...interfaces import GraphEdge, GraphNode

logger = logging.getLogger(__name__)


class AWSGraphStore:
    """
    AWS GraphStore 実装 (Neptune Serverless)

    Usage:
        graph = AWSGraphStore(region="us-west-2", endpoint="my-neptune.cluster.neptune.amazonaws.com")
        graph.create_node(GraphNode(node_id="agent-1", node_type="Agent", properties={"name": "CMS"}))
        graph.create_edge(GraphEdge(source_id="agent-1", target_id="task-1", edge_type="EXECUTES"))
    """

    def __init__(
        self,
        region: str = "us-west-2",
        endpoint: str = "",
        port: int = 8182,
    ):
        """
        Args:
            region: AWS リージョン
            endpoint: Neptune エンドポイント
            port: Neptune ポート
        """
        self.region = region
        self.endpoint = endpoint
        self.port = port

        # Gremlin クライアント
        self._gremlin_client = None
        self._connect()

        logger.info(f"AWSGraphStore initialized (endpoint={endpoint})")

    def _connect(self) -> None:
        """Neptune に接続"""
        if not self.endpoint:
            logger.warning("Neptune endpoint not configured")
            return

        try:
            from gremlin_python.driver import client, serializer

            self._gremlin_client = client.Client(
                f"wss://{self.endpoint}:{self.port}/gremlin",
                "g",
                message_serializer=serializer.GraphSONSerializersV2d0(),
            )
            logger.info("Connected to Neptune")
        except ImportError:
            logger.warning("gremlin-python not installed")
        except Exception as e:
            logger.error(f"Failed to connect to Neptune: {e}")

    def _execute(self, query: str, bindings: dict[str, Any] | None = None) -> list[Any]:
        """Gremlin クエリ実行"""
        if not self._gremlin_client:
            logger.warning("Neptune not connected")
            return []

        try:
            result = self._gremlin_client.submit(query, bindings=bindings or {})
            return result.all().result()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []

    def create_node(
        self,
        node: GraphNode,
    ) -> str:
        """ノード作成"""
        # プロパティをフラット化
        props = {"id": node.node_id, **node.properties}
        props_str = ".".join([f"property('{k}', '{v}')" for k, v in props.items()])

        query = f"g.addV('{node.node_type}').{props_str}"
        self._execute(query)

        logger.debug(f"Created node: {node.node_id}")
        return node.node_id

    def get_node(
        self,
        node_id: str,
    ) -> GraphNode | None:
        """ノード取得"""
        query = "g.V().has('id', node_id).valueMap(true)"
        results = self._execute(query, {"node_id": node_id})

        if results:
            props = results[0]
            return GraphNode(
                node_id=node_id,
                node_type=props.get("label", ["Unknown"])[0],
                properties={k: v[0] if isinstance(v, list) else v for k, v in props.items()},
            )
        return None

    def update_node(
        self,
        node_id: str,
        properties: dict[str, Any],
    ) -> bool:
        """ノード更新"""
        props_str = ".".join([f"property('{k}', '{v}')" for k, v in properties.items()])
        query = f"g.V().has('id', '{node_id}').{props_str}"
        self._execute(query)
        return True

    def delete_node(
        self,
        node_id: str,
    ) -> bool:
        """ノード削除"""
        query = f"g.V().has('id', '{node_id}').drop()"
        self._execute(query)
        return True

    def create_edge(
        self,
        edge: GraphEdge,
    ) -> str:
        """エッジ作成"""
        props = {"id": edge.edge_id, **edge.properties}
        if edge.valid_from:
            props["valid_from"] = edge.valid_from.isoformat()
        if edge.valid_to:
            props["valid_to"] = edge.valid_to.isoformat()

        props_str = ".".join([f"property('{k}', '{v}')" for k, v in props.items()])

        query = f"""
            g.V().has('id', '{edge.source_id}')
             .addE('{edge.edge_type}')
             .to(g.V().has('id', '{edge.target_id}'))
             .{props_str}
        """
        self._execute(query)

        logger.debug(f"Created edge: {edge.edge_id}")
        return edge.edge_id

    def get_edges(
        self,
        node_id: str,
        direction: str = "both",
        edge_type: str | None = None,
    ) -> list[GraphEdge]:
        """エッジ取得"""
        if direction == "out":
            query = f"g.V().has('id', '{node_id}').outE()"
        elif direction == "in":
            query = f"g.V().has('id', '{node_id}').inE()"
        else:
            query = f"g.V().has('id', '{node_id}').bothE()"

        if edge_type:
            query += f".hasLabel('{edge_type}')"

        query += ".valueMap(true).toList()"
        results = self._execute(query)

        edges = []
        for r in results:
            edges.append(
                GraphEdge(
                    edge_id=r.get("id", [""])[0],
                    source_id="",  # 別クエリで取得が必要
                    target_id="",
                    edge_type=r.get("label", [""])[0],
                    properties=r,
                )
            )
        return edges

    def delete_edge(
        self,
        edge_id: str,
    ) -> bool:
        """エッジ削除"""
        query = f"g.E().has('id', '{edge_id}').drop()"
        self._execute(query)
        return True

    def query(
        self,
        query_string: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Gremlin クエリ実行"""
        results = self._execute(query_string, parameters)
        return [dict(r) if hasattr(r, "items") else {"value": r} for r in results]

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> list[GraphNode] | None:
        """最短パス検索"""
        query = f"""
            g.V().has('id', '{source_id}')
             .repeat(both().simplePath())
             .until(has('id', '{target_id}'))
             .path()
             .limit(1)
        """
        results = self._execute(query)

        if results:
            path = results[0]
            return [
                GraphNode(
                    node_id=str(v),
                    node_type="Unknown",
                    properties={},
                )
                for v in path
            ]
        return None

    def get_neighbors(
        self,
        node_id: str,
        depth: int = 1,
        edge_types: list[str] | None = None,
    ) -> list[GraphNode]:
        """隣接ノード取得"""
        edge_filter = ""
        if edge_types:
            edge_filter = ",".join([f"'{t}'" for t in edge_types])
            edge_filter = f".hasLabel({edge_filter})"

        query = f"""
            g.V().has('id', '{node_id}')
             .repeat(bothE(){edge_filter}.otherV().simplePath())
             .times({depth})
             .dedup()
             .valueMap(true)
        """
        results = self._execute(query)

        nodes = []
        for r in results:
            nodes.append(
                GraphNode(
                    node_id=r.get("id", [""])[0],
                    node_type=r.get("label", ["Unknown"])[0],
                    properties=r,
                )
            )
        return nodes

    def close(self) -> None:
        """接続クローズ"""
        if self._gremlin_client:
            self._gremlin_client.close()

