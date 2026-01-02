"""
Image Generation Tool using Nova Canvas

StrandsAgents Tool として Nova Canvas を呼び出す。

注意:
- この Tool は StrandsAgents の @tool デコレータを使用
- エージェントが自動的にツール呼び出しを判断
- 直接 boto3 を使用するのは Tool 内部のみ（原則に基づく）
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

from strands.tool import tool

logger = logging.getLogger(__name__)


@tool
def image_generate(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    num_images: int = 1,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    Nova Canvas を使用して画像を生成します。

    テキストの説明から高品質な画像を生成できます。
    風景、人物、抽象的なコンセプトなど、様々な画像を生成可能です。

    Args:
        prompt: 生成する画像の説明（詳細であるほど良い結果が得られます）
        negative_prompt: 生成から除外したい要素（例: "低品質, ぼやけた"）
        width: 画像の幅（ピクセル、最大4096）
        height: 画像の高さ（ピクセル、最大4096）
        num_images: 生成する画像の数（1-4）
        seed: 再現性のためのシード値（同じシードで同じ画像を再生成）

    Returns:
        dict: {
            "images": [{"base64": "...", "s3_uri": "..."}],
            "model": "amazon.nova-canvas-v1:0",
            "success": True
        }

    Raises:
        Exception: Bedrock API 呼び出しエラー

    Example:
        >>> result = image_generate(
        ...     prompt="富士山と桜の美しい風景、朝日が昇る",
        ...     negative_prompt="低品質",
        ...     width=1024,
        ...     height=768,
        ... )
        >>> print(len(result["images"]))
        1
    """
    import boto3

    region = os.environ.get("AWS_REGION", "ap-northeast-1")
    output_bucket = os.environ.get("OUTPUT_BUCKET", "rd-knowledge-multimodal-output")

    logger.info(f"Generating image: prompt='{prompt[:50]}...', size={width}x{height}")

    try:
        bedrock = boto3.client("bedrock-runtime", region_name=region)

        # リクエストボディの構築
        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt,
            },
            "imageGenerationConfig": {
                "width": width,
                "height": height,
                "numberOfImages": min(num_images, 4),  # 最大4枚
            },
        }

        if negative_prompt:
            request_body["textToImageParams"]["negativeText"] = negative_prompt

        if seed is not None:
            request_body["imageGenerationConfig"]["seed"] = seed

        # Bedrock API 呼び出し
        response = bedrock.invoke_model(
            modelId="amazon.nova-canvas-v1:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )

        result = json.loads(response["body"].read())
        images = result.get("images", [])

        # S3 への保存（オプション）
        saved_images = []
        s3_client = boto3.client("s3", region_name=region)

        for i, img_base64 in enumerate(images):
            from datetime import datetime

            image_key = f"generated/images/{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}.png"

            try:
                s3_client.put_object(
                    Bucket=output_bucket,
                    Key=image_key,
                    Body=base64.b64decode(img_base64),
                    ContentType="image/png",
                )
                s3_uri = f"s3://{output_bucket}/{image_key}"
                logger.info(f"Image saved to: {s3_uri}")
            except Exception as e:
                logger.warning(f"Failed to save image to S3: {e}")
                s3_uri = None

            saved_images.append({
                "base64": img_base64,
                "s3_uri": s3_uri,
            })

        logger.info(f"Generated {len(saved_images)} image(s)")

        return {
            "images": saved_images,
            "model": "amazon.nova-canvas-v1:0",
            "success": True,
        }

    except Exception as e:
        logger.exception(f"Image generation failed: {e}")
        return {
            "images": [],
            "model": "amazon.nova-canvas-v1:0",
            "success": False,
            "error": str(e),
        }

