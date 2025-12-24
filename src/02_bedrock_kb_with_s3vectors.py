"""
02_bedrock_kb_with_s3vectors.py

Bedrock Knowledge Bases を使用し、バックエンドに S3 Vectors を指定するサンプル。
S3 Vectors を直接操作するのではなく、Bedrock KB 経由でマネージドRAGを実現。

使用API:
- bedrock-agent:CreateKnowledgeBase
- bedrock-agent:CreateDataSource
- bedrock-agent:StartIngestionJob
- bedrock-agent-runtime:Retrieve
- bedrock-agent-runtime:RetrieveAndGenerate

参考: https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-bedrock-kb.html

違い:
- 01_s3_vectors_direct.py: エンベディング生成・挿入を手動で行う
- このファイル: Bedrock KB が自動でデータ取り込み・チャンキング・エンベディング生成を行う
"""

import json
import time
import boto3
from datetime import datetime

# Configuration
REGION = "us-west-2"
KNOWLEDGE_BASE_NAME = f"learning-coach-kb-{datetime.now().strftime('%Y%m%d%H%M')}"
DATA_SOURCE_NAME = "educational-content-source"
S3_DATA_BUCKET = "your-data-source-bucket"  # 要変更: 教育コンテンツを格納したS3バケット
S3_DATA_PREFIX = "educational-content/"

# Embedding model for Bedrock KB
EMBEDDING_MODEL_ARN = f"arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v2:0"

# For RetrieveAndGenerate
GENERATION_MODEL_ARN = f"arn:aws:bedrock:{REGION}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"


def create_clients():
    """
    Bedrock Agent クライアントを作成
    
    注意:
    - bedrock-agent: ビルドタイム操作（KB作成、データソース作成等）
    - bedrock-agent-runtime: ランタイム操作（Retrieve, RetrieveAndGenerate）
    """
    bedrock_agent = boto3.client("bedrock-agent", region_name=REGION)
    bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)
    return bedrock_agent, bedrock_runtime


def step1_create_knowledge_base_with_s3vectors(bedrock_agent, role_arn: str):
    """
    Step 1: S3 Vectors バックエンドで Knowledge Base を作成
    
    Bedrock KB 作成時に vectorStoreType: S3_VECTOR を指定すると、
    Bedrock が自動的に S3 Vector Bucket と Index を作成・管理する。
    
    ⚠️ "Quick create" モードでは、Bedrock が自動で S3 Vector インフラを作成
    """
    print(f"\n=== Step 1: Create Knowledge Base with S3 Vectors Backend ===")
    
    response = bedrock_agent.create_knowledge_base(
        name=KNOWLEDGE_BASE_NAME,
        description="Learning Achievement Coach - Educational Content Knowledge Base",
        roleArn=role_arn,  # Bedrock KB用のサービスロール
        
        # Knowledge Base Configuration
        knowledgeBaseConfiguration={
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": EMBEDDING_MODEL_ARN,
                "embeddingModelConfiguration": {
                    "bedrockEmbeddingModelConfiguration": {
                        "dimensions": 1024  # Titan Embed v2 default
                    }
                }
            }
        },
        
        # Storage Configuration - S3 Vectors backend
        storageConfiguration={
            "type": "S3_VECTOR",
            # Quick create mode: Bedrock creates S3 Vector Bucket/Index automatically
            # Or specify existing:
            # "s3VectorConfiguration": {
            #     "vectorBucketArn": "arn:aws:s3vectors:us-west-2:...",
            #     "vectorIndexArn": "arn:aws:s3vectors:us-west-2:..."
            # }
        }
    )
    
    kb_id = response["knowledgeBase"]["knowledgeBaseId"]
    print(f"✅ Knowledge Base created: {kb_id}")
    print(f"   Name: {KNOWLEDGE_BASE_NAME}")
    print(f"   Status: {response['knowledgeBase']['status']}")
    
    # Wait for KB to be active
    _wait_for_knowledge_base_active(bedrock_agent, kb_id)
    
    return kb_id


def step2_create_data_source(bedrock_agent, kb_id: str):
    """
    Step 2: S3 データソースを作成
    
    Bedrock KB は S3 バケットからドキュメントを自動取り込み:
    - PDF, Word, HTML, TXT 等をサポート
    - 自動チャンキング
    - 自動エンベディング生成
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
        
        # Chunking strategy
        vectorIngestionConfiguration={
            "chunkingConfiguration": {
                "chunkingStrategy": "FIXED_SIZE",
                "fixedSizeChunkingConfiguration": {
                    "maxTokens": 512,
                    "overlapPercentage": 20
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
    
    Bedrock KB が自動で:
    1. S3 からドキュメントを取得
    2. テキスト抽出
    3. チャンキング
    4. エンベディング生成
    5. S3 Vectors に格納
    """
    print(f"\n=== Step 3: Start Ingestion Job ===")
    
    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id
    )
    
    job_id = response["ingestionJob"]["ingestionJobId"]
    print(f"✅ Ingestion Job started: {job_id}")
    
    # Wait for completion
    _wait_for_ingestion_complete(bedrock_agent, kb_id, ds_id, job_id)
    
    return job_id


def step4_retrieve(bedrock_runtime, kb_id: str, query: str, top_k: int = 5):
    """
    Step 4: Retrieve API - ベクトル検索のみ
    
    S3 Vectors をバックエンドとして、セマンティック検索を実行。
    チャンク（テキスト断片）を返す。
    """
    print(f"\n=== Step 4: Retrieve (Vector Search Only) ===")
    print(f"Query: {query}")
    
    response = bedrock_runtime.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={
            "text": query
        },
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": top_k
            }
        }
    )
    
    print(f"\nRetrieved {len(response['retrievalResults'])} chunks:")
    for i, result in enumerate(response["retrievalResults"], 1):
        content = result["content"]["text"][:100] + "..." if len(result["content"]["text"]) > 100 else result["content"]["text"]
        print(f"  {i}. Score: {result.get('score', 'N/A'):.4f}")
        print(f"     Content: {content}")
        if "location" in result:
            print(f"     Source: {result['location'].get('s3Location', {}).get('uri', 'N/A')}")
    
    return response


def step5_retrieve_and_generate(bedrock_runtime, kb_id: str, query: str):
    """
    Step 5: RetrieveAndGenerate API - RAG完全フロー
    
    1. S3 Vectors でベクトル検索
    2. 検索結果をコンテキストとしてLLMに渡す
    3. 回答を生成
    
    これが Bedrock KB の真価。
    """
    print(f"\n=== Step 5: RetrieveAndGenerate (Full RAG) ===")
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
                        "numberOfResults": 5
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
    
    Bedrock Knowledge Bases + S3 Vectors バックエンドの完全ワークフロー。
    
    01_s3_vectors_direct.py との違い:
    - エンベディング生成が自動
    - ドキュメント取り込みが自動
    - チャンキングが自動
    - RAG (RetrieveAndGenerate) が統合
    """
    print("=" * 60)
    print("Bedrock Knowledge Bases + S3 Vectors Sample")
    print("=" * 60)
    
    # クライアント作成
    bedrock_agent, bedrock_runtime = create_clients()
    
    # 実行前に設定が必要:
    # 1. S3_DATA_BUCKET を実際のバケット名に変更
    # 2. IAM Role ARN を設定（Bedrock KB 用サービスロール）
    
    # 以下はサービスロールがある前提でのフロー
    # role_arn = "arn:aws:iam::YOUR_ACCOUNT:role/AmazonBedrockExecutionRoleForKnowledgeBase"
    
    # Step 1: Knowledge Base 作成
    # kb_id = step1_create_knowledge_base_with_s3vectors(bedrock_agent, role_arn)
    
    # Step 2: Data Source 作成
    # ds_id = step2_create_data_source(bedrock_agent, kb_id)
    
    # Step 3: データ取り込み
    # step3_start_ingestion_job(bedrock_agent, kb_id, ds_id)
    
    # Step 4: Retrieve
    # step4_retrieve(bedrock_runtime, kb_id, "Pythonプログラミングについて教えて")
    
    # Step 5: RetrieveAndGenerate
    # step5_retrieve_and_generate(bedrock_runtime, kb_id, "AWSの基礎を学ぶには何から始めればいい？")
    
    print("\n⚠️ このサンプルを実行するには:")
    print("1. S3_DATA_BUCKET を教育コンテンツを格納した実際のS3バケット名に変更")
    print("2. IAM Role ARN を Bedrock KB 用サービスロールに設定")
    print("3. コメントアウトを解除して実行")
    
    print("\n" + "=" * 60)
    print("✅ Bedrock KB + S3 Vectors Sample (Dry Run) Completed")
    print("=" * 60)


if __name__ == "__main__":
    main()


