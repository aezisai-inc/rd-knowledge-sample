"""
AgentCore Runtime Entry Point

AgentCore Runtime にデプロイするためのエントリーポイント。
bedrock-agentcore-starter-toolkit で使用。

Usage:
    # ローカル開発サーバー
    agentcore dev

    # AWS デプロイ
    agentcore launch
"""

from __future__ import annotations

import logging
import os
from typing import Any

from strands import Agent
from strands.models import BedrockModel

from .config import create_session_manager
from .tools import image_generate, video_generate, get_video_status

logger = logging.getLogger(__name__)

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
- `get_video_status`: 動画生成ジョブの状態を確認します

## 回答のガイドライン
1. ユーザーの要求を正確に理解し、適切な処理を行う
2. 画像/動画の「理解」は私が直接行い、「生成」はツールを使用
3. 結果は日本語で分かりやすく説明する
4. エラーが発生した場合は原因と対処法を説明する
5. 過去の会話を覚えて、文脈に沿った回答をする

## 注意事項
- 動画生成は非同期処理のため、ジョブIDを返します
- 大きな画像/動画は S3 URI で指定してください
"""


# =============================================================================
# Agent Factory
# =============================================================================

def create_agent(
    actor_id: str = "",
    session_id: str = "",
    use_memory: bool = True,
) -> Agent:
    """
    Multimodal Agent を作成

    Args:
        actor_id: アクターID（ユーザー識別子）
        session_id: セッションID（会話識別子）
        use_memory: AgentCore Memory を使用するか

    Returns:
        Agent インスタンス
    """
    region = os.environ.get("AWS_REGION", "ap-northeast-1")
    model_id = os.environ.get("MODEL_ID", "amazon.nova-pro-v1:0")

    # Bedrock Model
    model = BedrockModel(
        model_id=model_id,
        region_name=region,
    )

    # Tools
    tools = [
        image_generate,
        video_generate,
        get_video_status,
    ]

    # Session Manager (AgentCore Memory)
    session_manager = None
    if use_memory:
        try:
            session_manager = create_session_manager(
                actor_id=actor_id,
                session_id=session_id,
            )
            logger.info(f"AgentCore Memory enabled: actor={actor_id}, session={session_id}")
        except Exception as e:
            logger.warning(f"Failed to initialize AgentCore Memory: {e}")

    # Create Agent
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        session_manager=session_manager,
    )

    logger.info(f"Agent created: model={model_id}, memory={'enabled' if session_manager else 'disabled'}")
    return agent


# =============================================================================
# AgentCore Runtime Handler
# =============================================================================

# Default agent instance for AgentCore Runtime
_runtime_agent: Agent | None = None


def get_runtime_agent() -> Agent:
    """Runtime 用のエージェントを取得"""
    global _runtime_agent
    if _runtime_agent is None:
        _runtime_agent = create_agent(
            use_memory=os.environ.get("USE_AGENTCORE_MEMORY", "true").lower() == "true"
        )
    return _runtime_agent


async def handler(event: dict[str, Any]) -> dict[str, Any]:
    """
    AgentCore Runtime ハンドラー

    Args:
        event: リクエストイベント
            - message: ユーザーメッセージ
            - actor_id: アクターID（オプション）
            - session_id: セッションID（オプション）
            - images: Base64 エンコード画像リスト（オプション）
            - videos: S3 URI リスト（オプション）

    Returns:
        レスポンス
            - response: エージェント応答
            - usage: トークン使用量
    """
    import base64

    message = event.get("message", "")
    actor_id = event.get("actor_id", "")
    session_id = event.get("session_id", "")
    images_b64 = event.get("images", [])
    videos = event.get("videos", [])

    # エージェント取得（セッション指定がある場合は新規作成）
    if actor_id or session_id:
        agent = create_agent(actor_id=actor_id, session_id=session_id)
    else:
        agent = get_runtime_agent()

    # マルチモーダル入力の構築
    content = []

    # 画像を追加
    for img_b64 in images_b64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": img_b64,
            },
        })

    # 動画を追加
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
    try:
        response = await agent.arun(content)
        return {
            "response": response.content,
            "usage": getattr(response, "usage", {}),
            "success": True,
        }
    except Exception as e:
        logger.exception(f"Agent execution failed: {e}")
        return {
            "response": f"エラーが発生しました: {str(e)}",
            "error": str(e),
            "success": False,
        }


# =============================================================================
# For agentcore starter toolkit
# =============================================================================

# Export agent for agentcore toolkit
agent = get_runtime_agent()

