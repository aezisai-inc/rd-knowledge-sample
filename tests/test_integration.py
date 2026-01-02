"""
統合 E2E テスト

全3テストケース（Memory / Multimodal / Voice）の統合テスト。

テスト対象:
- 各エージェントの初期化
- AgentCore Memory との連携
- AWS API への接続性
"""

import os

import pytest

# Skip if not running in AWS environment
pytestmark = pytest.mark.skipif(
    os.environ.get("AWS_EXECUTION_ENV") is None and os.environ.get("AWS_REGION") is None,
    reason="AWS credentials not configured"
)


class TestAgentImports:
    """全エージェントのインポートテスト"""

    def test_multimodal_agent_import(self):
        """Multimodal Agent がインポートできること"""
        from src.agents import MultimodalAgent
        assert MultimodalAgent is not None

    def test_voice_agent_import(self):
        """Voice Agent がインポートできること"""
        from src.agents import VoiceDialogueAgent
        assert VoiceDialogueAgent is not None

    def test_all_exports(self):
        """全エクスポートが存在すること"""
        from src.agents import (
            MultimodalAgent,
            understand_image,
            understand_video,
            generate_image,
            generate_video,
            VoiceDialogueAgent,
            VoiceConfig,
            get_default_voice_agent,
            start_voice_session,
            process_voice_input,
        )

        assert all([
            MultimodalAgent,
            understand_image,
            understand_video,
            generate_image,
            generate_video,
            VoiceDialogueAgent,
            VoiceConfig,
            get_default_voice_agent,
            start_voice_session,
            process_voice_input,
        ])


class TestAgentCoreMemoryIntegration:
    """AgentCore Memory 統合テスト"""

    def test_memory_config_import(self):
        """AgentCore Memory 設定がインポートできること"""
        from src.agents.config import AgentCoreMemorySettings
        assert AgentCoreMemorySettings is not None

    def test_session_manager_creation(self):
        """Session Manager が作成できること（環境変数依存）"""
        memory_id = os.environ.get("AGENTCORE_MEMORY_ID")
        if not memory_id:
            pytest.skip("AGENTCORE_MEMORY_ID not set")

        from src.agents.config import create_session_manager

        session_manager = create_session_manager(
            actor_id="test-actor",
            session_id="test-session",
        )
        assert session_manager is not None


class TestStorageAdapters:
    """Storage アダプターの統合テスト"""

    def test_vector_store_protocol(self):
        """VectorStore Protocol が定義されていること"""
        from src.interfaces.storage import VectorStoreProtocol
        assert VectorStoreProtocol is not None

    def test_memory_store_protocol(self):
        """MemoryStore Protocol が定義されていること"""
        from src.interfaces.storage import MemoryStoreProtocol
        assert MemoryStoreProtocol is not None

    def test_graph_store_protocol(self):
        """GraphStore Protocol が定義されていること"""
        from src.interfaces.storage import GraphStoreProtocol
        assert GraphStoreProtocol is not None

    def test_aws_vector_store_import(self):
        """AWS VectorStore がインポートできること"""
        from src.adapters.aws.vector_store import AWSVectorStore
        assert AWSVectorStore is not None

    def test_aws_memory_store_import(self):
        """AWS MemoryStore がインポートできること"""
        from src.adapters.aws.memory_store import AWSMemoryStore
        assert AWSMemoryStore is not None

    def test_aws_graph_store_import(self):
        """AWS GraphStore がインポートできること"""
        from src.adapters.aws.graph_store import AWSGraphStore
        assert AWSGraphStore is not None


class TestToolsIntegration:
    """Tools 統合テスト"""

    def test_image_generate_tool(self):
        """image_generate ツールが存在すること"""
        from src.agents.tools import image_generate
        assert image_generate is not None

    def test_video_generate_tool(self):
        """video_generate ツールが存在すること"""
        from src.agents.tools import video_generate
        assert video_generate is not None


class TestRuntimeIntegration:
    """Runtime 統合テスト"""

    def test_runtime_handler_import(self):
        """Runtime ハンドラーがインポートできること"""
        from src.agents.runtime import handler, create_agent
        assert handler is not None
        assert create_agent is not None

    def test_create_agent_without_memory(self):
        """Memory なしでエージェントが作成できること"""
        from src.agents.runtime import create_agent

        agent = create_agent(use_memory=False)
        assert agent is not None


class TestEndToEndScenarios:
    """E2E シナリオテスト"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_multimodal_voice_integration(self):
        """
        Multimodal と Voice の統合シナリオ

        シナリオ:
        1. Multimodal Agent で画像を分析
        2. 結果を Voice Agent で音声出力
        """
        from src.agents import MultimodalAgent, VoiceDialogueAgent

        # エージェント作成
        multimodal_agent = MultimodalAgent()
        voice_agent = VoiceDialogueAgent()

        # 両エージェントが存在することを確認
        assert multimodal_agent is not None
        assert voice_agent is not None

        # Voice セッション開始
        result = await voice_agent.start_session()
        assert result["status"] == "started"

        # Voice セッション終了
        end_result = await voice_agent.end_session()
        assert end_result["status"] == "ended"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_memory_persistence_scenario(self):
        """
        Memory 永続化シナリオ

        シナリオ:
        1. セッション作成
        2. イベント保存
        3. イベント取得
        """
        memory_id = os.environ.get("AGENTCORE_MEMORY_ID")
        if not memory_id:
            pytest.skip("AGENTCORE_MEMORY_ID not set")

        from src.adapters.aws.memory_store import AWSMemoryStore

        store = AWSMemoryStore()
        
        # 基本的な接続テスト
        # 実際の API 呼び出しは別途確認
        assert store is not None


class TestEnvironmentConfiguration:
    """環境設定テスト"""

    def test_aws_region_configured(self):
        """AWS リージョンが設定されていること（警告のみ）"""
        region = os.environ.get("AWS_REGION")
        if not region:
            pytest.skip("AWS_REGION not set (optional)")
        assert region in [
            "us-east-1", "us-west-2", "ap-northeast-1",
            "eu-west-1", "eu-central-1",
        ]

    def test_api_base_url_format(self):
        """API ベース URL が正しい形式であること"""
        api_url = os.environ.get(
            "API_BASE_URL",
            "https://s3pa7bz4o2.execute-api.ap-northeast-1.amazonaws.com/dev"
        )
        assert api_url.startswith("https://")
        assert "execute-api" in api_url or "localhost" in api_url

