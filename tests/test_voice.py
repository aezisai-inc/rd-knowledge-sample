"""
Voice Dialogue Agent E2E Tests

StrandsAgents + Nova Sonic を使用した音声対話エージェントのE2Eテスト。

テスト対象:
- VoiceDialogueAgent のインスタンス化
- セッション管理
- 音声/テキスト処理
"""

import os

import pytest

# Skip if not running in AWS environment
pytestmark = pytest.mark.skipif(
    os.environ.get("AWS_EXECUTION_ENV") is None and os.environ.get("AWS_REGION") is None,
    reason="AWS credentials not configured"
)


class TestVoiceDialogueAgent:
    """Voice Dialogue Agent のE2Eテスト"""

    @pytest.fixture
    def api_base_url(self) -> str:
        """API ベース URL"""
        return os.environ.get(
            "API_BASE_URL",
            "https://s3pa7bz4o2.execute-api.ap-northeast-1.amazonaws.com/dev"
        )

    @pytest.mark.asyncio
    async def test_voice_agent_import(self):
        """Voice Agent がインポートできること"""
        from src.agents import VoiceDialogueAgent

        assert VoiceDialogueAgent is not None

    @pytest.mark.asyncio
    async def test_voice_config_import(self):
        """VoiceConfig がインポートできること"""
        from src.agents import VoiceConfig

        assert VoiceConfig is not None

    def test_voice_agent_instantiation(self):
        """Voice Agent がインスタンス化できること"""
        from src.agents import VoiceDialogueAgent, VoiceConfig

        config = VoiceConfig(
            voice_id="ruth",
            language="en-US",
        )
        agent = VoiceDialogueAgent(
            config=config,
            actor_id="test-actor",
            session_id="test-session",
        )

        assert agent is not None
        assert agent.config.voice_id == "ruth"
        assert agent.config.language == "en-US"

    @pytest.mark.asyncio
    async def test_start_session(self):
        """セッション開始ができること"""
        from src.agents import VoiceDialogueAgent

        agent = VoiceDialogueAgent(
            actor_id="test-actor",
            session_id="test-session",
        )

        result = await agent.start_session()

        assert result is not None
        assert result["status"] == "started"
        assert "model_id" in result
        assert "voice_id" in result

    @pytest.mark.asyncio
    async def test_end_session(self):
        """セッション終了ができること"""
        from src.agents import VoiceDialogueAgent

        agent = VoiceDialogueAgent(
            actor_id="test-actor",
            session_id="test-session",
        )

        await agent.start_session()
        result = await agent.end_session()

        assert result is not None
        assert result["status"] == "ended"


class TestVoiceConfig:
    """Voice 設定のテスト"""

    def test_default_model_id(self):
        """デフォルトモデル ID が設定されていること"""
        from src.agents.voice_agent import VoiceConfig

        config = VoiceConfig()
        assert config.model_id == "amazon.nova-2-sonic-v1:0"

    def test_default_voice_id(self):
        """デフォルト音声 ID が設定されていること"""
        from src.agents.voice_agent import VoiceConfig

        config = VoiceConfig()
        assert config.voice_id == "ruth"

    def test_default_language(self):
        """デフォルト言語が設定されていること"""
        from src.agents.voice_agent import VoiceConfig

        config = VoiceConfig()
        assert config.language == "en-US"

    def test_custom_voice_config(self):
        """カスタム設定が適用されること"""
        from src.agents.voice_agent import VoiceConfig

        config = VoiceConfig(
            voice_id="matthew",
            language="en-GB",
            max_tokens=2048,
        )

        assert config.voice_id == "matthew"
        assert config.language == "en-GB"
        assert config.max_tokens == 2048


class TestVoiceConvenienceFunctions:
    """Voice ユーティリティ関数のテスト"""

    def test_get_default_voice_agent(self):
        """デフォルト Voice Agent を取得できること"""
        from src.agents import get_default_voice_agent

        agent = get_default_voice_agent()
        assert agent is not None

    @pytest.mark.asyncio
    async def test_start_voice_session_function(self):
        """start_voice_session 関数が動作すること"""
        from src.agents import start_voice_session

        result = await start_voice_session(
            actor_id="test-actor",
            session_id="test-session",
            voice_id="ruth",
            language="en-US",
        )

        assert result is not None
        assert result["status"] == "started"

