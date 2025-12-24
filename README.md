# rd-knowledge-sample

## 目的

**Amazon S3 Vectors** と **Amazon Bedrock Knowledge Bases** の違いを検証し、
Learning Achievement Coach プロジェクトへの適切な適用方法を確認する。

## 重要な違い

### S3 Vectors (低レベルAPI)

```python
# 専用クライアント
s3vectors = boto3.client("s3vectors", region_name="us-west-2")

# 直接的なベクトル操作
s3vectors.create_vector_bucket(vectorBucketName="my-bucket")
s3vectors.create_index(...)
s3vectors.put_vectors(...)
s3vectors.query_vectors(...)
```

**特徴:**
- ベクトルストレージの直接制御
- エンベディング生成は自分で行う必要あり
- 低コスト（最大90%削減）
- サブ秒のクエリレイテンシ

### Bedrock Knowledge Bases (高レベルAPI)

```python
# Bedrock Agentクライアント
bedrock_agent = boto3.client("bedrock-agent", region_name="us-west-2")
bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name="us-west-2")

# マネージドRAGワークフロー
bedrock_agent.create_knowledge_base(...)
bedrock_agent.create_data_source(...)
bedrock_runtime.retrieve(...)
bedrock_runtime.retrieve_and_generate(...)
```

**特徴:**
- フルマネージドRAGワークフロー
- 自動: データ取り込み、チャンキング、エンベディング生成
- バックエンドにS3 Vectors/OpenSearch/Neptune等を選択可能
- Retrieve/RetrieveAndGenerate API

## アーキテクチャ関係図

```
┌─────────────────────────────────────────────────────────────┐
│              Amazon Bedrock Knowledge Bases                 │
│                  (マネージドRAGサービス)                      │
├─────────────────────────────────────────────────────────────┤
│  CreateKnowledgeBase / CreateDataSource / Retrieve API      │
└──────────────────────────┬──────────────────────────────────┘
                           │ Uses
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 Vector Store Backends                        │
├──────────┬──────────┬────────────┬────────────┬─────────────┤
│ S3       │OpenSearch│ Aurora     │ Neptune    │ Pinecone    │
│ Vectors  │Serverless│ PostgreSQL │ Analytics  │             │
│ (低コスト)│(高性能)   │ (既存活用) │ (GraphRAG) │ (外部)      │
└──────────┴──────────┴────────────┴────────────┴─────────────┘
```

## サンプルファイル

| ファイル | 説明 | コスト | ユースケース |
|----------|------|--------|--------------|
| `src/00_verify_availability.py` | boto3 クライアントの利用可否を検証 | - | 環境確認 |
| `src/01_s3_vectors_direct.py` | S3 Vectors直接操作のサンプル | 💰 最低 | 低頻度クエリ、コスト最優先 |
| `src/02_bedrock_kb_with_s3vectors.py` | Bedrock KB + S3 Vectorsバックエンド | 💰💰 低〜中 | 標準的なRAGアプリ |
| `src/03_bedrock_kb_with_opensearch.py` | Bedrock KB + OpenSearchバックエンド | 💰💰💰 中〜高 | 高頻度、ハイブリッド検索 |
| `src/04_comparison.py` | 機能・コスト比較表 | - | 選定ガイド |
| `src/05_agentcore_memory.py` | **AgentCore Memory** のサンプル | 💰💰 中 | エピソード記憶、会話履歴 |

## クイックスタート

### 1. 環境構築

```bash
# プロジェクトディレクトリへ移動
cd 40-research-develop/rd-knowledge-sample

# 仮想環境作成 & 依存関係インストール
uv venv
source .venv/bin/activate
uv pip install -e .

# または一括で
uv sync
```

### 2. AWS認証情報設定

```bash
# AWS Profile を使用
export AWS_PROFILE=your-profile
export AWS_REGION=us-west-2

# または直接認証情報を設定
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
```

### 3. 利用可否の確認

```bash
# boto3 クライアントの利用可否を確認
uv run python src/00_verify_availability.py
```

### 4. サンプル実行

```bash
# S3 Vectors 直接操作
uv run python src/01_s3_vectors_direct.py

# Bedrock KB + S3 Vectors
uv run python src/02_bedrock_kb_with_s3vectors.py

# Bedrock KB + OpenSearch
uv run python src/03_bedrock_kb_with_opensearch.py

# 比較表を表示
uv run python src/04_comparison.py

# AgentCore Memory（エピソード記憶）
uv run python src/05_agentcore_memory.py
```

## 選定ガイド

| 要件 | 推奨 |
|------|------|
| コスト最優先、低頻度クエリ | S3 Vectors 直接 (`01_`) |
| 標準的なRAGアプリ、開発効率重視 | Bedrock KB + S3 Vectors (`02_`) |
| 高頻度クエリ、ハイブリッド検索 | Bedrock KB + OpenSearch (`03_`) |
| グラフ構造が必要 | Neptune Analytics (別サンプル) |

## Learning Achievement Coach への適用

### 推奨構成

```
┌──────────────────────────────────────────────────────────────┐
│                   Learning Achievement Coach                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  教育コンテンツRAG ──► Bedrock KB + S3 Vectors (低コスト)     │
│                                                              │
│  スキル関係グラフ ──► Neptune Serverless (GraphRAG)          │
│                                                              │
│  ユーザー対話履歴 ──► AgentCore Memory (マネージド)          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 理由

1. **Bedrock KB + S3 Vectors**: 教育コンテンツの検索に最適（低頻度クエリ、大量データ）
2. **Neptune**: スキル・学習パス間の関係性を表現（グラフ構造必須）
3. **AgentCore Memory**: ユーザーごとのコンテキスト保持（エピソード記憶）

### コスト概算 (月額)

| コンポーネント | 想定 | 月額概算 |
|----------------|------|----------|
| Bedrock KB + S3 Vectors | 10万ドキュメント | ~$50 |
| Neptune Serverless | 低頻度利用 | ~$30 |
| AgentCore Memory | 1000ユーザー | ~$20 |
| **合計** | | **~$100/月** |

## 注意事項

⚠️ **S3 Vectors はプレビュー段階** (2024年12月時点)
- 利用可能リージョン: us-east-1, us-east-2, us-west-2, eu-central-1, ap-southeast-2
- 本番利用前に GA を確認すること

💰 **OpenSearch Serverless のコスト**
- 最低 2 OCU (約 $100/月) のコストがかかる
- 低頻度利用の場合は S3 Vectors を推奨

## 参考リンク

- [Amazon S3 Vectors User Guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-getting-started.html)
- [Amazon Bedrock Knowledge Bases User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [Bedrock KB with S3 Vectors](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-bedrock-kb.html)
- [OpenSearch Serverless](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html)
