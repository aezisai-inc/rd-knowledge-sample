# IAM ロール・ポリシー定義

本ドキュメントでは、Knowledge Sample プロジェクトで使用する各 AWS サービスへのアクセスに必要な IAM ロールとポリシーを定義します。

## 📋 目次

1. [概要](#概要)
2. [S3 Vectors 用ポリシー](#s3-vectors-用ポリシー)
3. [Bedrock Knowledge Base 用ポリシー](#bedrock-knowledge-base-用ポリシー)
4. [AgentCore Memory 用ポリシー](#agentcore-memory-用ポリシー)
5. [Neptune 用ポリシー](#neptune-用ポリシー)
6. [統合ロール定義](#統合ロール定義)
7. [CDK 実装サンプル](#cdk-実装サンプル)

---

## 概要

### 最小権限の原則

すべてのポリシーは**最小権限の原則**に基づいて設計されています：

- 必要なアクションのみを許可
- リソースは可能な限り特定
- 条件キーで追加の制限を適用

### 環境別の設定

```
環境変数: ENVIRONMENT = "development" | "staging" | "production"
```

| 環境 | リソース接頭辞 | 制限 |
|-----|-------------|------|
| development | `dev-*` | 開発者のみアクセス可 |
| staging | `stg-*` | テストチームアクセス可 |
| production | `prod-*` | 本番運用チームのみ |

---

## S3 Vectors 用ポリシー

### 読み取り専用ポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3VectorsReadOnly",
      "Effect": "Allow",
      "Action": [
        "s3vectors:GetVectorBucket",
        "s3vectors:ListVectorBuckets",
        "s3vectors:GetIndex",
        "s3vectors:ListIndexes",
        "s3vectors:QueryVectors",
        "s3vectors:GetVectors"
      ],
      "Resource": [
        "arn:aws:s3vectors:*:${AWS::AccountId}:vector-bucket/*"
      ]
    }
  ]
}
```

### 読み書きポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3VectorsFullAccess",
      "Effect": "Allow",
      "Action": [
        "s3vectors:CreateVectorBucket",
        "s3vectors:DeleteVectorBucket",
        "s3vectors:GetVectorBucket",
        "s3vectors:ListVectorBuckets",
        "s3vectors:CreateIndex",
        "s3vectors:DeleteIndex",
        "s3vectors:GetIndex",
        "s3vectors:ListIndexes",
        "s3vectors:PutVectors",
        "s3vectors:DeleteVectors",
        "s3vectors:QueryVectors",
        "s3vectors:GetVectors"
      ],
      "Resource": [
        "arn:aws:s3vectors:*:${AWS::AccountId}:vector-bucket/*"
      ]
    }
  ]
}
```

---

## Bedrock Knowledge Base 用ポリシー

### Knowledge Base 読み取りポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockKBRetrieve",
      "Effect": "Allow",
      "Action": [
        "bedrock:Retrieve",
        "bedrock:RetrieveAndGenerate"
      ],
      "Resource": [
        "arn:aws:bedrock:*:${AWS::AccountId}:knowledge-base/*"
      ]
    },
    {
      "Sid": "BedrockModelsInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
        "arn:aws:bedrock:*::foundation-model/amazon.titan-*"
      ]
    }
  ]
}
```

### Knowledge Base 管理ポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockKBManagement",
      "Effect": "Allow",
      "Action": [
        "bedrock:CreateKnowledgeBase",
        "bedrock:DeleteKnowledgeBase",
        "bedrock:GetKnowledgeBase",
        "bedrock:ListKnowledgeBases",
        "bedrock:UpdateKnowledgeBase",
        "bedrock:CreateDataSource",
        "bedrock:DeleteDataSource",
        "bedrock:GetDataSource",
        "bedrock:ListDataSources",
        "bedrock:StartIngestionJob",
        "bedrock:GetIngestionJob",
        "bedrock:ListIngestionJobs"
      ],
      "Resource": [
        "arn:aws:bedrock:*:${AWS::AccountId}:knowledge-base/*"
      ]
    },
    {
      "Sid": "S3DataSourceAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${DataSourceBucket}",
        "arn:aws:s3:::${DataSourceBucket}/*"
      ]
    }
  ]
}
```

---

## AgentCore Memory 用ポリシー

### Memory 読み書きポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AgentCoreMemoryAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:CreateMemory",
        "bedrock:DeleteMemory",
        "bedrock:GetMemory",
        "bedrock:ListMemories",
        "bedrock:CreateMemoryEvent",
        "bedrock:RetrieveMemoryRecords",
        "bedrock:DeleteMemoryRecords"
      ],
      "Resource": [
        "arn:aws:bedrock:*:${AWS::AccountId}:memory/*"
      ]
    },
    {
      "Sid": "AgentCoreControl",
      "Effect": "Allow",
      "Action": [
        "bedrock:CreateAgent",
        "bedrock:DeleteAgent",
        "bedrock:GetAgent",
        "bedrock:ListAgents",
        "bedrock:CreateAgentActionGroup",
        "bedrock:InvokeAgent"
      ],
      "Resource": [
        "arn:aws:bedrock:*:${AWS::AccountId}:agent/*"
      ]
    }
  ]
}
```

---

## Neptune 用ポリシー

### Neptune 読み取りポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "NeptuneDataRead",
      "Effect": "Allow",
      "Action": [
        "neptune-db:ReadDataViaQuery",
        "neptune-db:GetQueryStatus",
        "neptune-db:CancelQuery"
      ],
      "Resource": [
        "arn:aws:neptune-db:*:${AWS::AccountId}:${ClusterId}/*"
      ]
    }
  ]
}
```

### Neptune 読み書きポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "NeptuneDataReadWrite",
      "Effect": "Allow",
      "Action": [
        "neptune-db:ReadDataViaQuery",
        "neptune-db:WriteDataViaQuery",
        "neptune-db:DeleteDataViaQuery",
        "neptune-db:GetQueryStatus",
        "neptune-db:CancelQuery"
      ],
      "Resource": [
        "arn:aws:neptune-db:*:${AWS::AccountId}:${ClusterId}/*"
      ]
    }
  ]
}
```

---

## 統合ロール定義

### アプリケーション実行ロール

すべてのサービスにアクセスできる統合ロール：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AssumeRolePolicy",
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "lambda.amazonaws.com",
          "ecs-tasks.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### 信頼ポリシー（Lambda 用）

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

---

## CDK 実装サンプル

### TypeScript CDK スタック

```typescript
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export class KnowledgeSampleIamStack extends cdk.Stack {
  public readonly executionRole: iam.Role;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // S3 Vectors ポリシー
    const s3VectorsPolicy = new iam.PolicyStatement({
      sid: 'S3VectorsFullAccess',
      effect: iam.Effect.ALLOW,
      actions: [
        's3vectors:CreateVectorBucket',
        's3vectors:DeleteVectorBucket',
        's3vectors:GetVectorBucket',
        's3vectors:ListVectorBuckets',
        's3vectors:CreateIndex',
        's3vectors:DeleteIndex',
        's3vectors:GetIndex',
        's3vectors:ListIndexes',
        's3vectors:PutVectors',
        's3vectors:DeleteVectors',
        's3vectors:QueryVectors',
        's3vectors:GetVectors',
      ],
      resources: [`arn:aws:s3vectors:*:${this.account}:vector-bucket/*`],
    });

    // Bedrock Knowledge Base ポリシー
    const bedrockKBPolicy = new iam.PolicyStatement({
      sid: 'BedrockKBAccess',
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:Retrieve',
        'bedrock:RetrieveAndGenerate',
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
        'bedrock:CreateKnowledgeBase',
        'bedrock:DeleteKnowledgeBase',
        'bedrock:GetKnowledgeBase',
        'bedrock:ListKnowledgeBases',
      ],
      resources: [
        `arn:aws:bedrock:*:${this.account}:knowledge-base/*`,
        'arn:aws:bedrock:*::foundation-model/anthropic.claude-*',
        'arn:aws:bedrock:*::foundation-model/amazon.titan-*',
      ],
    });

    // AgentCore Memory ポリシー
    const agentCorePolicy = new iam.PolicyStatement({
      sid: 'AgentCoreMemoryAccess',
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:CreateMemory',
        'bedrock:DeleteMemory',
        'bedrock:GetMemory',
        'bedrock:ListMemories',
        'bedrock:CreateMemoryEvent',
        'bedrock:RetrieveMemoryRecords',
      ],
      resources: [`arn:aws:bedrock:*:${this.account}:memory/*`],
    });

    // Neptune ポリシー
    const neptunePolicy = new iam.PolicyStatement({
      sid: 'NeptuneAccess',
      effect: iam.Effect.ALLOW,
      actions: [
        'neptune-db:ReadDataViaQuery',
        'neptune-db:WriteDataViaQuery',
        'neptune-db:DeleteDataViaQuery',
        'neptune-db:GetQueryStatus',
      ],
      resources: [`arn:aws:neptune-db:*:${this.account}:*/*`],
    });

    // 実行ロール作成
    this.executionRole = new iam.Role(this, 'KnowledgeSampleExecutionRole', {
      roleName: 'KnowledgeSampleExecutionRole',
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal('lambda.amazonaws.com'),
        new iam.ServicePrincipal('ecs-tasks.amazonaws.com')
      ),
      description: 'Execution role for Knowledge Sample application',
    });

    // ポリシーをロールにアタッチ
    this.executionRole.addToPolicy(s3VectorsPolicy);
    this.executionRole.addToPolicy(bedrockKBPolicy);
    this.executionRole.addToPolicy(agentCorePolicy);
    this.executionRole.addToPolicy(neptunePolicy);

    // CloudWatch Logs ポリシー（Lambda 実行に必要）
    this.executionRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName(
        'service-role/AWSLambdaBasicExecutionRole'
      )
    );

    // 出力
    new cdk.CfnOutput(this, 'ExecutionRoleArn', {
      value: this.executionRole.roleArn,
      description: 'ARN of the execution role',
      exportName: 'KnowledgeSampleExecutionRoleArn',
    });
  }
}
```

### デプロイコマンド

```bash
# CDK Bootstrap（初回のみ）
cdk bootstrap aws://ACCOUNT_ID/REGION

# スタックデプロイ
cdk deploy KnowledgeSampleIamStack

# 差分確認
cdk diff KnowledgeSampleIamStack

# 削除
cdk destroy KnowledgeSampleIamStack
```

---

## セキュリティベストプラクティス

### 1. リソースベースのアクセス制御

```json
{
  "Condition": {
    "StringEquals": {
      "aws:ResourceTag/Environment": "${Environment}"
    }
  }
}
```

### 2. IP アドレス制限（オプション）

```json
{
  "Condition": {
    "IpAddress": {
      "aws:SourceIp": ["203.0.113.0/24"]
    }
  }
}
```

### 3. MFA 必須（機密操作）

```json
{
  "Condition": {
    "Bool": {
      "aws:MultiFactorAuthPresent": "true"
    }
  }
}
```

### 4. 時間制限アクセス

```json
{
  "Condition": {
    "DateGreaterThan": {"aws:CurrentTime": "2024-01-01T00:00:00Z"},
    "DateLessThan": {"aws:CurrentTime": "2024-12-31T23:59:59Z"}
  }
}
```

---

## 参考リンク

- [AWS IAM ベストプラクティス](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [Amazon Bedrock IAM ポリシー](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html)
- [Amazon Neptune IAM](https://docs.aws.amazon.com/neptune/latest/userguide/iam-auth.html)
- [AWS CDK IAM モジュール](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_iam-readme.html)

