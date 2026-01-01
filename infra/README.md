# rd-knowledge-sample Infrastructure

AWS CDK による Infrastructure as Code 定義

## ⚡ グラフDB移行

**Neptune Serverless → Neo4j AuraDB に移行**

| 項目 | 変更前 (Neptune) | 変更後 (Neo4j) |
|-----|-----------------|---------------|
| 月額コスト | ~$166/月 | $0〜65/月 |
| AWS依存 | あり | なし |
| Graphiti対応 | 要調整 | ネイティブ対応 |
| Free Tier | なし | あり |

## 構成

```
infra/
├── bin/
│   └── app.ts                    # CDK エントリーポイント
├── lib/
│   ├── stacks/
│   │   ├── storage-stack.ts      # S3, Neo4j 接続情報 (Secrets Manager)
│   │   ├── compute-stack.ts      # Lambda, API Gateway
│   │   ├── frontend-stack.ts     # S3, CloudFront (静的サイト)
│   │   └── pipeline-stack.ts     # CodePipeline CI/CD
│   └── config/
│       └── environments.ts       # 環境設定
├── lambda/
│   ├── memory-api/               # Memory API Lambda
│   ├── vector-api/               # Vector API Lambda
│   ├── graph-api/                # Graph API Lambda (Neo4j)
│   └── layers/
│       └── dependencies/         # Lambda Layer
├── cdk.json
├── package.json
└── tsconfig.json
```

## デプロイ

### 前提条件

```bash
# AWS CDK CLI
npm install -g aws-cdk

# AWS 認証設定
aws configure
```

### 開発環境

```bash
cd infra
npm install

# 差分確認
cdk diff --context env=dev

# デプロイ
cdk deploy --context env=dev --all
```

### 本番環境

```bash
cdk deploy --context env=prod --all
```

## Neo4j AuraDB セットアップ

### 1. AuraDB インスタンス作成

1. [Neo4j Aura Console](https://console.neo4j.io/) にアクセス
2. 新しいインスタンスを作成
   - **Free Tier**: 開発用（無料）
   - **Professional**: 本番用（~$65/月〜）
3. 接続情報を控える
   - Connection URI: `neo4j+s://xxxxx.databases.neo4j.io`
   - Username: `neo4j`
   - Password: (生成されたパスワード)

### 2. Secrets Manager 更新

```bash
aws secretsmanager put-secret-value \
  --secret-id rd-knowledge-neo4j-dev \
  --secret-string '{
    "uri": "neo4j+s://xxxxx.databases.neo4j.io",
    "user": "neo4j",
    "password": "your-aura-password",
    "database": "neo4j"
  }'
```

## スタック構成

| スタック | 説明 | 主要リソース |
|---------|------|-------------|
| `StorageStack` | ストレージ層 | S3, Secrets Manager (Neo4j) |
| `ComputeStack` | コンピュート層 | Lambda×3, API Gateway |
| `FrontendStack` | フロント層 | S3, CloudFront |
| `PipelineStack` | CI/CD | CodePipeline, CodeBuild |

## 環境変数

| 変数 | 説明 | デフォルト |
|-----|------|-----------|
| `CDK_DEFAULT_ACCOUNT` | AWS アカウント ID | - |
| `CDK_DEFAULT_REGION` | リージョン | ap-northeast-1 |
| `NEO4J_SECRET_ARN` | Neo4j 接続情報シークレット ARN | 自動設定 |

## 💰 コスト概算

| 環境 | 月額 | 内訳 |
|-----|------|------|
| dev | **~$5-25** | Lambda (無料枠) + S3 + CloudFront |
| prod | **~$70-100** | Lambda + Neo4j AuraDB Pro (~$65) |

### コスト比較（Neptune vs Neo4j）

| サービス | 月額 | 備考 |
|---------|------|------|
| Neptune Serverless (1 NCU) | ~$166 | ❌ 廃止 |
| Neo4j AuraDB Free | $0 | 開発用 |
| Neo4j AuraDB Professional | ~$65〜 | 本番用 |

## 削除手順

```bash
# 全スタック削除
cd infra
cdk destroy --context env=dev --all

# 確認
aws cloudformation list-stacks --stack-status-filter DELETE_COMPLETE
```
