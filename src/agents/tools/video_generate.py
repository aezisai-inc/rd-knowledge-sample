"""
Video Generation Tool using Nova Reel

StrandsAgents Tool として Nova Reel を呼び出す（非同期）。

注意:
- 動画生成は非同期処理のため、ジョブIDを返す
- 完了確認は別途 get_video_status で行う
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from strands.tool import tool

logger = logging.getLogger(__name__)


@tool
def video_generate(
    prompt: str,
    duration_seconds: int = 6,
    fps: int = 24,
    dimension: str = "1280x720",
    seed: int | None = None,
) -> dict[str, Any]:
    """
    Nova Reel を使用して動画を生成します（非同期処理）。

    テキストの説明から動画を生成できます。生成は非同期で行われるため、
    ジョブIDを使って後で完了状態を確認する必要があります。

    Args:
        prompt: 生成する動画の説明（詳細であるほど良い結果が得られます）
        duration_seconds: 動画の長さ（秒、最大6秒）
        fps: フレームレート（24が推奨）
        dimension: 動画サイズ（"1280x720" または "1920x1080"）
        seed: 再現性のためのシード値

    Returns:
        dict: {
            "job_id": "arn:aws:bedrock:...",
            "status": "IN_PROGRESS" | "FAILED",
            "status_url": "/v1/multimodal/status/...",
            "output_s3_uri": "s3://..."
        }

    Raises:
        Exception: Bedrock API 呼び出しエラー

    Example:
        >>> result = video_generate(
        ...     prompt="海辺で波が静かに打ち寄せる様子、夕暮れ時",
        ...     duration_seconds=6,
        ... )
        >>> print(result["status"])
        "IN_PROGRESS"
        >>> print(result["job_id"])
        "arn:aws:bedrock:ap-northeast-1:..."
    """
    import boto3

    region = os.environ.get("AWS_REGION", "ap-northeast-1")
    output_bucket = os.environ.get("OUTPUT_BUCKET", "rd-knowledge-multimodal-output")
    job_id = str(uuid.uuid4())

    logger.info(f"Starting video generation: prompt='{prompt[:50]}...', duration={duration_seconds}s")

    try:
        bedrock = boto3.client("bedrock-runtime", region_name=region)

        # リクエストボディの構築
        request_body = {
            "taskType": "TEXT_VIDEO",
            "textToVideoParams": {
                "text": prompt,
            },
            "videoGenerationConfig": {
                "durationSeconds": min(duration_seconds, 6),  # 最大6秒
                "fps": fps,
                "dimension": dimension,
            },
        }

        if seed is not None:
            request_body["videoGenerationConfig"]["seed"] = seed

        # S3 出力先
        output_s3_uri = f"s3://{output_bucket}/generated/videos/{job_id}/"

        # Bedrock StartAsyncInvoke API 呼び出し
        response = bedrock.start_async_invoke(
            modelId="amazon.nova-reel-v1:0",
            modelInput=request_body,
            outputDataConfig={
                "s3OutputDataConfig": {
                    "s3Uri": output_s3_uri,
                }
            },
        )

        invocation_arn = response.get("invocationArn", "")
        logger.info(f"Video generation started: job_id={invocation_arn}")

        return {
            "job_id": invocation_arn,
            "status": "IN_PROGRESS",
            "status_url": f"/v1/multimodal/status/{invocation_arn}",
            "output_s3_uri": output_s3_uri,
            "success": True,
        }

    except Exception as e:
        logger.exception(f"Video generation failed: {e}")
        return {
            "job_id": job_id,
            "status": "FAILED",
            "error": str(e),
            "success": False,
        }


@tool
def get_video_status(job_id: str) -> dict[str, Any]:
    """
    動画生成ジョブの状態を確認します。

    video_generate で開始したジョブの完了状態を確認します。
    完了すると動画の S3 URI が返されます。

    Args:
        job_id: video_generate で返された job_id（invocationArn）

    Returns:
        dict: {
            "job_id": "...",
            "status": "IN_PROGRESS" | "COMPLETED" | "FAILED",
            "video_s3_uri": "s3://..." (完了時のみ),
            "error": "..." (失敗時のみ)
        }

    Example:
        >>> result = get_video_status("arn:aws:bedrock:ap-northeast-1:...")
        >>> if result["status"] == "COMPLETED":
        ...     print(f"Video ready: {result['video_s3_uri']}")
    """
    import boto3

    region = os.environ.get("AWS_REGION", "ap-northeast-1")

    logger.info(f"Checking video status: job_id={job_id[:50]}...")

    try:
        bedrock = boto3.client("bedrock-runtime", region_name=region)

        response = bedrock.get_async_invoke(invocationArn=job_id)

        status = response.get("status", "UNKNOWN")
        result: dict[str, Any] = {
            "job_id": job_id,
            "status": status,
        }

        if status == "Completed":
            output_config = response.get("outputDataConfig", {})
            s3_config = output_config.get("s3OutputDataConfig", {})
            result["video_s3_uri"] = s3_config.get("s3Uri", "")
            result["success"] = True
            logger.info(f"Video completed: {result['video_s3_uri']}")

        elif status == "Failed":
            result["error"] = response.get("failureMessage", "Unknown error")
            result["success"] = False
            logger.error(f"Video generation failed: {result['error']}")

        else:
            result["success"] = True
            logger.info(f"Video status: {status}")

        return result

    except Exception as e:
        logger.exception(f"Failed to get video status: {e}")
        return {
            "job_id": job_id,
            "status": "UNKNOWN",
            "error": str(e),
            "success": False,
        }

