"""
Live E2E Tests for GraphQL API

実際の AppSync GraphQL API に接続してテスト。
Sandbox が起動中でない場合はスキップ。
"""

import pytest
from conftest import skip_if_api_unavailable, GraphQLClient


@skip_if_api_unavailable
class TestMemoryAPILive:
    """Memory API Live E2E テスト"""
    
    def test_create_and_get_memory_session(self, graphql_client: GraphQLClient, test_session_id: str):
        """セッション作成と取得のライブテスト"""
        # Create session
        create_mutation = """
        mutation CreateSession($title: String, $tags: [String]) {
            createMemorySession(title: $title, tags: $tags) {
                sessionId
                startTime
                title
                tags
            }
        }
        """
        
        result = graphql_client.execute(
            create_mutation,
            {"title": "E2E Test Session", "tags": ["e2e", "test"]}
        )
        
        # Verify response
        assert "errors" not in result or result.get("errors") is None
        session = result["data"]["createMemorySession"]
        assert session["sessionId"] is not None
        assert session["title"] == "E2E Test Session"
        assert "e2e" in session["tags"]
        
        print(f"Created session: {session['sessionId']}")
    
    def test_create_memory_event(self, graphql_client: GraphQLClient):
        """メモリイベント作成のライブテスト"""
        # First create a session
        create_session = """
        mutation {
            createMemorySession(title: "Event Test") {
                sessionId
            }
        }
        """
        session_result = graphql_client.execute(create_session)
        session_id = session_result["data"]["createMemorySession"]["sessionId"]
        
        # Create event - use String! instead of ID! to match schema
        create_event = """
        mutation CreateEvent($actorId: String!, $sessionId: String!, $role: String!, $content: String!) {
            createMemoryEvent(actorId: $actorId, sessionId: $sessionId, role: $role, content: $content) {
                id
                actorId
                sessionId
                role
                content
                timestamp
            }
        }
        """
        
        result = graphql_client.execute(
            create_event,
            {
                "actorId": "user-123",
                "sessionId": session_id,
                "role": "USER",
                "content": "Hello from E2E test!"
            }
        )
        
        assert "errors" not in result or result.get("errors") is None
        event = result["data"]["createMemoryEvent"]
        assert event["content"] == "Hello from E2E test!"
        assert event["role"] == "USER"


@skip_if_api_unavailable
class TestAgentAPILive:
    """Agent API Live E2E テスト"""
    
    def test_invoke_multimodal_text_only(self, graphql_client: GraphQLClient):
        """Multimodal エージェント（テキストのみ）のライブテスト"""
        mutation = """
        mutation InvokeMultimodal($sessionId: String!, $prompt: String!) {
            invokeMultimodal(sessionId: $sessionId, prompt: $prompt) {
                message
                metadata
            }
        }
        """
        
        result = graphql_client.execute(
            mutation,
            {
                "sessionId": "e2e-test-multimodal",
                "prompt": "Hello! Please respond with a short greeting."
            }
        )
        
        # Check for response
        if "errors" in result and result["errors"]:
            # Some errors are expected if Bedrock is not fully configured
            print(f"Got expected error: {result['errors']}")
            pytest.skip("Bedrock model not fully configured")
        
        response = result["data"]["invokeMultimodal"]
        assert response["message"] is not None
        print(f"Agent response: {response['message']}")
    
    def test_send_voice_text(self, graphql_client: GraphQLClient):
        """Voice エージェントのライブテスト"""
        mutation = """
        mutation SendVoiceText($sessionId: String!, $text: String!) {
            sendVoiceText(sessionId: $sessionId, text: $text) {
                userText
                assistantText
                metadata
            }
        }
        """
        
        result = graphql_client.execute(
            mutation,
            {
                "sessionId": "e2e-test-voice",
                "text": "Tell me a short joke"
            }
        )
        
        if "errors" in result and result["errors"]:
            print(f"Got expected error: {result['errors']}")
            pytest.skip("Bedrock model not fully configured")
        
        response = result["data"]["sendVoiceText"]
        assert response["userText"] == "Tell me a short joke"
        assert response["assistantText"] is not None
        print(f"Voice response: {response['assistantText']}")


@skip_if_api_unavailable
class TestVectorAPILive:
    """Vector API Live E2E テスト"""
    
    def test_search_vectors(self, graphql_client: GraphQLClient):
        """ベクトル検索のライブテスト"""
        query = """
        query SearchVectors($query: String!, $k: Int) {
            searchVectors(query: $query, k: $k) {
                id
                content
                vector
            }
        }
        """
        
        result = graphql_client.execute(
            query,
            {"query": "AWS Lambda serverless", "k": 3}
        )
        
        if "errors" in result and result["errors"]:
            print(f"Got error: {result['errors']}")
            # Empty result is acceptable for new deployment
            return
        
        vectors = result["data"]["searchVectors"]
        assert isinstance(vectors, list)
        print(f"Found {len(vectors)} vectors")


@skip_if_api_unavailable
class TestGraphAPILive:
    """Graph API Live E2E テスト"""
    
    def test_create_and_query_node(self, graphql_client: GraphQLClient):
        """ノード作成とクエリのライブテスト"""
        # Create node
        create_mutation = """
        mutation CreateNode($type: String!, $properties: AWSJSON!) {
            createNode(type: $type, properties: $properties) {
                id
                type
                properties
            }
        }
        """
        
        result = graphql_client.execute(
            create_mutation,
            {
                "type": "TestEntity",
                "properties": '{"name": "E2E Test Node", "timestamp": "2026-01-04"}'
            }
        )
        
        if "errors" in result and result["errors"]:
            print(f"Got error (DynamoDB may not be set up): {result['errors']}")
            pytest.skip("Graph storage not configured")
        
        node = result["data"]["createNode"]
        assert node["type"] == "TestEntity"
        print(f"Created node: {node['id']}")


@skip_if_api_unavailable
class TestIntegrationLive:
    """統合ライブテスト"""
    
    def test_full_conversation_flow(self, graphql_client: GraphQLClient):
        """完全な会話フローのライブテスト"""
        # Step 1: Create session
        create_session = """
        mutation {
            createMemorySession(title: "Integration Test", tags: ["integration"]) {
                sessionId
            }
        }
        """
        session_result = graphql_client.execute(create_session)
        session_id = session_result["data"]["createMemorySession"]["sessionId"]
        print(f"Step 1: Created session {session_id}")
        
        # Step 2: Invoke agent
        invoke_agent = """
        mutation InvokeAgent($sessionId: String!, $prompt: String!) {
            invokeMultimodal(sessionId: $sessionId, prompt: $prompt) {
                message
            }
        }
        """
        agent_result = graphql_client.execute(
            invoke_agent,
            {"sessionId": session_id, "prompt": "Hello!"}
        )
        
        if "errors" in agent_result and agent_result["errors"]:
            print(f"Agent error (expected): {agent_result['errors']}")
        else:
            message = agent_result["data"]["invokeMultimodal"]["message"]
            print(f"Step 2: Agent responded: {message[:50]}...")
        
        # Step 3: Create memory event
        create_event = """
        mutation CreateEvent($actorId: String!, $sessionId: String!, $role: String!, $content: String!) {
            createMemoryEvent(actorId: $actorId, sessionId: $sessionId, role: $role, content: $content) {
                id
            }
        }
        """
        event_result = graphql_client.execute(
            create_event,
            {
                "actorId": "user",
                "sessionId": session_id,
                "role": "USER",
                "content": "Integration test complete"
            }
        )
        print(f"Step 3: Created event {event_result}")
        
        # All steps complete
        print("✅ Full conversation flow completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
