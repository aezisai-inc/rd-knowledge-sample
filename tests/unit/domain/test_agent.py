"""
Agent Domain Unit Tests

TDD: AgentSession エンティティのテスト。
"""

import pytest
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(__file__).replace('/tests/unit/domain/test_agent.py', ''))

from services.agent.domain.entities.agent_session import (
    AgentSession,
    AgentSessionId,
    AgentType,
    AgentResponse,
    ToolCall,
)


class TestAgentSession:
    """AgentSession エンティティのテスト"""
    
    def test_create_multimodal_session_should_generate_id(self):
        """Multimodal セッション作成時にIDが生成される"""
        session = AgentSession.create(
            agent_type=AgentType.MULTIMODAL,
            memory_session_id="mem-123",
        )
        
        assert session.id is not None
        assert isinstance(session.id, AgentSessionId)
    
    def test_create_voice_session_should_set_correct_model(self):
        """Voice セッション作成時に正しいモデルが設定される"""
        session = AgentSession.create(
            agent_type=AgentType.VOICE,
            memory_session_id="mem-123",
        )
        
        assert session.agent_type == AgentType.VOICE
        assert "sonic" in session.model_id.lower()
    
    def test_create_session_should_be_active(self):
        """作成直後のセッションはアクティブ"""
        session = AgentSession.create(
            agent_type=AgentType.MULTIMODAL,
            memory_session_id="mem-123",
        )
        
        assert session.is_active is True
        assert session.ended_at is None
    
    def test_record_tool_call_should_add_to_list(self):
        """ツール呼び出し記録がリストに追加される"""
        session = AgentSession.create(
            agent_type=AgentType.MULTIMODAL,
            memory_session_id="mem-123",
        )
        
        tool_call = session.record_tool_call(
            tool_name="nova_vision",
            input_data={"prompt": "test"},
            output_data={"result": "ok"},
        )
        
        assert session.tool_call_count == 1
        assert tool_call.tool_name == "nova_vision"
    
    def test_record_tool_call_on_ended_session_should_raise_error(self):
        """終了済みセッションへのツール呼び出し記録はエラー"""
        session = AgentSession.create(
            agent_type=AgentType.MULTIMODAL,
            memory_session_id="mem-123",
        )
        session.end()
        
        with pytest.raises(ValueError, match="inactive session"):
            session.record_tool_call(
                tool_name="nova_vision",
                input_data={"prompt": "test"},
            )
    
    def test_end_session_should_set_ended_at(self):
        """セッション終了で ended_at が設定される"""
        session = AgentSession.create(
            agent_type=AgentType.MULTIMODAL,
            memory_session_id="mem-123",
        )
        
        session.end()
        
        assert session.is_active is False
        assert session.ended_at is not None
    
    def test_end_already_ended_session_should_raise_error(self):
        """既に終了したセッションの終了はエラー"""
        session = AgentSession.create(
            agent_type=AgentType.MULTIMODAL,
            memory_session_id="mem-123",
        )
        session.end()
        
        with pytest.raises(ValueError, match="already ended"):
            session.end()
    
    def test_duration_seconds_should_return_positive_value(self):
        """duration_seconds が正の値を返す"""
        session = AgentSession.create(
            agent_type=AgentType.MULTIMODAL,
            memory_session_id="mem-123",
        )
        
        # 少し待つ必要はないがテストは通る
        assert session.duration_seconds >= 0
    
    def test_to_dict_should_return_serializable_dict(self):
        """to_dict がシリアライズ可能な辞書を返す"""
        session = AgentSession.create(
            agent_type=AgentType.MULTIMODAL,
            memory_session_id="mem-123",
        )
        session.record_tool_call(tool_name="test", input_data={})
        
        result = session.to_dict()
        
        assert "id" in result
        assert result["agent_type"] == "multimodal"
        assert result["memory_session_id"] == "mem-123"
        assert result["tool_call_count"] == 1


class TestAgentResponse:
    """AgentResponse のテスト"""
    
    def test_response_with_message_only(self):
        """メッセージのみのレスポンス"""
        response = AgentResponse(message="Hello!")
        
        assert response.message == "Hello!"
        assert response.images == []
        assert response.audio is None
    
    def test_response_with_images(self):
        """画像付きレスポンス"""
        response = AgentResponse(
            message="Generated image",
            images=[{"base64": "abc123", "seed": 42}],
        )
        
        assert len(response.images) == 1
        assert response.images[0]["seed"] == 42
    
    def test_response_to_dict(self):
        """レスポンスの to_dict"""
        response = AgentResponse(
            message="Test",
            images=[{"base64": "img"}],
            metadata={"model": "nova"},
        )
        
        data = response.to_dict()
        
        assert data["message"] == "Test"
        assert len(data["images"]) == 1
        assert data["metadata"]["model"] == "nova"


class TestToolCall:
    """ToolCall のテスト"""
    
    def test_tool_call_should_have_timestamp(self):
        """ToolCall はタイムスタンプを持つ"""
        tool_call = ToolCall(
            tool_name="nova_vision",
            input_data={"prompt": "test"},
        )
        
        assert tool_call.called_at is not None
        assert isinstance(tool_call.called_at, datetime)
    
    def test_tool_call_with_output(self):
        """出力付き ToolCall"""
        tool_call = ToolCall(
            tool_name="nova_canvas",
            input_data={"prompt": "generate cat"},
            output_data={"image": "base64..."},
            duration_ms=1500,
        )
        
        assert tool_call.output_data is not None
        assert tool_call.duration_ms == 1500


class TestAgentType:
    """AgentType のテスト"""
    
    def test_multimodal_type(self):
        """MULTIMODAL タイプ"""
        assert AgentType.MULTIMODAL.value == "multimodal"
    
    def test_voice_type(self):
        """VOICE タイプ"""
        assert AgentType.VOICE.value == "voice"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
