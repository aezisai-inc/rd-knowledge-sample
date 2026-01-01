"""
Graph API Lambda Handler

Neo4j AuraDB / Local Neo4j 対応のグラフ API。
Secrets Manager から接続情報を取得。
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Secrets Manager から Neo4j 接続情報を取得
_neo4j_config: dict[str, str] | None = None


def get_neo4j_config() -> dict[str, str]:
    """Neo4j 接続情報を取得（キャッシュ付き）"""
    global _neo4j_config

    if _neo4j_config is not None:
        return _neo4j_config

    secret_arn = os.environ.get("NEO4J_SECRET_ARN")

    if secret_arn:
        try:
            secrets_client = boto3.client("secretsmanager")
            response = secrets_client.get_secret_value(SecretId=secret_arn)
            _neo4j_config = json.loads(response["SecretString"])
            logger.info(f"Neo4j config loaded from Secrets Manager")
        except Exception as e:
            logger.error(f"Failed to get Neo4j secret: {e}")
            _neo4j_config = {
                "uri": "bolt://localhost:7687",
                "user": "neo4j",
                "password": "password",
                "database": "neo4j",
            }
    else:
        # ローカル開発用のデフォルト
        _neo4j_config = {
            "uri": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            "user": os.environ.get("NEO4J_USER", "neo4j"),
            "password": os.environ.get("NEO4J_PASSWORD", "password"),
            "database": os.environ.get("NEO4J_DATABASE", "neo4j"),
        }

    return _neo4j_config


class Neo4jClient:
    """Neo4j クライアント（Lambda 用）"""

    def __init__(self):
        config = get_neo4j_config()
        self.uri = config["uri"]
        self.user = config["user"]
        self.password = config["password"]
        self.database = config.get("database", "neo4j")
        self._driver = None

    def connect(self):
        """接続"""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase

                self._driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                )
                logger.info(f"Connected to Neo4j")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise

    def execute(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict]:
        """Cypher クエリ実行"""
        self.connect()

        with self._driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def close(self):
        """接続クローズ"""
        if self._driver:
            self._driver.close()
            self._driver = None


# グローバルクライアント（Lambda コンテナ再利用のため）
_client: Neo4jClient | None = None


def get_client() -> Neo4jClient:
    """クライアント取得"""
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client


def lambda_handler(event: dict, context: Any) -> dict:
    """Lambda ハンドラ"""
    logger.info(f"Event: {json.dumps(event)}")

    try:
        http_method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        path_params = event.get("pathParameters") or {}
        query_params = event.get("queryStringParameters") or {}
        body = json.loads(event.get("body") or "{}")

        client = get_client()

        # ルーティング
        if path.endswith("/nodes") and http_method == "POST":
            # ノード作成
            result = create_node(client, body)
        elif path.endswith("/nodes") and http_method == "GET":
            # ノード一覧
            result = list_nodes(client, query_params)
        elif "/nodes/" in path and http_method == "GET":
            # ノード取得
            node_id = path_params.get("nodeId")
            result = get_node(client, node_id)
        elif "/nodes/" in path and http_method == "PUT":
            # ノード更新
            node_id = path_params.get("nodeId")
            result = update_node(client, node_id, body)
        elif "/nodes/" in path and http_method == "DELETE":
            # ノード削除
            node_id = path_params.get("nodeId")
            result = delete_node(client, node_id)
        elif path.endswith("/edges") and http_method == "POST":
            # エッジ作成
            result = create_edge(client, body)
        elif path.endswith("/query") and http_method == "POST":
            # Cypher クエリ実行
            result = execute_query(client, body)
        else:
            return response(404, {"error": "Not Found"})

        return response(200, result)

    except Exception as e:
        logger.exception(f"Error: {e}")
        return response(500, {"error": str(e)})


def create_node(client: Neo4jClient, body: dict) -> dict:
    """ノード作成"""
    node_id = body.get("id") or f"node-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    node_type = body.get("type", "Entity")
    properties = body.get("properties", {})

    props = {"id": node_id, **properties}

    client.execute(
        f"CREATE (n:{node_type} $props) RETURN n",
        {"props": props},
    )

    return {"id": node_id, "type": node_type, "properties": properties}


def list_nodes(client: Neo4jClient, params: dict) -> dict:
    """ノード一覧"""
    node_type = params.get("type")
    limit = int(params.get("limit", 100))

    if node_type:
        results = client.execute(
            f"MATCH (n:{node_type}) RETURN n, labels(n) as labels LIMIT $limit",
            {"limit": limit},
        )
    else:
        results = client.execute(
            "MATCH (n) RETURN n, labels(n) as labels LIMIT $limit",
            {"limit": limit},
        )

    nodes = []
    for record in results:
        node_data = dict(record["n"])
        node_id = node_data.pop("id", "")
        labels = record["labels"]

        nodes.append({
            "id": node_id,
            "type": labels[0] if labels else "",
            "properties": node_data,
        })

    return {"nodes": nodes, "count": len(nodes)}


def get_node(client: Neo4jClient, node_id: str) -> dict:
    """ノード取得"""
    results = client.execute(
        "MATCH (n {id: $id}) RETURN n, labels(n) as labels",
        {"id": node_id},
    )

    if not results:
        return {"error": "Node not found"}

    record = results[0]
    node_data = dict(record["n"])
    node_data.pop("id", None)
    labels = record["labels"]

    return {
        "id": node_id,
        "type": labels[0] if labels else "",
        "properties": node_data,
    }


def update_node(client: Neo4jClient, node_id: str, body: dict) -> dict:
    """ノード更新"""
    properties = body.get("properties", {})

    results = client.execute(
        "MATCH (n {id: $id}) SET n += $props RETURN n",
        {"id": node_id, "props": properties},
    )

    if not results:
        return {"error": "Node not found"}

    return {"id": node_id, "updated": True}


def delete_node(client: Neo4jClient, node_id: str) -> dict:
    """ノード削除"""
    results = client.execute(
        "MATCH (n {id: $id}) DETACH DELETE n RETURN count(n) as deleted",
        {"id": node_id},
    )

    deleted = results[0]["deleted"] if results else 0
    return {"id": node_id, "deleted": deleted > 0}


def create_edge(client: Neo4jClient, body: dict) -> dict:
    """エッジ作成"""
    source_id = body.get("sourceId")
    target_id = body.get("targetId")
    edge_type = body.get("type", "RELATED_TO")
    properties = body.get("properties", {})

    edge_id = f"edge-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    props = {"id": edge_id, **properties}

    client.execute(
        f"""
        MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
        CREATE (a)-[r:{edge_type} $props]->(b)
        RETURN r
        """,
        {"source_id": source_id, "target_id": target_id, "props": props},
    )

    return {
        "id": edge_id,
        "sourceId": source_id,
        "targetId": target_id,
        "type": edge_type,
    }


def execute_query(client: Neo4jClient, body: dict) -> dict:
    """Cypher クエリ実行"""
    query = body.get("query", "")
    parameters = body.get("parameters", {})

    if not query:
        return {"error": "Query is required"}

    # 危険なクエリをブロック（本番では更に厳密に）
    dangerous_keywords = ["DELETE", "DROP", "REMOVE"]
    if any(keyword in query.upper() for keyword in dangerous_keywords):
        return {"error": "Destructive queries are not allowed via this endpoint"}

    results = client.execute(query, parameters)

    return {"results": results, "count": len(results)}


def response(status_code: int, body: dict) -> dict:
    """API Gateway レスポンス"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }
