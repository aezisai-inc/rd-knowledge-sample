"""
Graph API Lambda Handler

Neptune Serverless へのアクセス API
"""

import json
import logging
import os
from typing import Any

from gremlin_python.driver import client, serializer
from gremlin_python.driver.protocol import GremlinServerError

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
NEPTUNE_ENDPOINT = os.environ.get("NEPTUNE_ENDPOINT", "localhost:8182")


def get_gremlin_client():
    """Gremlin クライアントを取得"""
    endpoint = f"wss://{NEPTUNE_ENDPOINT}/gremlin"
    if ENVIRONMENT == "local":
        # ローカル環境では Neo4j Bolt を使用 (別途アダプタが必要)
        endpoint = f"ws://{NEPTUNE_ENDPOINT}/gremlin"

    return client.Client(
        endpoint,
        "g",
        message_serializer=serializer.GraphSONSerializersV2d0(),
    )


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Lambda ハンドラー

    エンドポイント:
    - POST /v1/graph/nodes: ノード作成
    - GET /v1/graph/nodes: ノード一覧
    - GET /v1/graph/nodes/{nodeId}: ノード取得
    - PUT /v1/graph/nodes/{nodeId}: ノード更新
    - DELETE /v1/graph/nodes/{nodeId}: ノード削除
    - POST /v1/graph/edges: エッジ作成
    - POST /v1/graph/query: Gremlin クエリ実行
    """
    logger.info(f"Event: {json.dumps(event)}")

    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    body = json.loads(event.get("body") or "{}")

    try:
        # ノード操作
        if "/nodes" in path:
            if http_method == "POST" and path.endswith("/nodes"):
                return create_node(body)
            elif http_method == "GET" and path.endswith("/nodes"):
                return list_nodes(query_params)
            elif "nodeId" in path_params:
                node_id = path_params["nodeId"]
                if http_method == "GET":
                    return get_node(node_id)
                elif http_method == "PUT":
                    return update_node(node_id, body)
                elif http_method == "DELETE":
                    return delete_node(node_id)

        # エッジ操作
        elif "/edges" in path:
            if http_method == "POST":
                return create_edge(body)

        # クエリ実行
        elif "/query" in path:
            if http_method == "POST":
                return execute_query(body)

        return response(404, {"error": "Not Found"})
    except GremlinServerError as e:
        logger.exception("Gremlin error")
        return response(500, {"error": f"Graph database error: {str(e)}"})
    except Exception as e:
        logger.exception("Error processing request")
        return response(500, {"error": str(e)})


def create_node(body: dict) -> dict:
    """ノード作成"""
    node_id = body.get("node_id")
    node_type = body.get("node_type", "Entity")
    properties = body.get("properties", {})

    if not node_id:
        return response(400, {"error": "node_id is required"})

    gremlin = get_gremlin_client()
    try:
        # Gremlin クエリを構築
        query = f"g.addV('{node_type}').property('id', '{node_id}')"
        for key, value in properties.items():
            escaped_value = str(value).replace("'", "\\'")
            query += f".property('{key}', '{escaped_value}')"

        gremlin.submit(query).all().result()

        return response(201, {"node_id": node_id, "message": "Node created"})
    finally:
        gremlin.close()


def list_nodes(query_params: dict) -> dict:
    """ノード一覧"""
    node_type = query_params.get("type")
    limit = int(query_params.get("limit", "100"))

    gremlin = get_gremlin_client()
    try:
        if node_type:
            query = f"g.V().hasLabel('{node_type}').limit({limit}).valueMap(true)"
        else:
            query = f"g.V().limit({limit}).valueMap(true)"

        results = gremlin.submit(query).all().result()

        nodes = []
        for r in results:
            node = {"node_id": r.get("id", [None])[0], "node_type": r.get("label", "")}
            properties = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in r.items() if k not in ["id", "label"]}
            node["properties"] = properties
            nodes.append(node)

        return response(200, {"nodes": nodes})
    finally:
        gremlin.close()


def get_node(node_id: str) -> dict:
    """ノード取得"""
    gremlin = get_gremlin_client()
    try:
        query = f"g.V().has('id', '{node_id}').valueMap(true)"
        results = gremlin.submit(query).all().result()

        if not results:
            return response(404, {"error": "Node not found"})

        r = results[0]
        node = {
            "node_id": r.get("id", [None])[0],
            "node_type": r.get("label", ""),
            "properties": {
                k: v[0] if isinstance(v, list) and len(v) == 1 else v
                for k, v in r.items()
                if k not in ["id", "label"]
            },
        }

        return response(200, node)
    finally:
        gremlin.close()


def update_node(node_id: str, body: dict) -> dict:
    """ノード更新"""
    properties = body.get("properties", {})

    if not properties:
        return response(400, {"error": "properties is required"})

    gremlin = get_gremlin_client()
    try:
        # プロパティを更新
        query = f"g.V().has('id', '{node_id}')"
        for key, value in properties.items():
            escaped_value = str(value).replace("'", "\\'")
            query += f".property('{key}', '{escaped_value}')"

        results = gremlin.submit(query).all().result()

        if not results:
            return response(404, {"error": "Node not found"})

        return response(200, {"message": "Node updated"})
    finally:
        gremlin.close()


def delete_node(node_id: str) -> dict:
    """ノード削除"""
    gremlin = get_gremlin_client()
    try:
        query = f"g.V().has('id', '{node_id}').drop()"
        gremlin.submit(query).all().result()

        return response(200, {"message": "Node deleted"})
    finally:
        gremlin.close()


def create_edge(body: dict) -> dict:
    """エッジ作成"""
    source_id = body.get("source_id")
    target_id = body.get("target_id")
    edge_type = body.get("edge_type", "RELATES_TO")
    properties = body.get("properties", {})

    if not source_id or not target_id:
        return response(400, {"error": "source_id and target_id are required"})

    gremlin = get_gremlin_client()
    try:
        query = f"g.V().has('id', '{source_id}').addE('{edge_type}').to(g.V().has('id', '{target_id}'))"
        for key, value in properties.items():
            escaped_value = str(value).replace("'", "\\'")
            query += f".property('{key}', '{escaped_value}')"

        gremlin.submit(query).all().result()

        return response(
            201, {"message": "Edge created", "source_id": source_id, "target_id": target_id}
        )
    finally:
        gremlin.close()


def execute_query(body: dict) -> dict:
    """Gremlin クエリ実行"""
    query = body.get("query")

    if not query:
        return response(400, {"error": "query is required"})

    # セキュリティ: 危険なクエリを拒否
    dangerous_keywords = ["drop()", "clear()", "removeAll"]
    for keyword in dangerous_keywords:
        if keyword in query.lower():
            return response(400, {"error": f"Dangerous operation not allowed: {keyword}"})

    gremlin = get_gremlin_client()
    try:
        results = gremlin.submit(query).all().result()

        return response(200, {"results": results})
    finally:
        gremlin.close()


def response(status_code: int, body: dict) -> dict:
    """API Gateway 用レスポンス"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }

