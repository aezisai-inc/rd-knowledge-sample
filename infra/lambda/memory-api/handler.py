"""
Memory API Lambda Handler

AgentCore Memory / ローカルメモリストアへのアクセス API
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")


def get_memory_client():
    """環境に応じたメモリクライアントを取得"""
    if ENVIRONMENT == "local":
        # ローカル環境では LocalStack を使用
        return boto3.client(
            "bedrock-agentcore",
            endpoint_url=os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566"),
            region_name="us-east-1",
        )
    return boto3.client("bedrock-agentcore", region_name="us-east-1")


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Lambda ハンドラー

    エンドポイント:
    - POST /v1/memory: イベント作成
    - GET /v1/memory: メモリレコード検索
    - GET /v1/memory/{actorId}: セッション履歴取得
    - DELETE /v1/memory/{actorId}: アクターメモリ削除
    """
    logger.info(f"Event: {json.dumps(event)}")

    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    body = json.loads(event.get("body") or "{}")

    try:
        if http_method == "POST" and path == "/v1/memory":
            return create_event(body)
        elif http_method == "GET" and path == "/v1/memory":
            return retrieve_records(query_params)
        elif http_method == "GET" and "actorId" in path_params:
            return get_session_history(path_params["actorId"], query_params)
        elif http_method == "DELETE" and "actorId" in path_params:
            return delete_actor_memory(path_params["actorId"])
        else:
            return response(404, {"error": "Not Found"})
    except Exception as e:
        logger.exception("Error processing request")
        return response(500, {"error": str(e)})


def create_event(body: dict) -> dict:
    """イベント作成"""
    client = get_memory_client()
    memory_id = os.environ.get("MEMORY_ID")

    if not memory_id:
        return response(400, {"error": "MEMORY_ID not configured"})

    events = body.get("events", [])
    if not events:
        return response(400, {"error": "events is required"})

    try:
        for event_data in events:
            client.create_event(
                memoryId=memory_id,
                actorId=event_data["actor_id"],
                sessionId=event_data["session_id"],
                eventTimestamp=datetime.fromisoformat(
                    event_data.get("timestamp", datetime.now().isoformat())
                ),
                payload=[
                    {
                        "conversational": {
                            "role": event_data["role"],
                            "content": {"text": event_data["content"]},
                        }
                    }
                ],
            )

        return response(201, {"message": f"Created {len(events)} events"})
    except Exception as e:
        logger.exception("Failed to create event")
        return response(500, {"error": str(e)})


def retrieve_records(query_params: dict) -> dict:
    """メモリレコード検索"""
    client = get_memory_client()
    memory_id = os.environ.get("MEMORY_ID")

    if not memory_id:
        return response(400, {"error": "MEMORY_ID not configured"})

    actor_id = query_params.get("actor_id")
    query = query_params.get("query", "")
    limit = int(query_params.get("limit", "10"))

    if not actor_id:
        return response(400, {"error": "actor_id is required"})

    try:
        result = client.retrieve_memory_records(
            memoryId=memory_id,
            actorId=actor_id,
            query=query,
            maxResults=limit,
        )

        records = result.get("memoryRecords", [])
        return response(
            200,
            {
                "records": [
                    {
                        "id": r.get("recordId"),
                        "memory_type": r.get("memoryType"),
                        "content": r.get("content"),
                        "score": r.get("score"),
                    }
                    for r in records
                ]
            },
        )
    except Exception as e:
        logger.exception("Failed to retrieve records")
        return response(500, {"error": str(e)})


def get_session_history(actor_id: str, query_params: dict) -> dict:
    """セッション履歴取得"""
    client = get_memory_client()
    memory_id = os.environ.get("MEMORY_ID")

    if not memory_id:
        return response(400, {"error": "MEMORY_ID not configured"})

    session_id = query_params.get("session_id")
    limit = int(query_params.get("limit", "50"))

    if not session_id:
        return response(400, {"error": "session_id is required"})

    try:
        result = client.get_session_summary(
            memoryId=memory_id,
            actorId=actor_id,
            sessionId=session_id,
        )

        return response(
            200,
            {
                "actor_id": actor_id,
                "session_id": session_id,
                "summary": result.get("summary"),
                "events": result.get("events", [])[:limit],
            },
        )
    except Exception as e:
        logger.exception("Failed to get session history")
        return response(500, {"error": str(e)})


def delete_actor_memory(actor_id: str) -> dict:
    """アクターメモリ削除"""
    # Note: AgentCore Memory API に削除機能がない場合は Not Implemented を返す
    return response(501, {"error": "Delete not implemented in AgentCore Memory"})


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

