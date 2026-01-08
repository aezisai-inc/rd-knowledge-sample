"""
AgentCore Runtime Entry Point

Standard entry point for agentcore dev/launch commands.
Uses BedrockAgentCoreApp for proper runtime integration.
"""

import json
import logging
import os
from typing import Any

from bedrock_agentcore import BedrockAgentCoreApp, RequestContext
from strands import Agent
from strands.models import BedrockModel

from src.agents.tools import image_generate, video_generate, get_video_status
from src.agents.config import create_session_manager

logger = logging.getLogger(__name__)

# =============================================================================
# System Prompt
# =============================================================================

SYSTEM_PROMPT = """あなたは AWS Nova を活用したマルチモーダル AI アシスタントです。

## 能力
1. **画像の理解・分析**: 画像を見て、内容を説明したり質問に答えたりできます
2. **動画の理解・要約**: 動画を見て、内容を要約したり特定のシーンを説明できます
3. **画像の生成**: テキストの説明から画像を生成できます（Nova Canvas）
4. **動画の生成**: テキストの説明から動画を生成します（Nova Reel）

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
# AgentCore App Setup
# =============================================================================

app = BedrockAgentCoreApp()

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


# Default agent for simple invocations
_default_agent: Agent | None = None


def get_default_agent() -> Agent:
    """Get or create the default agent instance."""
    global _default_agent
    if _default_agent is None:
        _default_agent = create_agent(
            use_memory=os.environ.get("USE_AGENTCORE_MEMORY", "true").lower() == "true"
        )
    return _default_agent


@app.entrypoint
def agent_invocation(payload: dict[str, Any], context: RequestContext) -> dict[str, Any]:
    """
    AgentCore Runtime handler with BedrockAgentCoreApp

    Args:
        payload: Request payload
            - prompt: User message (required)
            - actor_id: Actor ID (optional)
            - session_id: Session ID (optional)
            - images: Base64 encoded images (optional)
            - videos: S3 URIs for videos (optional)
        context: Request context with headers

    Returns:
        Response dict with agent output
    """
    app.logger.info(f"Received invocation: {json.dumps(payload, default=str)[:500]}")

    # Extract payload fields
    prompt = payload.get("prompt", payload.get("message", ""))
    actor_id = payload.get("actor_id", "")
    session_id = payload.get("session_id", "")
    images_b64 = payload.get("images", [])
    videos = payload.get("videos", [])

    if not prompt:
        return {
            "response": "プロンプトが指定されていません",
            "success": False,
            "error": "No prompt provided",
        }

    # Get or create agent
    if actor_id or session_id:
        agent = create_agent(actor_id=actor_id, session_id=session_id)
    else:
        agent = get_default_agent()

    # Build multimodal content
    content = []

    # Add images
    for img_b64 in images_b64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": img_b64,
            },
        })

    # Add videos
    for video_uri in videos:
        content.append({
            "type": "video",
            "source": {
                "type": "s3",
                "uri": video_uri,
            },
        })

    # Add text
    content.append({"type": "text", "text": prompt})

    # Execute agent
    try:
        # Use multimodal content if images/videos provided, otherwise just text
        if len(content) > 1:
            response = agent(content)
        else:
            response = agent(prompt)

        return {
            "response": str(response),
            "usage": getattr(response, "usage", {}),
            "success": True,
        }
    except Exception as e:
        app.logger.exception(f"Agent execution failed: {e}")
        return {
            "response": f"エラーが発生しました: {str(e)}",
            "error": str(e),
            "success": False,
        }


# Export for agentcore toolkit
agent = get_default_agent

if __name__ == "__main__":
    app.run()
