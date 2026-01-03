"""
Mock Bedrock Nova Service

テスト・開発用のモック Nova API。
本番では Bedrock Runtime API に置き換え。
"""

from typing import Any, Optional


class MockBedrockNovaService:
    """
    Bedrock Nova API のモック実装
    
    テスト用。実際の API 呼び出しは行わない。
    """
    
    async def invoke_text(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """テキスト生成"""
        return f"[Mock Response from {model_id}] {prompt[:50]}... への応答です。"
    
    async def invoke_vision(
        self,
        model_id: str,
        prompt: str,
        image_base64: str,
    ) -> str:
        """画像理解"""
        return f"[Mock Vision Response] 画像を分析しました: {prompt[:30]}..."
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """画像生成"""
        # 1x1 透明PNG (最小のBase64)
        mock_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        
        return {
            "base64": mock_image,
            "seed": 12345,
            "prompt": prompt,
        }
    
    async def generate_video(
        self,
        prompt: str,
        duration_seconds: int = 6,
    ) -> dict[str, Any]:
        """動画生成"""
        return {
            "url": "s3://mock-bucket/mock-video.mp4",
            "prompt": prompt,
            "duration_seconds": duration_seconds,
        }
    
    async def process_voice(
        self,
        audio_base64: str,
    ) -> dict[str, Any]:
        """音声処理（STT）"""
        return {
            "transcript": "[Mock Transcript] 音声認識結果のテキストです。",
            "confidence": 0.95,
        }
    
    async def synthesize_speech(
        self,
        text: str,
    ) -> dict[str, Any]:
        """音声合成（TTS）"""
        # Mock MP3 header
        mock_audio = "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4LjM1LjEwMAAA"
        
        return {
            "audio_base64": mock_audio,
            "text": text,
        }
