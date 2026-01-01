"""
Vector API Lambda Handler

S3 Vectors / Bedrock Knowledge Base へのアクセス API
"""

import json
import logging
import os
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
DATA_SOURCE_BUCKET = os.environ.get("DATA_SOURCE_BUCKET", "")


def get_s3vectors_client():
    """S3 Vectors クライアントを取得"""
    if ENVIRONMENT == "local":
        return boto3.client(
            "s3vectors",
            endpoint_url=os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566"),
            region_name="us-west-2",
        )
    return boto3.client("s3vectors", region_name="us-west-2")


def get_bedrock_runtime_client():
    """Bedrock Runtime クライアントを取得"""
    if ENVIRONMENT == "local":
        return boto3.client(
            "bedrock-runtime",
            endpoint_url=os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566"),
            region_name="us-west-2",
        )
    return boto3.client("bedrock-runtime", region_name="us-west-2")


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Lambda ハンドラー

    エンドポイント:
    - POST /v1/vectors: ベクトル挿入
    - GET /v1/vectors: ベクトル一覧
    - POST /v1/vectors/query: ベクトル検索
    """
    logger.info(f"Event: {json.dumps(event)}")

    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "")
    query_params = event.get("queryStringParameters") or {}
    body = json.loads(event.get("body") or "{}")

    try:
        if http_method == "POST" and path == "/v1/vectors":
            return put_vectors(body)
        elif http_method == "GET" and path == "/v1/vectors":
            return list_vectors(query_params)
        elif http_method == "POST" and path == "/v1/vectors/query":
            return query_vectors(body)
        else:
            return response(404, {"error": "Not Found"})
    except Exception as e:
        logger.exception("Error processing request")
        return response(500, {"error": str(e)})


def generate_embedding(text: str) -> list[float]:
    """テキストから埋め込みベクトルを生成"""
    client = get_bedrock_runtime_client()

    try:
        response = client.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": text}),
        )

        result = json.loads(response["body"].read())
        return result["embedding"]
    except Exception as e:
        logger.warning(f"Failed to generate embedding: {e}")
        # フォールバック: ダミーベクトル
        return [0.0] * 1024


def put_vectors(body: dict) -> dict:
    """ベクトル挿入"""
    client = get_s3vectors_client()

    index_name = body.get("index_name")
    vectors = body.get("vectors", [])

    if not index_name:
        return response(400, {"error": "index_name is required"})
    if not vectors:
        return response(400, {"error": "vectors is required"})

    try:
        # テキストから埋め込みを生成
        vector_records = []
        for v in vectors:
            if "text" in v and "vector" not in v:
                embedding = generate_embedding(v["text"])
                v["vector"] = embedding

            vector_records.append(
                {
                    "key": v["key"],
                    "data": {"float32": v["vector"]},
                    "metadata": v.get("metadata", {}),
                }
            )

        client.put_vectors(
            vectorBucketName=os.environ.get("VECTOR_BUCKET_NAME", ""),
            indexName=index_name,
            vectors=vector_records,
        )

        return response(201, {"message": f"Inserted {len(vectors)} vectors"})
    except Exception as e:
        logger.exception("Failed to put vectors")
        return response(500, {"error": str(e)})


def list_vectors(query_params: dict) -> dict:
    """ベクトル一覧"""
    client = get_s3vectors_client()

    index_name = query_params.get("index_name")
    if not index_name:
        return response(400, {"error": "index_name is required"})

    try:
        result = client.list_vectors(
            vectorBucketName=os.environ.get("VECTOR_BUCKET_NAME", ""),
            indexName=index_name,
            maxResults=int(query_params.get("limit", "100")),
        )

        return response(
            200,
            {
                "vectors": [
                    {"key": v["key"], "metadata": v.get("metadata", {})}
                    for v in result.get("vectors", [])
                ]
            },
        )
    except Exception as e:
        logger.exception("Failed to list vectors")
        return response(500, {"error": str(e)})


def query_vectors(body: dict) -> dict:
    """ベクトル検索"""
    client = get_s3vectors_client()

    index_name = body.get("index_name")
    query = body.get("query")
    query_vector = body.get("query_vector")
    top_k = body.get("top_k", 10)
    filters = body.get("filter")

    if not index_name:
        return response(400, {"error": "index_name is required"})
    if not query and not query_vector:
        return response(400, {"error": "query or query_vector is required"})

    try:
        # テキストクエリの場合は埋め込みを生成
        if query and not query_vector:
            query_vector = generate_embedding(query)

        result = client.query_vectors(
            vectorBucketName=os.environ.get("VECTOR_BUCKET_NAME", ""),
            indexName=index_name,
            queryVector={"float32": query_vector},
            topK=top_k,
            filter=filters,
            returnMetadata=True,
        )

        return response(
            200,
            {
                "results": [
                    {
                        "key": v["key"],
                        "score": v.get("score", 0),
                        "metadata": v.get("metadata", {}),
                    }
                    for v in result.get("vectors", [])
                ]
            },
        )
    except Exception as e:
        logger.exception("Failed to query vectors")
        return response(500, {"error": str(e)})


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

