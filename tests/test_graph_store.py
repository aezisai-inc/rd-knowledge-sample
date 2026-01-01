"""
GraphStore E2E テスト

ローカル環境と AWS 環境の両方で同一テストケースを実行。
"""

from __future__ import annotations

import pytest

from src.interfaces import GraphEdge, GraphNode


class TestGraphStore:
    """GraphStore Protocol の E2E テスト"""

    def test_create_node(self, graph_store, sample_graph_nodes):
        """ノード作成テスト"""
        node = sample_graph_nodes[0]
        result = graph_store.create_node(node)

        assert result is not None
        assert result == node.node_id

    def test_get_node(self, graph_store, sample_graph_nodes):
        """ノード取得テスト"""
        node = sample_graph_nodes[0]
        graph_store.create_node(node)

        # 取得
        result = graph_store.get_node(node.node_id)

        assert result is not None
        assert isinstance(result, GraphNode)
        assert result.node_id == node.node_id
        assert result.node_type == node.node_type
        assert result.properties["name"] == node.properties["name"]

    def test_update_node(self, graph_store, sample_graph_nodes):
        """ノード更新テスト"""
        node = sample_graph_nodes[0]
        graph_store.create_node(node)

        # 更新
        result = graph_store.update_node(
            node_id=node.node_id,
            properties={"name": "Alice Updated", "role": "admin"},
        )

        assert result is True

        # 更新後の値を確認
        updated_node = graph_store.get_node(node.node_id)
        assert updated_node.properties["name"] == "Alice Updated"
        assert updated_node.properties["role"] == "admin"

    def test_delete_node(self, graph_store, sample_graph_nodes):
        """ノード削除テスト"""
        node = sample_graph_nodes[0]
        graph_store.create_node(node)

        # 削除
        result = graph_store.delete_node(node.node_id)

        assert result is True

        # 削除後は取得できない
        deleted_node = graph_store.get_node(node.node_id)
        assert deleted_node is None

    def test_create_edge(self, graph_store, sample_graph_nodes, sample_graph_edges):
        """エッジ作成テスト"""
        # まずノードを作成
        for node in sample_graph_nodes:
            graph_store.create_node(node)

        # エッジ作成
        edge = sample_graph_edges[0]
        result = graph_store.create_edge(edge)

        assert result is not None
        assert result == edge.edge_id

    def test_get_edges(self, graph_store, sample_graph_nodes, sample_graph_edges):
        """エッジ取得テスト"""
        # ノードとエッジを作成
        for node in sample_graph_nodes:
            graph_store.create_node(node)
        for edge in sample_graph_edges:
            graph_store.create_edge(edge)

        # user-1 の出エッジを取得
        edges = graph_store.get_edges(
            node_id="user-1",
            direction="out",
        )

        assert len(edges) > 0
        assert all(isinstance(e, GraphEdge) for e in edges)
        assert all(e.source_id == "user-1" for e in edges)

    def test_get_edges_with_type_filter(self, graph_store, sample_graph_nodes, sample_graph_edges):
        """エッジタイプフィルタテスト"""
        # ノードとエッジを作成
        for node in sample_graph_nodes:
            graph_store.create_node(node)
        for edge in sample_graph_edges:
            graph_store.create_edge(edge)

        # OWNS タイプのみ取得
        edges = graph_store.get_edges(
            node_id="user-1",
            direction="out",
            edge_type="OWNS",
        )

        assert all(e.edge_type == "OWNS" for e in edges)

    def test_delete_edge(self, graph_store, sample_graph_nodes, sample_graph_edges):
        """エッジ削除テスト"""
        # ノードとエッジを作成
        for node in sample_graph_nodes:
            graph_store.create_node(node)
        edge = sample_graph_edges[0]
        graph_store.create_edge(edge)

        # 削除
        result = graph_store.delete_edge(edge.edge_id)

        assert result is True

    def test_find_path(self, graph_store, sample_graph_nodes, sample_graph_edges):
        """パス検索テスト"""
        # ノードとエッジを作成
        for node in sample_graph_nodes:
            graph_store.create_node(node)
        for edge in sample_graph_edges:
            graph_store.create_edge(edge)

        # user-1 から doc-1 へのパスを検索
        path = graph_store.find_path(
            source_id="user-1",
            target_id="doc-1",
            max_depth=5,
        )

        assert path is not None
        assert len(path) >= 2
        assert path[0].node_id == "user-1"
        assert path[-1].node_id == "doc-1"

    def test_get_neighbors(self, graph_store, sample_graph_nodes, sample_graph_edges):
        """隣接ノード取得テスト"""
        # ノードとエッジを作成
        for node in sample_graph_nodes:
            graph_store.create_node(node)
        for edge in sample_graph_edges:
            graph_store.create_edge(edge)

        # user-1 の隣接ノードを取得
        neighbors = graph_store.get_neighbors(
            node_id="user-1",
            depth=1,
        )

        assert len(neighbors) > 0
        neighbor_ids = [n.node_id for n in neighbors]
        # user-2 と doc-1 が隣接ノード
        assert "user-2" in neighbor_ids or "doc-1" in neighbor_ids

    def test_query(self, graph_store, sample_graph_nodes, is_local):
        """クエリ実行テスト"""
        # ノードを作成
        for node in sample_graph_nodes:
            graph_store.create_node(node)

        if is_local:
            # ローカル（NetworkX）では簡易クエリのみ
            results = graph_store.query("MATCH (n:User) RETURN n")
            assert len(results) > 0
        else:
            # AWS（Neptune）では Gremlin/Cypher クエリ
            results = graph_store.query(
                "g.V().hasLabel('User').values('name')",
                parameters={},
            )
            assert len(results) > 0

    def test_node_not_found(self, graph_store):
        """存在しないノード取得テスト"""
        result = graph_store.get_node("nonexistent-node")

        assert result is None

    def test_path_not_found(self, graph_store, sample_graph_nodes):
        """パスが存在しない場合のテスト"""
        # 接続されていないノードを作成
        node_a = GraphNode(node_id="isolated-a", node_type="Test", properties={})
        node_b = GraphNode(node_id="isolated-b", node_type="Test", properties={})

        graph_store.create_node(node_a)
        graph_store.create_node(node_b)

        # パスは存在しない
        path = graph_store.find_path(
            source_id="isolated-a",
            target_id="isolated-b",
            max_depth=5,
        )

        assert path is None
