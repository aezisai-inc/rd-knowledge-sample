"""
05_agentcore_memory.py

Amazon Bedrock AgentCore Memory を使用するサンプル。
エピソード記憶・会話履歴・洞察をマネージドサービスで管理。

使用API:
- bedrock-agentcore-control: Memory作成・管理（コントロールプレーン）
- bedrock-agentcore: イベント作成・検索（データプレーン）

参考:
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/aws-sdk-memory.html

MEMORY_ARCHITECTURE_DESIGN.md との関連:
- Short-term Memory: セッション中のコンテキスト保持
- Long-term Memory (Episodic): 過去のインタラクション記録
- Long-term Memory (Semantic): 学習した事実・知識
- Long-term Memory (Reflections): エピソードから抽出した洞察
"""

import json
import time
import boto3
from datetime import datetime

# Configuration
REGION = "us-east-1"  # AgentCore Memory available region
MEMORY_NAME = f"learning-coach-memory-{datetime.now().strftime('%Y%m%d%H%M')}"


def check_agentcore_clients():
    """
    AgentCore クライアントの利用可否を確認
    
    2つのクライアントが必要:
    - bedrock-agentcore-control: コントロールプレーン（Memory作成等）
    - bedrock-agentcore: データプレーン（イベント操作等）
    """
    print("=" * 60)
    print("AgentCore Memory Client Check")
    print("=" * 60)
    
    results = {}
    
    # Control Plane Client
    try:
        control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
        print("✅ bedrock-agentcore-control client created")
        
        # 利用可能なメソッドを確認
        control_methods = [
            "create_memory",
            "delete_memory",
            "get_memory",
            "list_memories",
            "update_memory",
        ]
        print("   Control plane methods:")
        for method in control_methods:
            if hasattr(control_client, method):
                print(f"     ✅ {method}")
            else:
                print(f"     ❌ {method}")
        
        results["control"] = True
    except Exception as e:
        print(f"❌ bedrock-agentcore-control client failed: {e}")
        results["control"] = False
    
    # Data Plane Client
    try:
        data_client = boto3.client("bedrock-agentcore", region_name=REGION)
        print("\n✅ bedrock-agentcore client created")
        
        # 利用可能なメソッドを確認
        data_methods = [
            "create_event",
            "get_event",
            "list_events",
            "list_sessions",
            "retrieve_memory_records",
            "get_memory_record",
            "list_memory_records",
        ]
        print("   Data plane methods:")
        for method in data_methods:
            if hasattr(data_client, method):
                print(f"     ✅ {method}")
            else:
                print(f"     ❌ {method}")
        
        results["data"] = True
    except Exception as e:
        print(f"❌ bedrock-agentcore client failed: {e}")
        results["data"] = False
    
    return results


def create_clients():
    """AgentCore クライアントを作成"""
    control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    data_client = boto3.client("bedrock-agentcore", region_name=REGION)
    return control_client, data_client


def step1_create_short_term_memory(control_client):
    """
    Step 1: Short-term Memory のみの Memory を作成
    
    Short-term Memory:
    - セッション中の会話コンテキストを保持
    - eventExpiryDuration で保持期間を設定（日数）
    - Long-term strategy なしの場合、イベントは自動で消える
    """
    print(f"\n=== Step 1: Create Short-term Memory ===")
    
    try:
        response = control_client.create_memory(
            name=f"{MEMORY_NAME}-short",
            description="Learning Coach - Short-term memory for session context",
            eventExpiryDuration=7  # 7日間保持
        )
        
        memory_id = response["memory"]["id"]
        print(f"✅ Short-term Memory created: {memory_id}")
        print(f"   Name: {response['memory']['name']}")
        print(f"   Event expiry: {response['memory']['eventExpiryDuration']} days")
        
        return memory_id
    except Exception as e:
        print(f"❌ Failed to create short-term memory: {e}")
        return None


def step2_create_long_term_memory(control_client):
    """
    Step 2: Long-term Memory 付きの Memory を作成
    
    Long-term Memory Strategies:
    - summaryMemoryStrategy: 会話の要約を抽出
    - userPreferenceMemoryStrategy: ユーザーの好み・傾向を抽出
    - semanticMemoryStrategy: 事実・知識を抽出
    
    これが MEMORY_ARCHITECTURE_DESIGN.md で説明している
    Episodic / Semantic / Reflections に対応
    """
    print(f"\n=== Step 2: Create Long-term Memory with Strategies ===")
    
    try:
        response = control_client.create_memory(
            name=f"{MEMORY_NAME}-long",
            description="Learning Coach - Comprehensive memory with long-term extraction",
            eventExpiryDuration=90,  # 90日間保持
            memoryStrategies=[
                # 📝 Session Summary - 会話の要約（Episodic相当）
                {
                    "summaryMemoryStrategy": {
                        "name": "SessionSummarizer",
                        "namespaces": ["/summaries/{actorId}/{sessionId}"]
                    }
                },
                # 💡 User Preference - ユーザーの好み（Reflections相当）
                {
                    "userPreferenceMemoryStrategy": {
                        "name": "PreferenceLearner",
                        "namespaces": ["/preferences/{actorId}"]
                    }
                },
                # 🧠 Semantic - 事実・知識（Semantic相当）
                {
                    "semanticMemoryStrategy": {
                        "name": "FactExtractor",
                        "namespaces": ["/facts/{actorId}"]
                    }
                }
            ]
        )
        
        memory_id = response["memory"]["id"]
        print(f"✅ Long-term Memory created: {memory_id}")
        print(f"   Name: {response['memory']['name']}")
        print(f"   Strategies: {len(response['memory'].get('memoryStrategies', []))} configured")
        
        return memory_id
    except Exception as e:
        print(f"❌ Failed to create long-term memory: {e}")
        return None


def step3_store_conversation_event(data_client, memory_id: str, actor_id: str, session_id: str):
    """
    Step 3: 会話イベントを保存
    
    イベントには複数の会話ターンを含めることができる。
    これが MEMORY_ARCHITECTURE_DESIGN.md の store_episodic に対応。
    """
    print(f"\n=== Step 3: Store Conversation Event ===")
    
    try:
        # 学習コーチングの会話例
        response = data_client.create_event(
            memoryId=memory_id,
            actorId=actor_id,
            sessionId=session_id,
            eventTimestamp=datetime.now(),
            payload=[
                {
                    "conversational": {
                        "content": {"text": "Pythonのループ処理を学びたいです"},
                        "role": "USER"
                    }
                },
                {
                    "conversational": {
                        "content": {"text": "Pythonのループ処理ですね！for文とwhile文がありますが、どちらから始めましょうか？"},
                        "role": "ASSISTANT"
                    }
                },
                {
                    "conversational": {
                        "content": {"text": "for文から教えてください。実は配列の処理が苦手なんです"},
                        "role": "USER"
                    }
                },
                {
                    "conversational": {
                        "content": {"text": "わかりました！for文は配列（リスト）を順番に処理するのに最適です。まずは簡単な例から始めましょう。"},
                        "role": "ASSISTANT"
                    }
                }
            ]
        )
        
        event_id = response["event"]["id"]
        print(f"✅ Event created: {event_id}")
        print(f"   Actor: {actor_id}")
        print(f"   Session: {session_id}")
        
        return event_id
    except Exception as e:
        print(f"❌ Failed to create event: {e}")
        return None


def step4_retrieve_short_term_context(data_client, memory_id: str, actor_id: str, session_id: str):
    """
    Step 4: Short-term Memory（セッション履歴）を取得
    
    現在のセッションの会話履歴を取得。
    """
    print(f"\n=== Step 4: Retrieve Short-term Context ===")
    
    try:
        # セッション内のイベントを取得
        response = data_client.list_events(
            memoryId=memory_id,
            actorId=actor_id,
            sessionId=session_id
        )
        
        events = response.get("events", [])
        print(f"✅ Retrieved {len(events)} events in session")
        
        for event in events:
            print(f"   - Event: {event.get('id', 'N/A')}")
        
        return events
    except Exception as e:
        print(f"❌ Failed to retrieve events: {e}")
        return []


def step5_retrieve_long_term_memory(data_client, memory_id: str, actor_id: str, query: str):
    """
    Step 5: Long-term Memory を検索
    
    セマンティック検索で過去のインタラクションから関連記憶を取得。
    これが MEMORY_ARCHITECTURE_DESIGN.md の search_episodic に対応。
    """
    print(f"\n=== Step 5: Retrieve Long-term Memory ===")
    print(f"Query: {query}")
    
    try:
        response = data_client.retrieve_memory_records(
            memoryId=memory_id,
            actorId=actor_id,
            query=query,
            maxResults=5
        )
        
        records = response.get("memoryRecords", [])
        print(f"\n✅ Retrieved {len(records)} memory records")
        
        for i, record in enumerate(records, 1):
            print(f"\n  {i}. Namespace: {record.get('namespace', 'N/A')}")
            print(f"     Content: {record.get('content', {}).get('text', 'N/A')[:100]}...")
            print(f"     Score: {record.get('score', 'N/A')}")
        
        return records
    except Exception as e:
        print(f"❌ Failed to retrieve memory records: {e}")
        return []


def step6_list_memory_records_by_namespace(data_client, memory_id: str, namespace: str):
    """
    Step 6: 名前空間でメモリレコードを一覧取得
    
    特定の種類の記憶（要約、好み、事実）を一括取得。
    """
    print(f"\n=== Step 6: List Memory Records by Namespace ===")
    print(f"Namespace: {namespace}")
    
    try:
        response = data_client.list_memory_records(
            memoryId=memory_id,
            namespace=namespace
        )
        
        records = response.get("memoryRecords", [])
        print(f"✅ Found {len(records)} records in namespace")
        
        for record in records:
            print(f"   - {record.get('id', 'N/A')}: {record.get('content', {}).get('text', 'N/A')[:50]}...")
        
        return records
    except Exception as e:
        print(f"❌ Failed to list memory records: {e}")
        return []


def cleanup(control_client, memory_id: str):
    """クリーンアップ"""
    print(f"\n=== Cleanup ===")
    
    try:
        control_client.delete_memory(memoryId=memory_id)
        print(f"✅ Deleted memory: {memory_id}")
    except Exception as e:
        print(f"⚠️ Failed to delete memory: {e}")


def main():
    """
    メイン実行フロー
    
    AgentCore Memory の完全ワークフロー:
    1. クライアント確認
    2. Short-term Memory 作成
    3. Long-term Memory 作成（Strategies付き）
    4. 会話イベント保存
    5. Short-term Context 取得
    6. Long-term Memory 検索
    
    MEMORY_ARCHITECTURE_DESIGN.md で説明している設計が
    実際にどう実装されるかを示す。
    """
    print("=" * 60)
    print("Amazon Bedrock AgentCore Memory Sample")
    print("=" * 60)
    
    # Step 0: クライアント確認
    results = check_agentcore_clients()
    
    if not results.get("control") or not results.get("data"):
        print("\n❌ AgentCore clients not available")
        print("   Make sure boto3 is up to date: pip install boto3 --upgrade")
        return
    
    print("\n" + "=" * 60)
    print("AgentCore Memory Operations")
    print("=" * 60)
    
    # クライアント作成
    control_client, data_client = create_clients()
    
    # 以下は AWS アカウントと適切な権限がある場合に実行可能
    # コメントアウトを解除して実行
    
    # actor_id = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    # session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Step 1: Short-term Memory 作成
    # short_memory_id = step1_create_short_term_memory(control_client)
    
    # Step 2: Long-term Memory 作成
    # long_memory_id = step2_create_long_term_memory(control_client)
    
    # Long-term Memory がアクティブになるまで待機が必要
    # time.sleep(30)
    
    # Step 3: 会話イベント保存
    # step3_store_conversation_event(data_client, long_memory_id, actor_id, session_id)
    
    # Step 4: Short-term Context 取得
    # step4_retrieve_short_term_context(data_client, long_memory_id, actor_id, session_id)
    
    # Long-term Memory 抽出には時間がかかる（非同期処理）
    # time.sleep(60)
    
    # Step 5: Long-term Memory 検索
    # step5_retrieve_long_term_memory(data_client, long_memory_id, actor_id, "Pythonの学習")
    
    # Step 6: 名前空間でメモリレコード一覧
    # step6_list_memory_records_by_namespace(data_client, long_memory_id, f"/preferences/{actor_id}")
    
    # クリーンアップ（オプション）
    # cleanup(control_client, short_memory_id)
    # cleanup(control_client, long_memory_id)
    
    print("\n⚠️ このサンプルを完全に実行するには:")
    print("1. AWS アカウントと適切な IAM 権限が必要")
    print("2. AgentCore Memory が利用可能なリージョン (us-east-1 等)")
    print("3. コメントアウトを解除して実行")
    
    print("\n📝 MEMORY_ARCHITECTURE_DESIGN.md との対応:")
    print("   - Short-term Memory → store_short_term()")
    print("   - Episodic Memory → create_event() + summaryMemoryStrategy")
    print("   - Semantic Memory → create_event() + semanticMemoryStrategy")
    print("   - Reflections → create_event() + userPreferenceMemoryStrategy")
    print("   - search_episodic() → retrieve_memory_records()")
    
    print("\n" + "=" * 60)
    print("✅ AgentCore Memory Sample Completed")
    print("=" * 60)


if __name__ == "__main__":
    main()

