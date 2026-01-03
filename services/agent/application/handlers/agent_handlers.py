"""
Agent Handlers - CQRS Application Layer

Multimodal / Voice エージェントのハンドラ。
StrandsAgents + Bedrock Nova API を使用。
"""

from dataclasses import dataclass
from typing import Any, Optional, Protocol

from services.agent.domain.entities.agent_session import (
    AgentSession,
    AgentSessionId,
    AgentType,
    AgentResponse,
)


# ============================================================================
# Repository Protocol
# ============================================================================

class AgentSessionRepository(Protocol):
    """エージェントセッションリポジトリ"""
    
    async def save(self, session: AgentSession) -> None:
        ...
    
    async def find_by_id(self, session_id: AgentSessionId) -> Optional[AgentSession]:
        ...


class BedrockNovaService(Protocol):
    """Bedrock Nova API サービス"""
    
    async def invoke_text(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        ...
    
    async def invoke_vision(
        self,
        model_id: str,
        prompt: str,
        image_base64: str,
    ) -> str:
        ...
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        ...
    
    async def process_voice(
        self,
        audio_base64: str,
    ) -> dict[str, Any]:
        ...


# ============================================================================
# Commands
# ============================================================================

@dataclass(frozen=True)
class InvokeMultimodalCommand:
    """Multimodal エージェント呼び出しコマンド"""
    memory_session_id: str
    prompt: str
    image_base64: Optional[str] = None
    generate_image: bool = False
    generate_video: bool = False


@dataclass(frozen=True)
class SendVoiceCommand:
    """Voice エージェント呼び出しコマンド"""
    memory_session_id: str
    text: str
    audio_base64: Optional[str] = None


# ============================================================================
# Results
# ============================================================================

@dataclass
class MultimodalResult:
    """Multimodal 結果"""
    session_id: str
    response: AgentResponse
    latency_ms: int


@dataclass
class VoiceResult:
    """Voice 結果"""
    session_id: str
    transcript: Optional[str]
    user_text: str
    assistant_text: str
    audio_base64: Optional[str]
    latency_ms: int


# ============================================================================
# Handlers
# ============================================================================

class MultimodalHandler:
    """Multimodal エージェントハンドラ"""
    
    def __init__(
        self,
        repository: AgentSessionRepository,
        nova_service: BedrockNovaService,
    ):
        self._repository = repository
        self._nova_service = nova_service
    
    async def handle(self, command: InvokeMultimodalCommand) -> MultimodalResult:
        """Multimodal エージェントを呼び出し"""
        import time
        start_time = time.time()
        
        # 1. セッション作成または取得
        session = AgentSession.create(
            agent_type=AgentType.MULTIMODAL,
            memory_session_id=command.memory_session_id,
        )
        
        response = AgentResponse()
        
        # 2. 処理実行
        if command.image_base64:
            # 画像理解
            text = await self._nova_service.invoke_vision(
                model_id="amazon.nova-pro-v1:0",
                prompt=command.prompt,
                image_base64=command.image_base64,
            )
            response.message = text
            session.record_tool_call(
                tool_name="nova_vision",
                input_data={"prompt": command.prompt, "has_image": True},
                output_data={"text": text[:100]},
            )
        elif command.generate_image:
            # 画像生成
            image_result = await self._nova_service.generate_image(
                prompt=command.prompt,
            )
            response.images = [image_result]
            response.message = f"画像を生成しました: {command.prompt}"
            session.record_tool_call(
                tool_name="nova_canvas",
                input_data={"prompt": command.prompt},
                output_data={"generated": True},
            )
        else:
            # テキスト応答
            text = await self._nova_service.invoke_text(
                model_id="amazon.nova-pro-v1:0",
                prompt=command.prompt,
            )
            response.message = text
            session.record_tool_call(
                tool_name="nova_text",
                input_data={"prompt": command.prompt},
                output_data={"text": text[:100]},
            )
        
        # 3. 保存
        await self._repository.save(session)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return MultimodalResult(
            session_id=str(session.id),
            response=response,
            latency_ms=latency_ms,
        )


class VoiceHandler:
    """Voice エージェントハンドラ"""
    
    def __init__(
        self,
        repository: AgentSessionRepository,
        nova_service: BedrockNovaService,
    ):
        self._repository = repository
        self._nova_service = nova_service
    
    async def handle(self, command: SendVoiceCommand) -> VoiceResult:
        """Voice エージェントを呼び出し"""
        import time
        start_time = time.time()
        
        # 1. セッション作成
        session = AgentSession.create(
            agent_type=AgentType.VOICE,
            memory_session_id=command.memory_session_id,
        )
        
        transcript = None
        
        # 2. 音声処理（あれば）
        if command.audio_base64:
            voice_result = await self._nova_service.process_voice(
                audio_base64=command.audio_base64,
            )
            transcript = voice_result.get("transcript")
            session.record_tool_call(
                tool_name="nova_sonic_stt",
                input_data={"has_audio": True},
                output_data={"transcript": transcript[:50] if transcript else None},
            )
        
        # 3. テキスト応答生成
        input_text = transcript or command.text
        assistant_text = await self._nova_service.invoke_text(
            model_id="amazon.nova-sonic-v1:0",
            prompt=input_text,
        )
        session.record_tool_call(
            tool_name="nova_sonic_tts",
            input_data={"text": input_text[:50]},
            output_data={"response": assistant_text[:50]},
        )
        
        # 4. 保存
        await self._repository.save(session)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return VoiceResult(
            session_id=str(session.id),
            transcript=transcript,
            user_text=input_text,
            assistant_text=assistant_text,
            audio_base64=None,  # TTS は別途実装
            latency_ms=latency_ms,
        )
