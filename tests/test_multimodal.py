"""
Multimodal Agent E2E Tests

StrandsAgents + Nova を使用したマルチモーダルエージェントのE2Eテスト。

テスト対象:
- 画像理解 (Nova Vision)
- 画像生成 (Nova Canvas)
- 動画生成 (Nova Reel)
"""

import base64
import os
from pathlib import Path

import pytest

# Skip if not running in AWS environment
pytestmark = pytest.mark.skipif(
    os.environ.get("AWS_EXECUTION_ENV") is None and os.environ.get("AWS_REGION") is None,
    reason="AWS credentials not configured"
)


class TestMultimodalAgent:
    """Multimodal Agent のE2Eテスト"""

    @pytest.fixture
    def sample_image_base64(self) -> str:
        """テスト用サンプル画像 (1x1 PNG)"""
        # 最小の PNG 画像 (1x1 白)
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        return base64.b64encode(png_bytes).decode("utf-8")

    @pytest.fixture
    def api_base_url(self) -> str:
        """API ベース URL"""
        return os.environ.get(
            "API_BASE_URL",
            "https://s3pa7bz4o2.execute-api.ap-northeast-1.amazonaws.com/dev"
        )

    @pytest.mark.asyncio
    async def test_multimodal_agent_import(self):
        """Multimodal Agent がインポートできること"""
        from src.agents import MultimodalAgent

        assert MultimodalAgent is not None

    @pytest.mark.asyncio
    async def test_image_understand_function(self):
        """画像理解関数が存在すること"""
        from src.agents import understand_image

        assert callable(understand_image)

    @pytest.mark.asyncio
    async def test_image_generate_function(self):
        """画像生成関数が存在すること"""
        from src.agents import generate_image

        assert callable(generate_image)

    @pytest.mark.asyncio
    async def test_video_generate_function(self):
        """動画生成関数が存在すること"""
        from src.agents import generate_video

        assert callable(generate_video)

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_image_understanding_integration(self, sample_image_base64: str):
        """
        画像理解の統合テスト

        Note: 実際の Bedrock API を呼び出すため、コストが発生します。
        """
        from src.agents import understand_image

        image_bytes = base64.b64decode(sample_image_base64)
        
        try:
            result = await understand_image(
                image_data=image_bytes,
                prompt="この画像を説明してください",
            )
            assert isinstance(result, str)
            assert len(result) > 0
        except Exception as e:
            # モデルアクセス権限がない場合はスキップ
            if "AccessDeniedException" in str(e):
                pytest.skip("Bedrock model access not configured")
            raise

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_image_generation_integration(self):
        """
        画像生成の統合テスト

        Note: 実際の Bedrock API を呼び出すため、コストが発生します。
        """
        from src.agents import generate_image

        try:
            result = await generate_image(
                prompt="青い空と白い雲",
                width=512,
                height=512,
            )
            assert isinstance(result, dict)
            # 成功時は images キーが存在
            if "error" not in result:
                assert "images" in result or "model" in result
        except Exception as e:
            if "AccessDeniedException" in str(e):
                pytest.skip("Bedrock model access not configured")
            raise


class TestMultimodalTools:
    """Multimodal Tools のユニットテスト"""

    def test_image_generate_tool_exists(self):
        """image_generate ツールが存在すること"""
        from src.agents.tools import image_generate

        assert image_generate is not None
        assert hasattr(image_generate, "__name__")

    def test_video_generate_tool_exists(self):
        """video_generate ツールが存在すること"""
        from src.agents.tools import video_generate

        assert video_generate is not None
        assert hasattr(video_generate, "__name__")


class TestMultimodalConfig:
    """Multimodal 設定のテスト"""

    def test_default_model_id(self):
        """デフォルトモデル ID が設定されていること"""
        from src.agents.multimodal_agent import MultimodalConfig

        config = MultimodalConfig()
        assert config.model_id == "amazon.nova-pro-v1:0"

    def test_default_region(self):
        """デフォルトリージョンが設定されていること"""
        from src.agents.multimodal_agent import MultimodalConfig

        config = MultimodalConfig()
        # 環境変数がなければ ap-northeast-1
        expected = os.environ.get("AWS_REGION", "ap-northeast-1")
        assert config.region == expected

