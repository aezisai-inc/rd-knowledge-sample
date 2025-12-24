"""
01_s3_vectors_direct.py

S3 Vectors API を直接使用するサンプル。
Bedrock Knowledge Bases を介さず、ベクトルストレージを直接操作する。

使用API:
- s3vectors:CreateVectorBucket
- s3vectors:CreateVectorIndex
- s3vectors:PutVectors
- s3vectors:QueryVectors

参考: https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-getting-started.html
"""

import json
import boto3
from datetime import datetime

# Configuration
REGION = "us-west-2"  # S3 Vectors available regions: us-east-1, us-east-2, us-west-2, eu-central-1, ap-southeast-2
VECTOR_BUCKET_NAME = f"learning-coach-vectors-{datetime.now().strftime('%Y%m%d')}"
VECTOR_INDEX_NAME = "educational-content"
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSION = 1024


def create_clients():
    """
    S3 Vectors と Bedrock Runtime クライアントを作成。
    
    注意: s3vectors は s3 とは別のサービス名前空間を使用
    """
    s3vectors = boto3.client("s3vectors", region_name=REGION)
    bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)
    return s3vectors, bedrock_runtime


def step1_create_vector_bucket(s3vectors):
    """
    Step 1: Vector Bucket を作成
    
    Vector Bucket は S3 バケットとは別物。
    ベクトルデータ専用のストレージタイプ。
    """
    print(f"\n=== Step 1: Create Vector Bucket: {VECTOR_BUCKET_NAME} ===")
    
    try:
        response = s3vectors.create_vector_bucket(
            vectorBucketName=VECTOR_BUCKET_NAME,
            # encryptionConfiguration={
            #     "sseType": "SSE_S3"  # or "SSE_KMS" with kmsKeyArn
            # }
        )
        print(f"✅ Vector Bucket created: {response['vectorBucketArn']}")
        return response
    except s3vectors.exceptions.ConflictException:
        print(f"⚠️ Vector Bucket already exists: {VECTOR_BUCKET_NAME}")
        return {"vectorBucketArn": f"arn:aws:s3vectors:{REGION}::vector-bucket/{VECTOR_BUCKET_NAME}"}


def step2_create_vector_index(s3vectors):
    """
    Step 2: Vector Index を作成
    
    Index ごとに dimension と distance metric を設定。
    一度作成すると変更不可。
    
    注意: boto3 では create_index() メソッド（create_vector_index ではない）
    """
    print(f"\n=== Step 2: Create Vector Index: {VECTOR_INDEX_NAME} ===")
    
    try:
        # 正しいメソッド名: create_index（create_vector_index ではない）
        response = s3vectors.create_index(
            vectorBucketName=VECTOR_BUCKET_NAME,
            indexName=VECTOR_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            distanceMetric="cosine",  # or "euclidean"
            # nonFilterableMetadataKeys=["source_text"]  # Optional: 検索フィルタ対象外のメタデータ
        )
        print(f"✅ Vector Index created: {response['indexArn']}")
        return response
    except s3vectors.exceptions.ConflictException:
        print(f"⚠️ Vector Index already exists: {VECTOR_INDEX_NAME}")
        return {"indexArn": f"arn:aws:s3vectors:{REGION}::vector-bucket/{VECTOR_BUCKET_NAME}/index/{VECTOR_INDEX_NAME}"}


def step3_generate_embedding(bedrock_runtime, text: str) -> list[float]:
    """
    Step 3: Bedrock でエンベディングを生成
    
    S3 Vectors は単なるストレージなので、
    エンベディング生成は Bedrock を直接呼び出す必要がある。
    """
    response = bedrock_runtime.invoke_model(
        modelId=EMBEDDING_MODEL_ID,
        body=json.dumps({"inputText": text})
    )
    response_body = json.loads(response["body"].read())
    return response_body["embedding"]


def step4_put_vectors(s3vectors, bedrock_runtime):
    """
    Step 4: ベクトルを挿入
    
    エンベディング生成 → S3 Vectors に格納の2ステップ。
    Bedrock KB なら自動化されるが、S3 Vectors 直接操作では手動。
    """
    print(f"\n=== Step 4: Insert Vectors ===")
    
    # 教育コンテンツサンプル
    educational_contents = [
        {
            "key": "python-basics",
            "text": "Python入門: 変数、データ型、制御構造の基礎を学ぶ",
            "metadata": {"category": "programming", "difficulty": "beginner", "language": "python"}
        },
        {
            "key": "python-advanced",
            "text": "Python応用: デコレータ、ジェネレータ、メタクラスを理解する",
            "metadata": {"category": "programming", "difficulty": "advanced", "language": "python"}
        },
        {
            "key": "aws-basics",
            "text": "AWS入門: EC2、S3、Lambdaの基本概念と使い方",
            "metadata": {"category": "cloud", "difficulty": "beginner", "platform": "aws"}
        },
        {
            "key": "machine-learning",
            "text": "機械学習入門: 教師あり学習と教師なし学習の違いを理解する",
            "metadata": {"category": "ai", "difficulty": "intermediate"}
        },
    ]
    
    # エンベディング生成
    vectors_to_insert = []
    for content in educational_contents:
        embedding = step3_generate_embedding(bedrock_runtime, content["text"])
        vectors_to_insert.append({
            "key": content["key"],
            "data": {"float32": embedding},
            "metadata": {
                **content["metadata"],
                "source_text": content["text"]  # 元テキストを保存
            }
        })
        print(f"  Generated embedding for: {content['key']}")
    
    # S3 Vectors に挿入
    response = s3vectors.put_vectors(
        vectorBucketName=VECTOR_BUCKET_NAME,
        indexName=VECTOR_INDEX_NAME,
        vectors=vectors_to_insert
    )
    print(f"✅ Inserted {len(vectors_to_insert)} vectors")
    return response


def step5_query_vectors(s3vectors, bedrock_runtime, query_text: str, top_k: int = 3):
    """
    Step 5: ベクトル検索
    
    クエリテキスト → エンベディング生成 → S3 Vectors でクエリ
    """
    print(f"\n=== Step 5: Query Vectors ===")
    print(f"Query: {query_text}")
    
    # クエリのエンベディング生成
    query_embedding = step3_generate_embedding(bedrock_runtime, query_text)
    
    # S3 Vectors でクエリ
    response = s3vectors.query_vectors(
        vectorBucketName=VECTOR_BUCKET_NAME,
        indexName=VECTOR_INDEX_NAME,
        queryVector={"float32": query_embedding},
        topK=top_k,
        returnDistance=True,
        returnMetadata=True
    )
    
    print(f"\nResults (top {top_k}):")
    for i, result in enumerate(response["vectors"], 1):
        print(f"  {i}. {result['key']} (distance: {result['distance']:.4f})")
        if "metadata" in result:
            print(f"     Category: {result['metadata'].get('category', 'N/A')}")
            print(f"     Difficulty: {result['metadata'].get('difficulty', 'N/A')}")
    
    return response


def step6_query_with_filter(s3vectors, bedrock_runtime, query_text: str):
    """
    Step 6: メタデータフィルタ付きクエリ
    
    特定のカテゴリや難易度でフィルタリング可能。
    """
    print(f"\n=== Step 6: Query with Metadata Filter ===")
    print(f"Query: {query_text}")
    print(f"Filter: category = 'programming'")
    
    query_embedding = step3_generate_embedding(bedrock_runtime, query_text)
    
    response = s3vectors.query_vectors(
        vectorBucketName=VECTOR_BUCKET_NAME,
        indexName=VECTOR_INDEX_NAME,
        queryVector={"float32": query_embedding},
        topK=3,
        filter={"category": "programming"},  # メタデータフィルタ
        returnDistance=True,
        returnMetadata=True
    )
    
    print(f"\nFiltered Results:")
    for i, result in enumerate(response["vectors"], 1):
        print(f"  {i}. {result['key']} (distance: {result['distance']:.4f})")
    
    return response


def cleanup(s3vectors):
    """クリーンアップ（オプション）"""
    print(f"\n=== Cleanup ===")
    
    try:
        # Delete vectors first
        # s3vectors.delete_vectors(...)
        
        # Delete index (正しいメソッド名: delete_index)
        s3vectors.delete_index(
            vectorBucketName=VECTOR_BUCKET_NAME,
            indexName=VECTOR_INDEX_NAME
        )
        print(f"✅ Deleted Vector Index: {VECTOR_INDEX_NAME}")
        
        # Delete bucket
        s3vectors.delete_vector_bucket(
            vectorBucketName=VECTOR_BUCKET_NAME
        )
        print(f"✅ Deleted Vector Bucket: {VECTOR_BUCKET_NAME}")
    except Exception as e:
        print(f"⚠️ Cleanup failed: {e}")


def main():
    """
    メイン実行フロー
    
    S3 Vectors を直接使用する場合の完全なワークフロー。
    Bedrock KB を使わないため、以下が手動で必要:
    - エンベディング生成
    - ベクトル挿入
    - クエリ実行
    """
    print("=" * 60)
    print("S3 Vectors Direct API Sample")
    print("=" * 60)
    
    # クライアント作成
    s3vectors, bedrock_runtime = create_clients()
    
    # Step 1-2: インフラ作成
    step1_create_vector_bucket(s3vectors)
    step2_create_vector_index(s3vectors)
    
    # Step 3-4: データ挿入
    step4_put_vectors(s3vectors, bedrock_runtime)
    
    # Step 5-6: クエリ
    step5_query_vectors(s3vectors, bedrock_runtime, "Pythonでプログラミングを学びたい")
    step6_query_with_filter(s3vectors, bedrock_runtime, "クラウドについて学びたい")
    
    # クリーンアップ（コメントアウト）
    # cleanup(s3vectors)
    
    print("\n" + "=" * 60)
    print("✅ S3 Vectors Direct API Sample Completed")
    print("=" * 60)


if __name__ == "__main__":
    main()

