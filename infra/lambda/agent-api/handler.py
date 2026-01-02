"""
Agent API Lambda Handler (Placeholder)

Multimodal / Voice エージェントのプレースホルダ。
本番環境では AgentCore Runtime を使用。

CORS 対応済み。
"""

import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# CORS ヘッダー
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}


def lambda_handler(event, context):
    """Lambda ハンドラー"""
    logger.info(f"Event: {json.dumps(event)}")

    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "")

    # OPTIONS (CORS preflight)
    if http_method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": "",
        }

    # パスに基づいて処理
    if "/multimodal" in path:
        return handle_multimodal(event)
    elif "/voice" in path:
        return handle_voice(event)
    else:
        return response(404, {"error": "Not found"})


def handle_multimodal(event):
    """Multimodal エージェント処理"""
    http_method = event.get("httpMethod", "GET")

    if http_method == "POST":
        try:
            body = json.loads(event.get("body", "{}"))
            message = body.get("message", "")
            images = body.get("images", [])

            # プレースホルダレスポンス
            # 本番では AgentCore Runtime で処理
            return response(200, {
                "status": "placeholder",
                "message": "Multimodal Agent is designed for AgentCore Runtime deployment.",
                "info": {
                    "deployment_guide": "/docs/AGENTCORE_DEPLOYMENT.md",
                    "commands": {
                        "local_dev": "agentcore dev",
                        "deploy": "agentcore launch",
                    },
                },
                "received": {
                    "message": message,
                    "images_count": len(images),
                },
                "mock_response": f"Received message: '{message}' with {len(images)} image(s). "
                                 f"Deploy to AgentCore Runtime for full functionality."
            })
        except Exception as e:
            logger.exception(f"Error: {e}")
            return response(500, {"error": str(e)})

    return response(405, {"error": "Method not allowed"})


def handle_voice(event):
    """Voice エージェント処理"""
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "")

    if http_method == "POST":
        try:
            body = json.loads(event.get("body", "{}"))

            if "/process" in path:
                # 音声処理
                audio = body.get("audio", "")
                return response(200, {
                    "status": "placeholder",
                    "message": "Voice Agent requires AgentCore Runtime with Nova Sonic.",
                    "info": {
                        "model": "amazon.nova-2-sonic-v1:0",
                        "features": ["speech-to-speech", "bidirectional-streaming"],
                    },
                    "mock_response": {
                        "transcript": "This is a placeholder response.",
                        "user_text": "Sample user input",
                        "assistant_text": "Voice dialogue requires AgentCore Runtime deployment.",
                    }
                })
            elif "/text" in path:
                # テキスト処理
                text = body.get("text", "")
                return response(200, {
                    "status": "placeholder",
                    "message": "Voice Agent placeholder response.",
                    "received_text": text,
                    "response": f"Echo: {text} (Deploy to AgentCore for real voice synthesis)",
                })
            else:
                return response(200, {
                    "status": "placeholder",
                    "message": "Voice Agent endpoint",
                })

        except Exception as e:
            logger.exception(f"Error: {e}")
            return response(500, {"error": str(e)})

    return response(405, {"error": "Method not allowed"})


def response(status_code: int, body: dict) -> dict:
    """レスポンス生成"""
    return {
        "statusCode": status_code,
        "headers": {
            **CORS_HEADERS,
            "Content-Type": "application/json",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }

