"""
00_verify_availability.py

boto3 で s3vectors クライアントが利用可能か検証するスクリプト。
S3 Vectors はプレビュー機能のため、boto3 バージョンや SDK によって利用可否が異なる。

実行方法:
    uv venv && source .venv/bin/activate
    uv pip install boto3
    python src/00_verify_availability.py
"""

import sys


def check_boto3_version():
    """boto3 バージョンを確認"""
    import boto3
    import botocore
    
    print("=" * 60)
    print("Environment Check")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"boto3 version: {boto3.__version__}")
    print(f"botocore version: {botocore.__version__}")
    
    return boto3.__version__, botocore.__version__


def check_s3vectors_client():
    """s3vectors クライアントが作成可能か確認"""
    import boto3
    
    print("\n" + "=" * 60)
    print("S3 Vectors Client Check")
    print("=" * 60)
    
    try:
        s3vectors = boto3.client("s3vectors", region_name="us-west-2")
        print("✅ s3vectors client created successfully")
        
        # 利用可能なメソッドを確認
        methods = [m for m in dir(s3vectors) if not m.startswith('_') and callable(getattr(s3vectors, m))]
        print(f"   Available methods: {len(methods)}")
        
        # 主要メソッドの存在確認
        # 注意: boto3 では create_vector_index ではなく create_index を使用
        expected_methods = [
            "create_vector_bucket",
            "delete_vector_bucket",
            "get_vector_bucket",
            "list_vector_buckets",
            "create_index",      # ← create_vector_index ではない
            "delete_index",      # ← delete_vector_index ではない
            "get_index",         # ← get_vector_index ではない
            "list_indexes",      # ← list_vector_indexes ではない
            "put_vectors",
            "get_vectors",
            "delete_vectors",
            "query_vectors",
        ]
        
        print("\n   Expected methods:")
        for method in expected_methods:
            if hasattr(s3vectors, method):
                print(f"     ✅ {method}")
            else:
                print(f"     ❌ {method} (not found)")
        
        return True
    except Exception as e:
        print(f"❌ s3vectors client creation failed: {e}")
        print("\n   Possible reasons:")
        print("   1. boto3 version too old (need >= 1.35.0)")
        print("   2. S3 Vectors not available in the region")
        print("   3. AWS credentials not configured")
        return False


def check_bedrock_agent_client():
    """bedrock-agent クライアントを確認（比較用）"""
    import boto3
    
    print("\n" + "=" * 60)
    print("Bedrock Agent Client Check (for comparison)")
    print("=" * 60)
    
    try:
        bedrock_agent = boto3.client("bedrock-agent", region_name="us-west-2")
        print("✅ bedrock-agent client created successfully")
        
        # KB関連メソッドの確認
        kb_methods = [
            "create_knowledge_base",
            "delete_knowledge_base",
            "get_knowledge_base",
            "list_knowledge_bases",
            "create_data_source",
            "start_ingestion_job",
        ]
        
        print("\n   Knowledge Base methods:")
        for method in kb_methods:
            if hasattr(bedrock_agent, method):
                print(f"     ✅ {method}")
            else:
                print(f"     ❌ {method}")
        
        return True
    except Exception as e:
        print(f"❌ bedrock-agent client creation failed: {e}")
        return False


def check_bedrock_runtime_client():
    """bedrock-agent-runtime クライアントを確認"""
    import boto3
    
    print("\n" + "=" * 60)
    print("Bedrock Agent Runtime Client Check")
    print("=" * 60)
    
    try:
        bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name="us-west-2")
        print("✅ bedrock-agent-runtime client created successfully")
        
        # RAG関連メソッドの確認
        rag_methods = [
            "retrieve",
            "retrieve_and_generate",
        ]
        
        print("\n   RAG methods:")
        for method in rag_methods:
            if hasattr(bedrock_runtime, method):
                print(f"     ✅ {method}")
            else:
                print(f"     ❌ {method}")
        
        return True
    except Exception as e:
        print(f"❌ bedrock-agent-runtime client creation failed: {e}")
        return False


def check_agentcore_memory_clients():
    """AgentCore Memory クライアントを確認"""
    import boto3
    
    print("\n" + "=" * 60)
    print("AgentCore Memory Client Check")
    print("=" * 60)
    
    control_ok = False
    data_ok = False
    
    # Control Plane Client
    try:
        control_client = boto3.client("bedrock-agentcore-control", region_name="us-east-1")
        print("✅ bedrock-agentcore-control client created successfully")
        
        control_methods = [
            "create_memory",
            "delete_memory",
            "get_memory",
            "list_memories",
            "update_memory",
        ]
        
        print("\n   Control plane methods:")
        for method in control_methods:
            if hasattr(control_client, method):
                print(f"     ✅ {method}")
            else:
                print(f"     ❌ {method}")
        
        control_ok = True
    except Exception as e:
        print(f"❌ bedrock-agentcore-control client creation failed: {e}")
    
    # Data Plane Client
    try:
        data_client = boto3.client("bedrock-agentcore", region_name="us-east-1")
        print("\n✅ bedrock-agentcore client created successfully")
        
        data_methods = [
            "create_event",
            "get_event",
            "list_events",
            "list_sessions",
            "retrieve_memory_records",
            "get_memory_record",
            "list_memory_records",
        ]
        
        print("\n   Data plane methods:")
        for method in data_methods:
            if hasattr(data_client, method):
                print(f"     ✅ {method}")
            else:
                print(f"     ❌ {method}")
        
        data_ok = True
    except Exception as e:
        print(f"❌ bedrock-agentcore client creation failed: {e}")
    
    return control_ok and data_ok


def list_available_s3vectors_operations():
    """S3 Vectors で利用可能な操作を一覧"""
    import boto3
    
    print("\n" + "=" * 60)
    print("S3 Vectors Available Operations")
    print("=" * 60)
    
    try:
        s3vectors = boto3.client("s3vectors", region_name="us-west-2")
        
        # サービスモデルからオペレーションを取得
        service_model = s3vectors._service_model
        operation_names = service_model.operation_names
        
        print(f"Total operations: {len(operation_names)}")
        for op in sorted(operation_names):
            print(f"  - {op}")
        
    except Exception as e:
        print(f"❌ Could not list operations: {e}")


def main():
    print("=" * 60)
    print("S3 Vectors & Bedrock KB & AgentCore Memory Verification")
    print("=" * 60)
    
    # 1. バージョン確認
    boto3_ver, botocore_ver = check_boto3_version()
    
    # 2. s3vectors クライアント確認
    s3vectors_ok = check_s3vectors_client()
    
    # 3. bedrock-agent クライアント確認
    bedrock_agent_ok = check_bedrock_agent_client()
    
    # 4. bedrock-agent-runtime クライアント確認
    bedrock_runtime_ok = check_bedrock_runtime_client()
    
    # 5. AgentCore Memory クライアント確認
    agentcore_memory_ok = check_agentcore_memory_clients()
    
    # 6. S3 Vectors オペレーション一覧
    if s3vectors_ok:
        list_available_s3vectors_operations()
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"S3 Vectors client:          {'✅ Available' if s3vectors_ok else '❌ Not available'}")
    print(f"Bedrock Agent client:       {'✅ Available' if bedrock_agent_ok else '❌ Not available'}")
    print(f"Bedrock Agent Runtime:      {'✅ Available' if bedrock_runtime_ok else '❌ Not available'}")
    print(f"AgentCore Memory clients:   {'✅ Available' if agentcore_memory_ok else '❌ Not available'}")
    
    if s3vectors_ok:
        print("\n📌 Note: S3 Vectors is in PREVIEW (as of Dec 2024)")
        print("   Available regions: us-east-1, us-east-2, us-west-2, eu-central-1, ap-southeast-2")
    
    if agentcore_memory_ok:
        print("\n📌 Note: AgentCore Memory is available")
        print("   Primary region: us-east-1")
    
    if not s3vectors_ok or not agentcore_memory_ok:
        print("\n💡 To update boto3:")
        print("   uv pip install boto3 --upgrade")
        print("   Make sure you're using the latest boto3 version")


if __name__ == "__main__":
    main()

