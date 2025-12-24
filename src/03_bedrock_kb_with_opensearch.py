"""
03_bedrock_kb_with_opensearch.py

⚠️ WARNING: このファイルは学習・参照用サンプルです。直接実行しないでください。
============================================================================
OpenSearch Serverlessリソースを作成する場合は、必ずCDKを使用してください。
Boto3/CLIでの直接作成はトレーサビリティがなく、リソース削除漏れのリスクがあります。

CDK実装例: infrastructure/lib/opensearch-stack.ts
ガイドライン: .cursor/rules/triggers/infra/aws-resource-traceability.mdc
============================================================================

Bedrock Knowledge Bases を使用し、バックエンドに OpenSearch Serverless を指定するサンプル。
高頻度クエリ、ハイブリッド検索（セマンティック+キーワード）が必要な場合に適している。

使用API:
- bedrock-agent:CreateKnowledgeBase
- bedrock-agent:CreateDataSource
- bedrock-agent:StartIngestionJob
- bedrock-agent-runtime:Retrieve
- bedrock-agent-runtime:RetrieveAndGenerate

参考: 
- https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-opensearch.html
- https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html

比較:
- 01_s3_vectors_direct.py: S3 Vectors直接操作（低コスト、低レベルAPI）
- 02_bedrock_kb_with_s3vectors.py: Bedrock KB + S3 Vectors（低〜中コスト、マネージド）
- このファイル: Bedrock KB + OpenSearch（中〜高コスト、高性能、ハイブリッド検索）
"""

import json
import time
import boto3
from datetime import datetime

# Configuration
REGION = "us-west-2"
KNOWLEDGE_BASE_NAME = f"learning-coach-kb-opensearch-{datetime.now().strftime('%Y%m%d%H%M')}"
DATA_SOURCE_NAME = "educational-content-source"
S3_DATA_BUCKET = "your-data-source-bucket"  # 要変更: 教育コンテンツを格納したS3バケット
S3_DATA_PREFIX = "educational-content/"

# OpenSearch Serverless Configuration
COLLECTION_NAME = f"learning-coach-{datetime.now().strftime('%Y%m%d')}"
INDEX_NAME = "educational-content-index"

# Embedding model for Bedrock KB
EMBEDDING_MODEL_ARN = f"arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v2:0"

# For RetrieveAndGenerate
GENERATION_MODEL_ARN = f"arn:aws:bedrock:{REGION}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"


def create_clients():
    """
    必要なクライアントを作成
    
    - bedrock-agent: ビルドタイム操作
    - bedrock-agent-runtime: ランタイム操作
    - opensearchserverless: OpenSearch Serverless 管理
    """
    bedrock_agent = boto3.client("bedrock-agent", region_name=REGION)
    bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)
    aoss = boto3.client("opensearchserverless", region_name=REGION)
    return bedrock_agent, bedrock_runtime, aoss


def step0_create_opensearch_collection(aoss, account_id: str):
    """
    Step 0: OpenSearch Serverless Collection を作成
    
    OpenSearch Serverless は事前に Collection を作成する必要がある。
    Bedrock KB は既存の Collection を使用する。
    
    注意: 
    - Serverless は最低 2 OCU (約$100/月) のコストがかかる
    - Collection 作成には数分かかる
    """
    print(f"\n=== Step 0: Create OpenSearch Serverless Collection ===")
    
    # 1. Create encryption policy
    encryption_policy = {
        "Rules": [
            {
                "ResourceType": "collection",
                "Resource": [f"collection/{COLLECTION_NAME}"]
            }
        ],
        "AWSOwnedKey": True
    }
    
    try:
        aoss.create_security_policy(
            name=f"{COLLECTION_NAME}-encryption",
            type="encryption",
            policy=json.dumps(encryption_policy)
        )
        print(f"  ✅ Encryption policy created")
    except aoss.exceptions.ConflictException:
        print(f"  ⚠️ Encryption policy already exists")
    
    # 2. Create network policy
    network_policy = [
        {
            "Description": "Public access for Bedrock KB",
            "Rules": [
                {
                    "ResourceType": "collection",
                    "Resource": [f"collection/{COLLECTION_NAME}"]
                },
                {
                    "ResourceType": "dashboard",
                    "Resource": [f"collection/{COLLECTION_NAME}"]
                }
            ],
            "AllowFromPublic": True
        }
    ]
    
    try:
        aoss.create_security_policy(
            name=f"{COLLECTION_NAME}-network",
            type="network",
            policy=json.dumps(network_policy)
        )
        print(f"  ✅ Network policy created")
    except aoss.exceptions.ConflictException:
        print(f"  ⚠️ Network policy already exists")
    
    # 3. Create data access policy for Bedrock
    data_access_policy = [
        {
            "Description": "Bedrock KB access",
            "Rules": [
                {
                    "ResourceType": "index",
                    "Resource": [f"index/{COLLECTION_NAME}/*"],
                    "Permission": [
                        "aoss:CreateIndex",
                        "aoss:UpdateIndex",
                        "aoss:DeleteIndex",
                        "aoss:DescribeIndex",
                        "aoss:ReadDocument",
                        "aoss:WriteDocument"
                    ]
                },
                {
                    "ResourceType": "collection",
                    "Resource": [f"collection/{COLLECTION_NAME}"],
                    "Permission": [
                        "aoss:CreateCollectionItems",
                        "aoss:DescribeCollectionItems",
                        "aoss:UpdateCollectionItems"
                    ]
                }
            ],
            "Principal": [
                f"arn:aws:iam::{account_id}:root",
                f"arn:aws:iam::{account_id}:role/AmazonBedrockExecutionRoleForKnowledgeBase"
            ]
        }
    ]
    
    try:
        aoss.create_access_policy(
            name=f"{COLLECTION_NAME}-access",
            type="data",
            policy=json.dumps(data_access_policy)
        )
        print(f"  ✅ Data access policy created")
    except aoss.exceptions.ConflictException:
        print(f"  ⚠️ Data access policy already exists")
    
    # 4. Create collection
    try:
        response = aoss.create_collection(
            name=COLLECTION_NAME,
            type="VECTORSEARCH",
            description="OpenSearch Serverless collection for Learning Achievement Coach"
        )
        collection_id = response["createCollectionDetail"]["id"]
        print(f"  ✅ Collection created: {collection_id}")
        
        # Wait for collection to be active
        _wait_for_collection_active(aoss, collection_id)
        
        return collection_id
    except aoss.exceptions.ConflictException:
        print(f"  ⚠️ Collection already exists: {COLLECTION_NAME}")
        # Get existing collection
        response = aoss.batch_get_collection(names=[COLLECTION_NAME])
        return response["collectionDetails"][0]["id"]


def step1_create_knowledge_base_with_opensearch(bedrock_agent, role_arn: str, collection_arn: str):
    """
    Step 1: OpenSearch Serverless バックエンドで Knowledge Base を作成
    
    OpenSearch の利点:
    - ハイブリッド検索（セマンティック + キーワード）
    - 高速クエリレスポンス
    - 細かいフィルタリング
    - スケーラビリティ
    """
    print(f"\n=== Step 1: Create Knowledge Base with OpenSearch Backend ===")
    
    response = bedrock_agent.create_knowledge_base(
        name=KNOWLEDGE_BASE_NAME,
        description="Learning Achievement Coach - Educational Content KB (OpenSearch backend)",
        roleArn=role_arn,
        
        # Knowledge Base Configuration
        knowledgeBaseConfiguration={
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": EMBEDDING_MODEL_ARN,
                "embeddingModelConfiguration": {
                    "bedrockEmbeddingModelConfiguration": {
                        "dimensions": 1024
                    }
                }
            }
        },
        
        # Storage Configuration - OpenSearch Serverless
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
            "opensearchServerlessConfiguration": {
                "collectionArn": collection_arn,
                "vectorIndexName": INDEX_NAME,
                "fieldMapping": {
                    "vectorField": "embedding",
                    "textField": "text",
                    "metadataField": "metadata"
                }
            }
        }
    )
    
    kb_id = response["knowledgeBase"]["knowledgeBaseId"]
    print(f"✅ Knowledge Base created: {kb_id}")
    print(f"   Backend: OpenSearch Serverless")
    print(f"   Collection: {COLLECTION_NAME}")
    
    _wait_for_knowledge_base_active(bedrock_agent, kb_id)
    
    return kb_id


def step2_create_data_source(bedrock_agent, kb_id: str):
    """
    Step 2: S3 データソースを作成
    
    S3 Vectors バックエンドと同じ API。
    バックエンドが OpenSearch でもデータソース作成方法は同一。
    """
    print(f"\n=== Step 2: Create Data Source ===")
    
    response = bedrock_agent.create_data_source(
        knowledgeBaseId=kb_id,
        name=DATA_SOURCE_NAME,
        description="S3 bucket containing educational content",
        
        dataSourceConfiguration={
            "type": "S3",
            "s3Configuration": {
                "bucketArn": f"arn:aws:s3:::{S3_DATA_BUCKET}",
                "inclusionPrefixes": [S3_DATA_PREFIX]
            }
        },
        
        # Chunking strategy - Semantic chunking for better quality
        vectorIngestionConfiguration={
            "chunkingConfiguration": {
                "chunkingStrategy": "SEMANTIC",
                "semanticChunkingConfiguration": {
                    "maxTokens": 512,
                    "bufferSize": 0,
                    "breakpointPercentileThreshold": 95
                }
            }
        }
    )
    
    ds_id = response["dataSource"]["dataSourceId"]
    print(f"✅ Data Source created: {ds_id}")
    
    return ds_id


def step3_start_ingestion_job(bedrock_agent, kb_id: str, ds_id: str):
    """
    Step 3: データ取り込みジョブを開始
    
    OpenSearch Serverless へのインデックス作成が行われる。
    """
    print(f"\n=== Step 3: Start Ingestion Job ===")
    
    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id
    )
    
    job_id = response["ingestionJob"]["ingestionJobId"]
    print(f"✅ Ingestion Job started: {job_id}")
    
    _wait_for_ingestion_complete(bedrock_agent, kb_id, ds_id, job_id)
    
    return job_id


def step4_retrieve_with_hybrid_search(bedrock_runtime, kb_id: str, query: str, top_k: int = 5):
    """
    Step 4: Retrieve API - ハイブリッド検索
    
    OpenSearch バックエンドならではの機能:
    - セマンティック検索 + キーワード検索の組み合わせ
    - より精度の高い検索結果
    """
    print(f"\n=== Step 4: Retrieve with Hybrid Search ===")
    print(f"Query: {query}")
    
    response = bedrock_runtime.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={
            "text": query
        },
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": top_k,
                # OpenSearch specific: hybrid search
                "overrideSearchType": "HYBRID"  # or "SEMANTIC"
            }
        }
    )
    
    print(f"\nRetrieved {len(response['retrievalResults'])} chunks (Hybrid Search):")
    for i, result in enumerate(response["retrievalResults"], 1):
        content = result["content"]["text"][:100] + "..." if len(result["content"]["text"]) > 100 else result["content"]["text"]
        print(f"  {i}. Score: {result.get('score', 'N/A'):.4f}")
        print(f"     Content: {content}")
    
    return response


def step5_retrieve_with_filters(bedrock_runtime, kb_id: str, query: str):
    """
    Step 5: メタデータフィルタ付き検索
    
    OpenSearch の強力なフィルタリング機能を活用。
    """
    print(f"\n=== Step 5: Retrieve with Metadata Filters ===")
    print(f"Query: {query}")
    print(f"Filters: difficulty = 'beginner' AND category = 'programming'")
    
    response = bedrock_runtime.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={
            "text": query
        },
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 5,
                "overrideSearchType": "HYBRID",
                "filter": {
                    "andAll": [
                        {
                            "equals": {
                                "key": "difficulty",
                                "value": "beginner"
                            }
                        },
                        {
                            "equals": {
                                "key": "category",
                                "value": "programming"
                            }
                        }
                    ]
                }
            }
        }
    )
    
    print(f"\nFiltered Results:")
    for i, result in enumerate(response["retrievalResults"], 1):
        content = result["content"]["text"][:100] + "..."
        print(f"  {i}. Score: {result.get('score', 'N/A'):.4f}")
        print(f"     Content: {content}")
    
    return response


def step6_retrieve_and_generate(bedrock_runtime, kb_id: str, query: str):
    """
    Step 6: RetrieveAndGenerate - フルRAGフロー
    
    OpenSearch バックエンドでも同じ API で RAG を実行可能。
    """
    print(f"\n=== Step 6: RetrieveAndGenerate (Full RAG) ===")
    print(f"Query: {query}")
    
    response = bedrock_runtime.retrieve_and_generate(
        input={
            "text": query
        },
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": GENERATION_MODEL_ARN,
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults": 5,
                        "overrideSearchType": "HYBRID"
                    }
                },
                "generationConfiguration": {
                    "inferenceConfig": {
                        "textInferenceConfig": {
                            "maxTokens": 1024,
                            "temperature": 0.7
                        }
                    }
                }
            }
        }
    )
    
    print(f"\n📝 Generated Response:")
    print(response["output"]["text"])
    
    print(f"\n📚 Citations:")
    for citation in response.get("citations", []):
        for ref in citation.get("retrievedReferences", []):
            if "location" in ref:
                print(f"  - {ref['location'].get('s3Location', {}).get('uri', 'N/A')}")
    
    return response


def _wait_for_collection_active(aoss, collection_id: str, timeout: int = 300):
    """OpenSearch Collection が ACTIVE になるまで待機"""
    print("  Waiting for OpenSearch Collection to be active...")
    start = time.time()
    while time.time() - start < timeout:
        response = aoss.batch_get_collection(ids=[collection_id])
        if response["collectionDetails"]:
            status = response["collectionDetails"][0]["status"]
            if status == "ACTIVE":
                endpoint = response["collectionDetails"][0].get("collectionEndpoint", "N/A")
                print(f"  ✅ Collection is ACTIVE")
                print(f"     Endpoint: {endpoint}")
                return
            elif status == "FAILED":
                raise Exception(f"Collection creation failed")
        time.sleep(10)
    raise TimeoutError(f"Collection did not become active within {timeout} seconds")


def _wait_for_knowledge_base_active(bedrock_agent, kb_id: str, timeout: int = 300):
    """Knowledge Base が ACTIVE になるまで待機"""
    print("  Waiting for Knowledge Base to be active...")
    start = time.time()
    while time.time() - start < timeout:
        response = bedrock_agent.get_knowledge_base(knowledgeBaseId=kb_id)
        status = response["knowledgeBase"]["status"]
        if status == "ACTIVE":
            print(f"  ✅ Knowledge Base is ACTIVE")
            return
        elif status == "FAILED":
            raise Exception(f"Knowledge Base creation failed: {response}")
        time.sleep(5)
    raise TimeoutError(f"Knowledge Base did not become active within {timeout} seconds")


def _wait_for_ingestion_complete(bedrock_agent, kb_id: str, ds_id: str, job_id: str, timeout: int = 600):
    """Ingestion Job が完了するまで待機"""
    print("  Waiting for Ingestion Job to complete...")
    start = time.time()
    while time.time() - start < timeout:
        response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            ingestionJobId=job_id
        )
        status = response["ingestionJob"]["status"]
        if status == "COMPLETE":
            stats = response["ingestionJob"]["statistics"]
            print(f"  ✅ Ingestion complete: {stats.get('numberOfDocumentsScanned', 0)} documents processed")
            return
        elif status == "FAILED":
            raise Exception(f"Ingestion failed: {response}")
        time.sleep(10)
    raise TimeoutError(f"Ingestion did not complete within {timeout} seconds")


def main():
    """
    メイン実行フロー
    
    Bedrock Knowledge Bases + OpenSearch Serverless バックエンドの完全ワークフロー。
    
    02_bedrock_kb_with_s3vectors.py との違い:
    - OpenSearch Serverless Collection を事前に作成
    - ハイブリッド検索（セマンティック + キーワード）が可能
    - 高速なクエリレスポンス
    - 高コスト（最低約$100/月）
    
    ユースケース:
    - 高頻度クエリが必要な場合
    - キーワード検索との組み合わせが必要な場合
    - リアルタイム検索が必要な場合
    """
    print("=" * 60)
    print("Bedrock Knowledge Bases + OpenSearch Serverless Sample")
    print("=" * 60)
    
    # クライアント作成
    bedrock_agent, bedrock_runtime, aoss = create_clients()
    
    # 実行前に設定が必要:
    # 1. S3_DATA_BUCKET を実際のバケット名に変更
    # 2. IAM Role ARN を設定（Bedrock KB 用サービスロール）
    # 3. AWS Account ID を設定
    
    # 以下はサービスロールがある前提でのフロー
    # account_id = "YOUR_AWS_ACCOUNT_ID"
    # role_arn = f"arn:aws:iam::{account_id}:role/AmazonBedrockExecutionRoleForKnowledgeBase"
    
    # Step 0: OpenSearch Collection 作成
    # collection_id = step0_create_opensearch_collection(aoss, account_id)
    # collection_arn = f"arn:aws:aoss:{REGION}:{account_id}:collection/{collection_id}"
    
    # Step 1: Knowledge Base 作成
    # kb_id = step1_create_knowledge_base_with_opensearch(bedrock_agent, role_arn, collection_arn)
    
    # Step 2: Data Source 作成
    # ds_id = step2_create_data_source(bedrock_agent, kb_id)
    
    # Step 3: データ取り込み
    # step3_start_ingestion_job(bedrock_agent, kb_id, ds_id)
    
    # Step 4: ハイブリッド検索
    # step4_retrieve_with_hybrid_search(bedrock_runtime, kb_id, "Pythonプログラミング入門")
    
    # Step 5: フィルタ付き検索
    # step5_retrieve_with_filters(bedrock_runtime, kb_id, "プログラミング")
    
    # Step 6: RetrieveAndGenerate
    # step6_retrieve_and_generate(bedrock_runtime, kb_id, "プログラミング初心者が最初に学ぶべきことは？")
    
    print("\n⚠️ このサンプルを実行するには:")
    print("1. S3_DATA_BUCKET を教育コンテンツを格納した実際のS3バケット名に変更")
    print("2. account_id を AWS アカウント ID に設定")
    print("3. IAM Role ARN を Bedrock KB 用サービスロールに設定")
    print("4. コメントアウトを解除して実行")
    
    print("\n💰 コスト注意:")
    print("   OpenSearch Serverless は最低 2 OCU (約 $100/月) のコストがかかります")
    print("   低頻度利用なら S3 Vectors バックエンド (02_) を推奨")
    
    print("\n" + "=" * 60)
    print("✅ Bedrock KB + OpenSearch Serverless Sample (Dry Run) Completed")
    print("=" * 60)


if __name__ == "__main__":
    main()

