"""
E2E Test Configuration

環境変数:
- GRAPHQL_ENDPOINT: AppSync GraphQL エンドポイント
- GRAPHQL_API_KEY: AppSync API Key
- SKIP_E2E_TESTS: E2E テストをスキップ（sandbox未起動時）
"""

import os
import pytest
import httpx

# E2E テスト用の設定
GRAPHQL_ENDPOINT = os.getenv(
    "GRAPHQL_ENDPOINT",
    "https://xume65igfnemxeu3lwjorup3de.appsync-api.ap-northeast-1.amazonaws.com/graphql"
)
GRAPHQL_API_KEY = os.getenv(
    "GRAPHQL_API_KEY",
    "da2-djxjfyzfgbekpfwr74ajscj464"
)
SKIP_E2E = os.getenv("SKIP_E2E_TESTS", "false").lower() == "true"


def is_api_available() -> bool:
    """API が利用可能かチェック"""
    if SKIP_E2E:
        return False
    try:
        response = httpx.post(
            GRAPHQL_ENDPOINT,
            json={"query": "{ __typename }"},
            headers={
                "Content-Type": "application/json",
                "x-api-key": GRAPHQL_API_KEY,
            },
            timeout=5.0,
        )
        return response.status_code == 200
    except Exception:
        return False


# API 利用可能性をセッションスコープでキャッシュ
_api_available = None


def check_api_available():
    global _api_available
    if _api_available is None:
        _api_available = is_api_available()
    return _api_available


skip_if_api_unavailable = pytest.mark.skipif(
    not check_api_available(),
    reason="GraphQL API is not available (sandbox may not be running)"
)


class GraphQLClient:
    """Simple GraphQL client for E2E tests"""
    
    def __init__(self, endpoint: str = GRAPHQL_ENDPOINT, api_key: str = GRAPHQL_API_KEY):
        self.endpoint = endpoint
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)
    
    def execute(self, query: str, variables: dict = None) -> dict:
        """Execute GraphQL query/mutation"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        response = self.client.post(
            self.endpoint,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
            },
        )
        response.raise_for_status()
        return response.json()
    
    def close(self):
        self.client.close()


@pytest.fixture(scope="session")
def graphql_client():
    """GraphQL client fixture"""
    client = GraphQLClient()
    yield client
    client.close()


@pytest.fixture(scope="function")
def test_session_id():
    """Generate unique test session ID"""
    import uuid
    return f"test-session-{uuid.uuid4().hex[:8]}"
