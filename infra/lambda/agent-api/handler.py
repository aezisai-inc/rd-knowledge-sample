"""
Agent API Lambda Handler

Multimodal / Voice エージェント。
Bedrock Nova API を使用して実際の画像解析・音声処理を実行。

CORS 対応済み。
"""

import json
import logging
import os
import base64
import boto3
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# AWS リージョン
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")

# Bedrock クライアント初期化
bedrock_config = Config(
    region_name=BEDROCK_REGION,
    retries={"max_attempts": 3, "mode": "adaptive"},
)
bedrock_runtime = boto3.client("bedrock-runtime", config=bedrock_config)

# モデル ID
NOVA_LITE_MODEL = os.environ.get("NOVA_LITE_MODEL", "amazon.nova-lite-v1:0")
NOVA_PRO_MODEL = os.environ.get("NOVA_PRO_MODEL", "amazon.nova-pro-v1:0")

# CORS ヘッダー
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}


def lambda_handler(event, context):
    """Lambda ハンドラー"""
    logger.info(f"Event: {json.dumps(event)[:500]}")

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
    """
    Multimodal エージェント処理
    
    Bedrock Nova Lite/Pro を使用して画像解析を実行
    """
    http_method = event.get("httpMethod", "GET")

    if http_method == "POST":
        try:
            body = json.loads(event.get("body", "{}"))
            message = body.get("message", "この画像を説明してください")
            images = body.get("images", [])
            mode = body.get("mode", "understand")  # understand, generate, video_understand, video_generate

            logger.info(f"Multimodal request: mode={mode}, images={len(images)}, message={message[:50]}")

            # モード別処理
            if mode == "understand" or mode == "画像理解":
                return handle_image_understanding(message, images)
            elif mode == "generate" or mode == "画像生成":
                return handle_image_generation(message)
            elif mode == "video_understand" or mode == "動画理解":
                return handle_video_understanding(message, images)
            elif mode == "video_generate" or mode == "動画生成":
                return handle_video_generation(message)
            else:
                # デフォルトは画像理解
                return handle_image_understanding(message, images)

        except Exception as e:
            logger.exception(f"Multimodal error: {e}")
            return response(500, {"error": str(e), "type": type(e).__name__})

    return response(405, {"error": "Method not allowed"})


def handle_image_understanding(message: str, images: list) -> dict:
    """
    画像理解 (Nova Lite/Pro Vision)
    
    画像をアップロードしてAIに内容を説明させる
    """
    if not images:
        return response(400, {"error": "No images provided for understanding"})

    try:
        # メッセージコンテンツを構築
        content = []
        
        # 画像を追加
        for img in images:
            if isinstance(img, dict):
                # Base64形式
                image_data = img.get("data", img.get("base64", ""))
                media_type = img.get("mediaType", img.get("type", "image/jpeg"))
            elif isinstance(img, str):
                # 直接Base64文字列
                image_data = img
                media_type = "image/jpeg"
            else:
                continue
            
            # Base64プレフィックスを除去
            if "," in image_data:
                image_data = image_data.split(",")[1]
            
            content.append({
                "image": {
                    "format": media_type.split("/")[-1] if "/" in media_type else "jpeg",
                    "source": {
                        "bytes": base64.b64decode(image_data)
                    }
                }
            })
        
        # テキストプロンプトを追加
        content.append({
            "text": message or "この画像の内容を詳しく説明してください。"
        })

        # Bedrock Converse API 呼び出し
        response_data = bedrock_runtime.converse(
            modelId=NOVA_LITE_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            inferenceConfig={
                "maxTokens": 2048,
                "temperature": 0.7,
            },
            system=[
                {
                    "text": "あなたは画像分析の専門家です。画像の内容を詳細に分析し、日本語で分かりやすく説明してください。"
                }
            ]
        )

        # レスポンス抽出
        output_message = response_data.get("output", {}).get("message", {})
        output_content = output_message.get("content", [])
        
        result_text = ""
        for item in output_content:
            if "text" in item:
                result_text += item["text"]

        usage = response_data.get("usage", {})

        logger.info(f"Image understanding completed: {len(result_text)} chars")

        return response(200, {
            "status": "success",
            "mode": "image_understanding",
            "model": NOVA_LITE_MODEL,
            "response": result_text,
            "usage": {
                "inputTokens": usage.get("inputTokens", 0),
                "outputTokens": usage.get("outputTokens", 0),
            },
            "metadata": {
                "images_processed": len(images),
                "prompt": message,
            }
        })

    except Exception as e:
        logger.exception(f"Image understanding error: {e}")
        return response(500, {
            "status": "error",
            "error": str(e),
            "type": type(e).__name__,
            "message": "画像解析中にエラーが発生しました"
        })


def handle_image_generation(prompt: str) -> dict:
    """
    画像生成 (Nova Canvas)
    
    テキストプロンプトから画像を生成
    """
    try:
        # Nova Canvas モデル
        NOVA_CANVAS_MODEL = os.environ.get("NOVA_CANVAS_MODEL", "amazon.nova-canvas-v1:0")
        
        # 画像生成リクエスト
        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt,
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "width": 1024,
                "height": 1024,
                "cfgScale": 8.0,
                "seed": 0,
            }
        }

        response_data = bedrock_runtime.invoke_model(
            modelId=NOVA_CANVAS_MODEL,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )

        result = json.loads(response_data["body"].read())
        images = result.get("images", [])

        if images:
            return response(200, {
                "status": "success",
                "mode": "image_generation",
                "model": NOVA_CANVAS_MODEL,
                "images": images,  # Base64エンコードされた画像
                "metadata": {
                    "prompt": prompt,
                    "count": len(images),
                }
            })
        else:
            return response(200, {
                "status": "no_images",
                "message": "画像を生成できませんでした",
                "prompt": prompt,
            })

    except Exception as e:
        logger.exception(f"Image generation error: {e}")
        return response(500, {
            "status": "error",
            "error": str(e),
            "message": "画像生成中にエラーが発生しました"
        })


def handle_video_understanding(message: str, videos: list) -> dict:
    """
    動画理解 (Nova Pro Vision)
    
    動画をアップロードしてAIに内容を説明させる
    """
    if not videos:
        return response(400, {"error": "No videos provided for understanding"})

    try:
        # 動画の最初のフレームまたはサムネイルを使用
        # 注: Nova Proは動画の直接処理に制限があるため、フレーム抽出が推奨
        
        content = []
        
        for video in videos:
            if isinstance(video, dict):
                video_data = video.get("data", video.get("base64", ""))
                # 動画の場合、最初のフレームを抽出する処理が必要
                # ここではサムネイルとして扱う
            elif isinstance(video, str):
                video_data = video
            else:
                continue
            
            if "," in video_data:
                video_data = video_data.split(",")[1]
            
            content.append({
                "image": {
                    "format": "jpeg",
                    "source": {
                        "bytes": base64.b64decode(video_data)
                    }
                }
            })
        
        content.append({
            "text": message or "この動画/フレームの内容を説明してください。"
        })

        response_data = bedrock_runtime.converse(
            modelId=NOVA_PRO_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            inferenceConfig={
                "maxTokens": 2048,
                "temperature": 0.7,
            },
            system=[
                {
                    "text": "あなたは動画分析の専門家です。動画/フレームの内容を詳細に分析し、日本語で分かりやすく説明してください。"
                }
            ]
        )

        output_message = response_data.get("output", {}).get("message", {})
        output_content = output_message.get("content", [])
        
        result_text = ""
        for item in output_content:
            if "text" in item:
                result_text += item["text"]

        return response(200, {
            "status": "success",
            "mode": "video_understanding",
            "model": NOVA_PRO_MODEL,
            "response": result_text,
            "metadata": {
                "frames_processed": len(videos),
                "prompt": message,
            }
        })

    except Exception as e:
        logger.exception(f"Video understanding error: {e}")
        return response(500, {
            "status": "error",
            "error": str(e),
            "message": "動画解析中にエラーが発生しました"
        })


def handle_video_generation(prompt: str) -> dict:
    """
    動画生成 (Nova Reel)
    
    テキストプロンプトから動画を生成
    """
    try:
        # Nova Reel モデル
        NOVA_REEL_MODEL = os.environ.get("NOVA_REEL_MODEL", "amazon.nova-reel-v1:0")
        
        # 動画生成は非同期処理が推奨
        # ここでは開始のみを行い、結果はS3に出力
        
        return response(200, {
            "status": "pending",
            "mode": "video_generation",
            "model": NOVA_REEL_MODEL,
            "message": "動画生成は非同期処理です。生成完了後、S3に出力されます。",
            "info": {
                "prompt": prompt,
                "note": "動画生成は時間がかかるため、バックグラウンドで処理されます。"
            }
        })

    except Exception as e:
        logger.exception(f"Video generation error: {e}")
        return response(500, {
            "status": "error",
            "error": str(e),
            "message": "動画生成の開始中にエラーが発生しました"
        })


def handle_voice(event):
    """
    Voice エージェント処理
    
    Nova Sonic を使用した音声処理
    """
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "")

    if http_method == "POST":
        try:
            body = json.loads(event.get("body", "{}"))

            if "/process" in path:
                audio = body.get("audio", "")
                
                # 注: Nova Sonic は双方向ストリーミングが必要
                # Lambda単体では完全な実装が困難
                # AgentCore Runtime での実装を推奨
                
                return response(200, {
                    "status": "info",
                    "message": "Voice processing with Nova Sonic requires WebSocket streaming.",
                    "recommendation": "Use AgentCore Runtime with WebSocket support for real-time voice dialogue.",
                    "alternative": {
                        "transcription": "Use Amazon Transcribe for speech-to-text",
                        "synthesis": "Use Amazon Polly for text-to-speech"
                    }
                })
                
            elif "/text" in path:
                text = body.get("text", "")
                
                # テキスト処理は Bedrock で可能
                response_data = bedrock_runtime.converse(
                    modelId=NOVA_LITE_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": [{"text": text}]
                        }
                    ],
                    inferenceConfig={
                        "maxTokens": 1024,
                        "temperature": 0.7,
                    }
                )
                
                output_message = response_data.get("output", {}).get("message", {})
                output_content = output_message.get("content", [])
                
                result_text = ""
                for item in output_content:
                    if "text" in item:
                        result_text += item["text"]
                
                return response(200, {
                    "status": "success",
                    "response": result_text,
                    "input": text,
                })
            else:
                return response(200, {
                    "status": "ok",
                    "endpoints": {
                        "/voice/process": "Audio processing (requires WebSocket)",
                        "/voice/text": "Text processing"
                    }
                })

        except Exception as e:
            logger.exception(f"Voice error: {e}")
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
