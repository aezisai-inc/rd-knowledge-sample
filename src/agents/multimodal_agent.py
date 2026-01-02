"""
Multimodal Agent using StrandsAgents SDK

AWS Nova Pro を使用したマルチモーダル AI エージェント。
AgentCore Runtime でホスト、AgentCore Memory で記憶管理。

設計原則:
- AgentCore + StrandsAgents + BedrockAPI 構成
- AgentCore_Observability / CloudTrail 追跡可能
- AgentCore_Memory + S3Vector (コスト最小)
- boto3 / cli / script / sh 直接処理禁止
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from strands import Agent
from strands.models import BedrockModel

from .tools import image_generate, video_generate

if TYPE_CHECKING:
    from strands.types import AgentResponse

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class MultimodalConfig:
    """Multimodal Agent 設定"""

    # Model
    model_id: str = "amazon.nova-pro-v1:0"
    region: str = field(default_factory=lambda: os.environ.get("AWS_REGION", "ap-northeast-1"))

    # AgentCore Memory
    memory_id: str = field(default_factory=lambda: os.environ.get("AGENTCORE_MEMORY_ID", ""))

    # S3
    output_bucket: str = field(
        default_factory=lambda: os.environ.get("OUTPUT_BUCKET", "rd-knowledge-multimodal-output")
    )


# =============================================================================
# System Prompt
# =============================================================================

SYSTEM_PROMPT = """あなたは AWS Nova を活用したマルチモーダル AI アシスタントです。

## 能力
1. **画像の理解・分析**: 画像を見て、内容を説明したり質問に答えたりできます
2. **動画の理解・要約**: 動画を見て、内容を要約したり特定のシーンを説明できます
3. **画像の生成**: テキストの説明から画像を生成できます（Nova Canvas）
4. **動画の生成**: テキストの説明から動画を生成できます（Nova Reel）

## 使用可能なツール
- `image_generate`: テキストから画像を生成します
- `video_generate`: テキストから動画を生成します（非同期）

## 回答のガイドライン
1. ユーザーの要求を正確に理解し、適切な処理を行う
2. 画像/動画の「理解」は私が直接行い、「生成」はツールを使用
3. 結果は日本語で分かりやすく説明する
4. エラーが発生した場合は原因と対処法を説明する
5. 不明な点があれば、確認の質問をする

## 注意事項
- 動画生成は非同期処理のため、ジョブIDを返します
- 大きな画像/動画は S3 URI で指定してください
"""


# =============================================================================
# Multimodal Agent Class
# =============================================================================

class MultimodalAgent:
    """
    StrandsAgents ベースのマルチモーダルエージェント

    Features:
    - Nova Pro によるマルチモーダル理解（画像・動画）
    - Nova Canvas / Reel による生成（Tool 経由）
    - AgentCore Memory による記憶管理
    - AgentCore Observability による追跡
    """

    def __init__(self, config: MultimodalConfig | None = None):
        """
        Args:
            config: エージェント設定（省略時はデフォルト設定）
        """
        self.config = config or MultimodalConfig()
        self._agent: Agent | None = None
        self._initialize()

    def _initialize(self) -> None:
        """エージェントを初期化"""
        # Bedrock Model (Nova Pro)
        model = BedrockModel(
            model_id=self.config.model_id,
            region_name=self.config.region,
        )

        # Tools
        tools = [
            image_generate,
            video_generate,
        ]

        # Agent
        self._agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
        )

        logger.info(
            f"MultimodalAgent initialized: model={self.config.model_id}, "
            f"region={self.config.region}"
        )

    @property
    def agent(self) -> Agent:
        """内部 Agent インスタンスを取得"""
        if self._agent is None:
            self._initialize()
        return self._agent

    async def run(
        self,
        message: str,
        images: list[bytes] | None = None,
        videos: list[str] | None = None,
        session_id: str | None = None,
    ) -> AgentResponse:
        """
        エージェントを実行

        Args:
            message: ユーザーメッセージ
            images: 画像バイナリのリスト
            videos: 動画 S3 URI のリスト
            session_id: セッションID（会話継続用）

        Returns:
            エージェントレスポンス
        """
        # マルチモーダル入力の構築
        content = []

        # 画像を追加
        if images:
            for img_data in images:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(img_data).decode("utf-8"),
                    },
                })

        # 動画を追加（S3 URI）
        if videos:
            for video_uri in videos:
                content.append({
                    "type": "video",
                    "source": {
                        "type": "s3",
                        "uri": video_uri,
                    },
                })

        # テキストを追加
        content.append({"type": "text", "text": message})

        # エージェント実行
        response = await self.agent.arun(
            content,
            session_id=session_id,
        )

        return response

    def run_sync(
        self,
        message: str,
        images: list[bytes] | None = None,
        videos: list[str] | None = None,
        session_id: str | None = None,
    ) -> AgentResponse:
        """
        エージェントを同期実行

        Args:
            message: ユーザーメッセージ
            images: 画像バイナリのリスト
            videos: 動画 S3 URI のリスト
            session_id: セッションID

        Returns:
            エージェントレスポンス
        """
        import asyncio

        return asyncio.run(self.run(message, images, videos, session_id))


# =============================================================================
# Convenience Functions
# =============================================================================

# シングルトンインスタンス
_default_agent: MultimodalAgent | None = None


def get_default_agent() -> MultimodalAgent:
    """デフォルトエージェントを取得"""
    global _default_agent
    if _default_agent is None:
        _default_agent = MultimodalAgent()
    return _default_agent


async def understand_image(image_data: bytes, prompt: str, session_id: str | None = None) -> str:
    """
    画像理解

    Args:
        image_data: 画像バイナリデータ
        prompt: ユーザープロンプト
        session_id: セッションID

    Returns:
        理解結果テキスト

    Example:
        >>> with open("image.png", "rb") as f:
        ...     result = await understand_image(f.read(), "この画像を説明してください")
        >>> print(result)
        "この画像には..."
    """
    agent = get_default_agent()
    response = await agent.run(prompt, images=[image_data], session_id=session_id)
    return response.content


async def understand_video(video_s3_uri: str, prompt: str, session_id: str | None = None) -> str:
    """
    動画理解

    Args:
        video_s3_uri: 動画の S3 URI
        prompt: ユーザープロンプト
        session_id: セッションID

    Returns:
        理解結果テキスト

    Example:
        >>> result = await understand_video(
        ...     "s3://my-bucket/video.mp4",
        ...     "この動画を要約してください"
        ... )
        >>> print(result)
        "この動画では..."
    """
    agent = get_default_agent()
    response = await agent.run(prompt, videos=[video_s3_uri], session_id=session_id)
    return response.content


async def generate_image(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    画像生成

    Args:
        prompt: 生成プロンプト
        negative_prompt: ネガティブプロンプト
        width: 幅（px）
        height: 高さ（px）
        session_id: セッションID

    Returns:
        生成結果（images, model）

    Example:
        >>> result = await generate_image("富士山と桜の風景")
        >>> print(result["images"][0]["base64"][:50])
        "iVBORw0KGgoAAAANSUhE..."
    """
    agent = get_default_agent()
    message = f"""以下の条件で画像を生成してください:

プロンプト: {prompt}
ネガティブプロンプト: {negative_prompt or "なし"}
サイズ: {width}x{height}
"""
    response = await agent.run(message, session_id=session_id)

    # Tool 実行結果を抽出
    if hasattr(response, "tool_results") and response.tool_results:
        return response.tool_results
    return {"error": "Tool execution failed", "content": response.content}


async def generate_video(
    prompt: str,
    duration_seconds: int = 6,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    動画生成（非同期）

    Args:
        prompt: 生成プロンプト
        duration_seconds: 動画長（秒）
        session_id: セッションID

    Returns:
        ジョブ情報（job_id, status, status_url）

    Example:
        >>> result = await generate_video("海辺で波が打ち寄せる様子")
        >>> print(result["job_id"])
        "arn:aws:bedrock:ap-northeast-1:..."
    """
    agent = get_default_agent()
    message = f"""以下の条件で動画を生成してください:

プロンプト: {prompt}
長さ: {duration_seconds}秒
"""
    response = await agent.run(message, session_id=session_id)

    # Tool 実行結果を抽出
    if hasattr(response, "tool_results") and response.tool_results:
        return response.tool_results
    return {"error": "Tool execution failed", "content": response.content}

