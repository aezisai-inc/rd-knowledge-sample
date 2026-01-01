# 環境差分比較マトリクス

ローカル開発環境と AWS 本番環境の差分を詳細に比較し、環境切り替え時の注意点をまとめます。

## 📋 目次

1. [概要](#概要)
2. [VectorStore 比較](#vectorstore-比較)
3. [KnowledgeBase 比較](#knowledgebase-比較)
4. [MemoryStore 比較](#memorystore-比較)
5. [GraphStore 比較](#graphstore-比較)
6. [コスト比較](#コスト比較)
7. [制限事項](#制限事項)
8. [推奨構成](#推奨構成)

---

## 概要

### アーキテクチャ図

```
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Protocol (Interface) Layer                  │   │
│  │   VectorStore | KnowledgeBase | MemoryStore | GraphStore │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│              ┌───────────────┴───────────────┐                  │
│              ▼                               ▼                  │
│  ┌─────────────────────┐       ┌─────────────────────┐         │
│  │   Local Adapters    │       │    AWS Adapters     │         │
│  │                     │       │                     │         │
│  │  • In-memory/FAISS  │       │  • S3 Vectors       │         │
│  │  • Ollama/ChromaDB  │       │  • Bedrock KB       │         │
│  │  • SQLite/Redis     │       │  • AgentCore Memory │         │
│  │  • Neo4j/NetworkX   │       │  • Neptune          │         │
│  └─────────────────────┘       └─────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 環境切り替え方法

```python
import os
from src.config import get_storage_factory

# 環境変数で切り替え
os.environ["ENVIRONMENT"] = "local"  # or "aws"

# ファクトリから適切なアダプタを取得
factory = get_storage_factory()
vector_store = factory.create_vector_store()
knowledge_base = factory.create_knowledge_base()
memory_store = factory.create_memory_store()
graph_store = factory.create_graph_store()
```

---

## VectorStore 比較

| 項目 | ローカル (FAISS/In-memory) | AWS (S3 Vectors) |
|------|---------------------------|------------------|
| **エンドポイント** | `localhost` (In-memory) | `s3vectors.{region}.amazonaws.com` |
| **認証** | 不要 | IAM / Access Key |
| **データ永続化** | JSON ファイル | S3 バケット |
| **最大次元数** | 制限なし | 2,000 |
| **最大ベクトル数** | メモリ依存 | 100億/バケット |
| **クエリ top_k** | 制限なし | 最大 10,000 |
| **距離メトリクス** | cosine, euclidean | cosine, euclidean, dot_product |
| **フィルタリング** | メタデータ完全一致 | メタデータフィルタ式 |
| **レイテンシ** | < 10ms | 10-100ms |
| **スケーラビリティ** | シングルノード | 自動スケーリング |

### 設定の違い

**ローカル:**
```python
from src.adapters.local import LocalVectorStore

store = LocalVectorStore(
    persist_dir="./data/vectors"
)
```

**AWS:**
```python
from src.adapters.aws import AWSVectorStore

store = AWSVectorStore(
    region="ap-northeast-1",
    bucket_name="my-vector-bucket"
)
```

---

## KnowledgeBase 比較

| 項目 | ローカル (Ollama/ChromaDB) | AWS (Bedrock KB) |
|------|---------------------------|------------------|
| **エンドポイント** | `localhost:11434` (Ollama) | `bedrock-agent-runtime.{region}.amazonaws.com` |
| **認証** | 不要 | IAM |
| **LLM モデル** | llama3.2, mistral 等 | Claude 3.5, Titan 等 |
| **埋め込みモデル** | nomic-embed-text | Titan Embeddings |
| **ベクトル DB** | ChromaDB / In-memory | S3 Vectors / OpenSearch |
| **最大ドキュメントサイズ** | 制限なし | 50 MB |
| **チャンクサイズ** | カスタム | 最大 500 トークン |
| **レイテンシ (retrieve)** | 50-200ms | 200-500ms |
| **レイテンシ (RAG)** | 1-5s | 2-10s |
| **コスト** | 無料 (ローカル GPU) | 入力/出力トークン課金 |

### 設定の違い

**ローカル:**
```python
from src.adapters.local import LocalKnowledgeBase

kb = LocalKnowledgeBase(
    mode="ollama",
    ollama_base_url="http://localhost:11434",
    model="llama3.2",
    embedding_model="nomic-embed-text"
)
```

**AWS:**
```python
from src.adapters.aws import AWSKnowledgeBase

kb = AWSKnowledgeBase(
    region="ap-northeast-1",
    knowledge_base_id="KB12345678",
    model_arn="arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
)
```

---

## MemoryStore 比較

| 項目 | ローカル (SQLite/Redis) | AWS (AgentCore Memory) |
|------|------------------------|------------------------|
| **エンドポイント** | `localhost:6379` (Redis) | `bedrock-agentcore.{region}.amazonaws.com` |
| **認証** | Redis AUTH (オプション) | IAM |
| **ストレージ** | SQLite / Redis | マネージドサービス |
| **メモリタイプ** | 簡易実装 | Short-term/Episodic/Semantic/Reflections |
| **セッション管理** | 手動実装 | 自動管理 |
| **埋め込み検索** | 簡易 (キーワード) | セマンティック検索 |
| **TTL** | Redis TTL | memoryStrategies で設定 |
| **最大イベント数** | 制限なし | 10,000/セッション |
| **レイテンシ** | < 5ms | 50-200ms |

### 設定の違い

**ローカル:**
```python
from src.adapters.local import LocalMemoryStore

memory = LocalMemoryStore(
    mode="sqlite",
    db_path="./data/memory.db"
)
# または
memory = LocalMemoryStore(
    mode="redis",
    redis_url="redis://localhost:6379"
)
```

**AWS:**
```python
from src.adapters.aws import AWSMemoryStore

memory = AWSMemoryStore(
    region="ap-northeast-1",
    memory_id="mem-12345678"
)
```

---

## GraphStore 比較

| 項目 | ローカル (Neo4j/NetworkX) | AWS (Neptune) |
|------|-------------------------|---------------|
| **エンドポイント** | `bolt://localhost:7687` | `{cluster}.{region}.neptune.amazonaws.com:8182` |
| **認証** | Neo4j Auth | IAM / Gremlin |
| **クエリ言語** | Cypher | Gremlin / openCypher / SPARQL |
| **最大ノード数** | メモリ依存 | 数十億 |
| **最大エッジ数** | メモリ依存 | 数十億 |
| **レプリケーション** | なし | 自動 (最大 15 リードレプリカ) |
| **バックアップ** | 手動 | 自動スナップショット |
| **ACID** | ✅ | ✅ |
| **レイテンシ** | < 10ms | 10-50ms |

### 設定の違い

**ローカル:**
```python
from src.adapters.local import LocalGraphStore

graph = LocalGraphStore(
    mode="neo4j",
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password123"
)
# または
graph = LocalGraphStore(
    mode="networkx",
    persist_dir="./data/graph"
)
```

**AWS:**
```python
from src.adapters.aws import AWSGraphStore

graph = AWSGraphStore(
    region="ap-northeast-1",
    cluster_endpoint="my-cluster.cluster-xxxx.ap-northeast-1.neptune.amazonaws.com",
    port=8182
)
```

---

## コスト比較

### 月額コスト概算（中規模利用）

| サービス | ローカル | AWS | 備考 |
|---------|---------|-----|------|
| **VectorStore** | $0 | $10-50 | S3 Vectors: ストレージ + クエリ課金 |
| **KnowledgeBase** | $0 (GPU電気代) | $50-500 | Bedrock: トークン課金 |
| **MemoryStore** | $0 | $20-100 | AgentCore: イベント + 検索課金 |
| **GraphStore** | $0 | $100-500 | Neptune Serverless: NCU 課金 |
| **合計** | ~$0 | $180-1,150 | |

### AWS 料金詳細

| サービス | 単価 | 単位 |
|---------|------|------|
| S3 Vectors ストレージ | $0.023 | GB/月 |
| S3 Vectors クエリ | $0.0003 | 1,000 クエリ |
| Bedrock Claude 3.5 入力 | $0.003 | 1K トークン |
| Bedrock Claude 3.5 出力 | $0.015 | 1K トークン |
| AgentCore Memory イベント | $0.0001 | イベント |
| Neptune Serverless | $0.12 | NCU-時間 |

---

## 制限事項

### ローカル環境の制限

| 項目 | 制限 | 回避策 |
|------|------|--------|
| スケーラビリティ | シングルノード | Docker Compose スケーリング |
| データ耐久性 | ローカルディスク依存 | 定期バックアップ |
| 同時接続数 | プロセス数依存 | コネクションプール |
| GPU メモリ | ローカル GPU に依存 | モデルサイズ調整 |

### AWS 環境の制限

| サービス | 制限 | デフォルト値 | 引き上げ可能 |
|---------|------|-------------|-------------|
| S3 Vectors バケット数 | 100/アカウント | 100 | ✅ |
| Bedrock KB 数 | 100/アカウント | 100 | ✅ |
| AgentCore Memory 数 | 100/アカウント | 100 | ✅ |
| Neptune クラスター | 40/アカウント | 40 | ✅ |
| Bedrock TPM | 100,000 | - | サービス依存 |

---

## 推奨構成

### 開発環境

```yaml
# docker-compose.local.yml
services:
  localstack:
    image: localstack/localstack
    ports: ["4566:4566"]
  
  neo4j:
    image: neo4j:5.15-community
    ports: ["7474:7474", "7687:7687"]
  
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  
  chromadb:
    image: chromadb/chroma
    ports: ["8000:8000"]
  
  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
```

### ステージング環境

```
┌─────────────────────────────────────────────────────┐
│                  AWS Staging                        │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │ S3 Vectors  │  │ Bedrock KB  │  │  Neptune   │  │
│  │ (dev prefix)│  │ (dev tier)  │  │ Serverless │  │
│  └─────────────┘  └─────────────┘  └────────────┘  │
│                                                     │
│  コスト削減: 最小リソース構成                        │
└─────────────────────────────────────────────────────┘
```

### 本番環境

```
┌─────────────────────────────────────────────────────┐
│                  AWS Production                     │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │ S3 Vectors  │  │ Bedrock KB  │  │  Neptune   │  │
│  │ (HA config) │  │(prod model) │  │ (HA + DR)  │  │
│  └─────────────┘  └─────────────┘  └────────────┘  │
│                                                     │
│  ・マルチ AZ 配置                                    │
│  ・自動バックアップ                                  │
│  ・モニタリング + アラート                           │
└─────────────────────────────────────────────────────┘
```

---

## 環境切り替えチェックリスト

### ローカル → AWS 移行時

- [ ] IAM ロール・ポリシーの作成
- [ ] VPC / セキュリティグループの設定
- [ ] AWS リソースの作成（S3 Vectors, Bedrock KB, Neptune）
- [ ] 環境変数の更新 (`ENVIRONMENT=aws`)
- [ ] データ移行スクリプトの実行
- [ ] 接続テストの実施
- [ ] パフォーマンステスト

### AWS → ローカル 移行時

- [ ] Docker Compose 環境の起動
- [ ] 環境変数の更新 (`ENVIRONMENT=local`)
- [ ] 必要に応じてデータのエクスポート/インポート
- [ ] Ollama モデルのダウンロード
- [ ] 接続テストの実施

---

## 参考リンク

- [S3 Vectors ドキュメント](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors.html)
- [Bedrock Knowledge Base ドキュメント](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [Amazon Neptune ドキュメント](https://docs.aws.amazon.com/neptune/latest/userguide/)
- [LocalStack ドキュメント](https://docs.localstack.cloud/)
