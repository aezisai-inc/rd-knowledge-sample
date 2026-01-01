# Neo4j AuraDB 設計ドキュメント

## 1. 概要

### 1.1 移行背景

| 項目 | Neptune Serverless | Neo4j AuraDB |
|-----|-------------------|--------------|
| 月額コスト | ~$166 (1 NCU最低) | $0〜65 |
| AWS依存 | あり | なし |
| Graphiti対応 | 要調整 | ネイティブ |
| Free Tier | なし | あり |
| クエリ言語 | Gremlin | Cypher |

### 1.2 採用理由

1. **コスト削減**: 開発環境で Free Tier 利用可能
2. **Graphiti 親和性**: Neo4j は Graphiti の推奨バックエンド
3. **マルチクラウド対応**: AWS 以外でも利用可能
4. **エコシステム**: APOC, GDS などの豊富なプラグイン

---

## 2. アーキテクチャ

### 2.1 システム構成

```
┌─────────────────────────────────────────────────────────────────┐
│                        rd-knowledge-sample                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Frontend   │    │  API Gateway │    │   Lambda     │      │
│  │  CloudFront  │───▶│    REST API  │───▶│  Functions   │      │
│  └──────────────┘    └──────────────┘    └──────┬───────┘      │
│                                                  │               │
│                                    ┌─────────────┴─────────────┐│
│                                    │                           ││
│                           ┌────────▼────────┐  ┌──────────────┐││
│                           │ Secrets Manager │  │     S3       │││
│                           │  (Neo4j接続情報) │  │ (DataSource) │││
│                           └────────┬────────┘  └──────────────┘││
│                                    │                           ││
└────────────────────────────────────┼───────────────────────────┘│
                                     │                             │
                    ┌────────────────▼────────────────┐            │
                    │         Neo4j AuraDB            │            │
                    │   (外部マネージドサービス)       │            │
                    │                                 │            │
                    │  ┌─────────┐  ┌─────────────┐  │            │
                    │  │  Nodes  │  │    Edges    │  │            │
                    │  │ (Entity)│  │(Relationship)│  │            │
                    │  └─────────┘  └─────────────┘  │            │
                    └─────────────────────────────────┘            │
```

### 2.2 環境構成

| 環境 | Neo4j プラン | 用途 | 月額コスト |
|-----|-------------|------|-----------|
| dev | AuraDB Free | 開発・検証 | $0 |
| staging | AuraDB Professional | ステージング | ~$65 |
| prod | AuraDB Professional | 本番 | ~$65〜 |

---

## 3. Neo4j AuraDB セットアップ手順

### 3.1 インスタンス作成

1. **Neo4j Aura Console にアクセス**
   - URL: https://console.neo4j.io/
   - Google / GitHub アカウントでサインアップ可能

2. **新規インスタンス作成**
   ```
   Name: rd-knowledge-dev
   Type: AuraDB Free (開発用) または Professional (本番用)
   Region: Asia Pacific (Tokyo) - 推奨
   ```

3. **接続情報の保存**
   - Connection URI: `neo4j+s://xxxxxxxx.databases.neo4j.io`
   - Username: `neo4j`
   - Password: (自動生成されたパスワード)

### 3.2 AWS Secrets Manager 設定

```bash
# 開発環境
aws secretsmanager put-secret-value \
  --secret-id rd-knowledge-neo4j-dev \
  --secret-string '{
    "uri": "neo4j+s://xxxxxxxx.databases.neo4j.io",
    "user": "neo4j",
    "password": "your-generated-password",
    "database": "neo4j"
  }'

# 本番環境
aws secretsmanager put-secret-value \
  --secret-id rd-knowledge-neo4j-prod \
  --secret-string '{
    "uri": "neo4j+s://yyyyyyyy.databases.neo4j.io",
    "user": "neo4j",
    "password": "your-generated-password",
    "database": "neo4j"
  }'
```

### 3.3 接続テスト

```python
from neo4j import GraphDatabase

uri = "neo4j+s://xxxxxxxx.databases.neo4j.io"
user = "neo4j"
password = "your-password"

driver = GraphDatabase.driver(uri, auth=(user, password))

with driver.session() as session:
    result = session.run("RETURN 'Hello, Neo4j!' AS message")
    print(result.single()["message"])

driver.close()
```

---

## 4. データモデル設計

### 4.1 ノードラベル

| ラベル | 説明 | プロパティ |
|-------|------|-----------|
| `Episode` | 時系列イベント | id, content, event_time, ingestion_time, source |
| `Entity` | 抽出エンティティ | id, name, type, created_at |
| `Person` | 人物 | id, name, email, role |
| `Document` | ドキュメント | id, title, content, created_at |
| `Concept` | 概念・トピック | id, name, description |

### 4.2 リレーションシップタイプ

| タイプ | 説明 | プロパティ |
|-------|------|-----------|
| `MENTIONS` | エピソードがエンティティを言及 | extracted_at |
| `RELATED_TO` | 汎用関連 | weight, created_at |
| `OWNS` | 所有関係 | since |
| `KNOWS` | 人物間の知人関係 | since, context |
| `PART_OF` | 構成要素 | - |

### 4.3 インデックス設計

```cypher
-- ID検索用インデックス
CREATE INDEX entity_id_idx FOR (n:Entity) ON (n.id);
CREATE INDEX episode_id_idx FOR (n:Episode) ON (n.id);
CREATE INDEX person_id_idx FOR (n:Person) ON (n.id);

-- 時間範囲検索用インデックス
CREATE INDEX episode_event_time_idx FOR (n:Episode) ON (n.event_time);

-- 全文検索用インデックス
CREATE FULLTEXT INDEX entity_name_fulltext FOR (n:Entity) ON EACH [n.name];
```

---

## 5. Graphiti 統合設計

### 5.1 Graphiti 概要

Graphiti は Zep が開発した時系列対応ナレッジグラフフレームワーク。

**主要機能:**
- Dual-temporal model (event_time + ingestion_time)
- エピソードベースの知識蓄積
- LLM によるエンティティ抽出
- 時間を考慮したクエリ

### 5.2 統合アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Agent Application                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    Graphiti Client                    │   │
│  │                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │ add_episode │  │   search    │  │ get_entity  │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  │   │
│  │         │                │                │         │   │
│  └─────────┼────────────────┼────────────────┼─────────┘   │
│            │                │                │              │
│            ▼                ▼                ▼              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    Neo4j Driver                       │   │
│  │              (Cypher Query Execution)                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                              │                              │
└──────────────────────────────┼──────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │   Neo4j AuraDB   │
                    └──────────────────┘
```

### 5.3 サンプルコード

```python
from graphiti_core import Graphiti
from graphiti_core.llm_client import OpenAIClient

# Graphiti クライアント初期化
graphiti = Graphiti(
    neo4j_uri="neo4j+s://xxx.databases.neo4j.io",
    neo4j_user="neo4j",
    neo4j_password="your-password",
    llm_client=OpenAIClient(),
)

# エピソード追加
await graphiti.add_episode(
    name="user_conversation_001",
    episode_body="ユーザーが機械学習について質問しました。特にTransformerアーキテクチャに興味があるようです。",
    source_description="Chat conversation",
    reference_time=datetime.now(),
)

# 検索
results = await graphiti.search(
    query="Transformerについて知りたい",
    num_results=5,
)
```

---

## 6. セキュリティ設計

### 6.1 認証・認可

| 項目 | 設定 |
|-----|------|
| 接続方式 | TLS 1.2+ (neo4j+s://) |
| 認証 | ユーザー名 + パスワード |
| シークレット管理 | AWS Secrets Manager |
| IP制限 | AuraDB Professional で設定可能 |

### 6.2 シークレットローテーション

```python
# Lambda 関数で Secrets Manager から取得
import boto3
import json

def get_neo4j_credentials():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="rd-knowledge-neo4j-dev")
    return json.loads(response["SecretString"])
```

### 6.3 最小権限の原則

```cypher
-- 読み取り専用ユーザー作成（AuraDB Professional のみ）
CREATE USER reader SET PASSWORD 'readonly-password' SET STATUS ACTIVE;
GRANT ROLE reader TO reader;
```

---

## 7. 運用・監視

### 7.1 メトリクス

| メトリクス | 説明 | 閾値 |
|-----------|------|------|
| Query Latency | クエリ応答時間 | < 100ms |
| Active Connections | 接続数 | < 100 |
| Memory Usage | メモリ使用率 | < 80% |
| Disk Usage | ディスク使用率 | < 80% |

### 7.2 CloudWatch 連携

```python
import boto3
from datetime import datetime

cloudwatch = boto3.client("cloudwatch")

def put_neo4j_metric(metric_name: str, value: float):
    cloudwatch.put_metric_data(
        Namespace="RdKnowledgeSample/Neo4j",
        MetricData=[
            {
                "MetricName": metric_name,
                "Value": value,
                "Unit": "Milliseconds",
                "Timestamp": datetime.utcnow(),
            }
        ],
    )
```

### 7.3 バックアップ

- **AuraDB Free**: 自動バックアップなし（手動エクスポート推奨）
- **AuraDB Professional**: 日次自動バックアップ + ポイントインタイムリカバリ

```cypher
-- データエクスポート（Cypher）
CALL apoc.export.cypher.all("backup.cypher", {})
```

---

## 8. コスト試算

### 8.1 月額コスト比較

| 項目 | Neptune Serverless | Neo4j AuraDB |
|-----|-------------------|--------------|
| 開発環境 | $166 | $0 (Free) |
| 本番環境 | $166+ | $65+ |
| **年間削減額** | - | **$1,200+** |

### 8.2 AuraDB プラン詳細

| プラン | 月額 | ノード数 | メモリ | ストレージ |
|-------|------|---------|--------|-----------|
| Free | $0 | 50K | 1GB | 256MB |
| Professional | $65〜 | 無制限 | 4GB+ | 4GB+ |
| Enterprise | 要問合せ | 無制限 | カスタム | カスタム |

---

## 9. 移行チェックリスト

- [x] Neptune リソース削除
- [ ] Neo4j AuraDB インスタンス作成
- [ ] Secrets Manager に接続情報設定
- [ ] CDK 再デプロイ
- [ ] Lambda 関数動作確認
- [ ] API エンドポイントテスト
- [ ] Graphiti 統合テスト

---

## 10. 参考リンク

- [Neo4j AuraDB Documentation](https://neo4j.com/docs/aura/)
- [Graphiti GitHub](https://github.com/getzep/graphiti)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)
- [APOC Library](https://neo4j.com/labs/apoc/)

