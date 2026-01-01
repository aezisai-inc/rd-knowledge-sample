# rd-knowledge-sample Infrastructure

AWS CDK による Infrastructure as Code 定義

## 構成

```
infra/
├── bin/
│   └── app.ts                    # CDK エントリーポイント
├── lib/
│   ├── stacks/
│   │   ├── storage-stack.ts      # S3 Vectors / Bedrock KB / Neptune
│   │   ├── compute-stack.ts      # Lambda / API Gateway
│   │   ├── memory-stack.ts       # AgentCore Memory 設定
│   │   └── pipeline-stack.ts     # CodePipeline CI/CD
│   ├── constructs/
│   │   ├── vector-store.ts       # VectorStore Construct
│   │   ├── knowledge-base.ts     # Knowledge Base Construct
│   │   ├── memory-api.ts         # Memory API Construct
│   │   └── graph-store.ts        # Neptune Construct
│   └── config/
│       └── environments.ts       # 環境設定
├── lambda/
│   ├── memory-api/               # Memory API Lambda
│   ├── vector-api/               # Vector API Lambda
│   └── shared/                   # 共通ユーティリティ
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

## スタック構成

| スタック | 説明 | 主要リソース |
|---------|------|-------------|
| `StorageStack` | ストレージ層 | S3, Neptune Serverless |
| `ComputeStack` | コンピュート層 | Lambda, API Gateway |
| `MemoryStack` | メモリ層 | AgentCore Memory 設定 |
| `PipelineStack` | CI/CD | CodePipeline, CodeBuild |

## 環境変数

| 変数 | 説明 | デフォルト |
|-----|------|-----------|
| `CDK_DEFAULT_ACCOUNT` | AWS アカウント ID | - |
| `CDK_DEFAULT_REGION` | リージョン | us-west-2 |
| `ENVIRONMENT` | 環境名 (dev/prod) | dev |

## コスト概算

| 環境 | 月額 | 内訳 |
|-----|------|------|
| dev | ~$50 | Lambda (無料枠) + Neptune (最小NCU) |
| prod | ~$200+ | Lambda + Neptune (オートスケール) |

