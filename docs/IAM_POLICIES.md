# IAM ロール・ポリシー定義

rd-knowledge-sample プロジェクトで使用する AWS サービスへのアクセスに必要な IAM ロール・ポリシーの定義です。

## 概要

| サービス | 必要な権限 | 推定コスト |
|----------|-----------|-----------|
| S3 Vectors | s3vectors:* | プレビュー期間無料 |
| Bedrock Knowledge Base | bedrock:*, bedrock-agent:*, bedrock-agent-runtime:* | 使用量課金 |
| AgentCore Memory | bedrock-agentcore:*, bedrock-agentcore-control:* | 使用量課金 |
| Neptune Serverless | neptune-db:* | ~$0.1/NCU時間 |
| S3 (データソース) | s3:GetObject, s3:ListBucket | ~$0.023/GB |

---

## 1. S3 Vectors アクセスポリシー

### 最小権限ポリシー

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "S3VectorsReadWrite",
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
                "s3vectors:GetVectors",
                "s3vectors:DeleteVectors",
                "s3vectors:QueryVectors"
            ],
            "Resource": [
                "arn:aws:s3vectors:*:${AWS::AccountId}:vector-bucket/*"
            ]
        }
    ]
}
```

### CDK 実装例

```typescript
import * as iam from 'aws-cdk-lib/aws-iam';

const s3VectorsPolicy = new iam.PolicyStatement({
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
    's3vectors:GetVectors',
    's3vectors:DeleteVectors',
    's3vectors:QueryVectors',
  ],
  resources: [`arn:aws:s3vectors:*:${this.account}:vector-bucket/*`],
});
```

---

## 2. Bedrock Knowledge Base アクセスポリシー

### 最小権限ポリシー

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockKnowledgeBaseManagement",
            "Effect": "Allow",
            "Action": [
                "bedrock:CreateKnowledgeBase",
                "bedrock:DeleteKnowledgeBase",
                "bedrock:GetKnowledgeBase",
                "bedrock:ListKnowledgeBases",
                "bedrock:UpdateKnowledgeBase"
            ],
            "Resource": [
                "arn:aws:bedrock:*:${AWS::AccountId}:knowledge-base/*"
            ]
        },
        {
            "Sid": "BedrockAgentDataSourceManagement",
            "Effect": "Allow",
            "Action": [
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
            "Sid": "BedrockAgentRuntimeRetrieve",
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
            "Sid": "BedrockFoundationModelInvoke",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/*"
            ]
        }
    ]
}
```

### CDK 実装例

```typescript
import * as iam from 'aws-cdk-lib/aws-iam';

const bedrockKbPolicy = new iam.PolicyDocument({
  statements: [
    new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:CreateKnowledgeBase',
        'bedrock:DeleteKnowledgeBase',
        'bedrock:GetKnowledgeBase',
        'bedrock:ListKnowledgeBases',
        'bedrock:UpdateKnowledgeBase',
        'bedrock:CreateDataSource',
        'bedrock:DeleteDataSource',
        'bedrock:GetDataSource',
        'bedrock:ListDataSources',
        'bedrock:StartIngestionJob',
        'bedrock:GetIngestionJob',
        'bedrock:ListIngestionJobs',
      ],
      resources: [`arn:aws:bedrock:*:${this.account}:knowledge-base/*`],
    }),
    new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:Retrieve',
        'bedrock:RetrieveAndGenerate',
      ],
      resources: [`arn:aws:bedrock:*:${this.account}:knowledge-base/*`],
    }),
    new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
      ],
      resources: ['arn:aws:bedrock:*::foundation-model/*'],
    }),
  ],
});
```

---

## 3. AgentCore Memory アクセスポリシー

### 最小権限ポリシー

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AgentCoreMemoryControl",
            "Effect": "Allow",
            "Action": [
                "bedrock:CreateMemory",
                "bedrock:DeleteMemory",
                "bedrock:GetMemory",
                "bedrock:ListMemories",
                "bedrock:UpdateMemory"
            ],
            "Resource": [
                "arn:aws:bedrock:*:${AWS::AccountId}:memory/*"
            ]
        },
        {
            "Sid": "AgentCoreMemoryData",
            "Effect": "Allow",
            "Action": [
                "bedrock:CreateEvent",
                "bedrock:RetrieveMemoryRecords",
                "bedrock:GetSessionSummary"
            ],
            "Resource": [
                "arn:aws:bedrock:*:${AWS::AccountId}:memory/*"
            ]
        }
    ]
}
```

### CDK 実装例

```typescript
import * as iam from 'aws-cdk-lib/aws-iam';

const agentCoreMemoryPolicy = new iam.PolicyDocument({
  statements: [
    new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:CreateMemory',
        'bedrock:DeleteMemory',
        'bedrock:GetMemory',
        'bedrock:ListMemories',
        'bedrock:UpdateMemory',
        'bedrock:CreateEvent',
        'bedrock:RetrieveMemoryRecords',
        'bedrock:GetSessionSummary',
      ],
      resources: [`arn:aws:bedrock:*:${this.account}:memory/*`],
    }),
  ],
});
```

---

## 4. Neptune Serverless アクセスポリシー

### 最小権限ポリシー

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "NeptuneServerlessAccess",
            "Effect": "Allow",
            "Action": [
                "neptune-db:connect",
                "neptune-db:ReadDataViaQuery",
                "neptune-db:WriteDataViaQuery",
                "neptune-db:DeleteDataViaQuery",
                "neptune-db:GetQueryStatus",
                "neptune-db:CancelQuery"
            ],
            "Resource": [
                "arn:aws:neptune-db:*:${AWS::AccountId}:*/*"
            ]
        },
        {
            "Sid": "NeptuneManagement",
            "Effect": "Allow",
            "Action": [
                "rds:DescribeDBClusters",
                "rds:DescribeDBInstances"
            ],
            "Resource": [
                "arn:aws:rds:*:${AWS::AccountId}:cluster:*",
                "arn:aws:rds:*:${AWS::AccountId}:db:*"
            ]
        }
    ]
}
```

### CDK 実装例

```typescript
import * as iam from 'aws-cdk-lib/aws-iam';

const neptunePolicy = new iam.PolicyDocument({
  statements: [
    new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'neptune-db:connect',
        'neptune-db:ReadDataViaQuery',
        'neptune-db:WriteDataViaQuery',
        'neptune-db:DeleteDataViaQuery',
        'neptune-db:GetQueryStatus',
        'neptune-db:CancelQuery',
      ],
      resources: [`arn:aws:neptune-db:*:${this.account}:*/*`],
    }),
    new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'rds:DescribeDBClusters',
        'rds:DescribeDBInstances',
      ],
      resources: [
        `arn:aws:rds:*:${this.account}:cluster:*`,
        `arn:aws:rds:*:${this.account}:db:*`,
      ],
    }),
  ],
});
```

---

## 5. S3 データソースアクセスポリシー

Bedrock Knowledge Base のデータソースとして S3 バケットを使用する場合に必要なポリシーです。

### 最小権限ポリシー

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "S3DataSourceRead",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::${DataSourceBucketName}",
                "arn:aws:s3:::${DataSourceBucketName}/*"
            ]
        }
    ]
}
```

---

## 6. 統合ロール定義

### rd-knowledge-sample 用の統合ロール

```typescript
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';

export class RdKnowledgeSampleIamStack extends cdk.Stack {
  public readonly executionRole: iam.Role;

  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Lambda/ECS 実行ロール
    this.executionRole = new iam.Role(this, 'RdKnowledgeSampleExecutionRole', {
      roleName: 'rd-knowledge-sample-execution-role',
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal('lambda.amazonaws.com'),
        new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      ),
      description: 'Execution role for rd-knowledge-sample services',
    });

    // CloudWatch Logs 権限
    this.executionRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: ['*'],
    }));

    // S3 Vectors 権限
    this.executionRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        's3vectors:*',
      ],
      resources: [`arn:aws:s3vectors:*:${this.account}:vector-bucket/*`],
    }));

    // Bedrock Knowledge Base 権限
    this.executionRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:CreateKnowledgeBase',
        'bedrock:DeleteKnowledgeBase',
        'bedrock:GetKnowledgeBase',
        'bedrock:ListKnowledgeBases',
        'bedrock:UpdateKnowledgeBase',
        'bedrock:CreateDataSource',
        'bedrock:DeleteDataSource',
        'bedrock:GetDataSource',
        'bedrock:ListDataSources',
        'bedrock:StartIngestionJob',
        'bedrock:GetIngestionJob',
        'bedrock:ListIngestionJobs',
        'bedrock:Retrieve',
        'bedrock:RetrieveAndGenerate',
      ],
      resources: [`arn:aws:bedrock:*:${this.account}:knowledge-base/*`],
    }));

    // Bedrock Foundation Model 権限
    this.executionRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
      ],
      resources: ['arn:aws:bedrock:*::foundation-model/*'],
    }));

    // AgentCore Memory 権限
    this.executionRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:CreateMemory',
        'bedrock:DeleteMemory',
        'bedrock:GetMemory',
        'bedrock:ListMemories',
        'bedrock:UpdateMemory',
        'bedrock:CreateEvent',
        'bedrock:RetrieveMemoryRecords',
        'bedrock:GetSessionSummary',
      ],
      resources: [`arn:aws:bedrock:*:${this.account}:memory/*`],
    }));

    // Neptune 権限
    this.executionRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'neptune-db:connect',
        'neptune-db:ReadDataViaQuery',
        'neptune-db:WriteDataViaQuery',
        'neptune-db:DeleteDataViaQuery',
      ],
      resources: [`arn:aws:neptune-db:*:${this.account}:*/*`],
    }));

    // 出力
    new cdk.CfnOutput(this, 'ExecutionRoleArn', {
      value: this.executionRole.roleArn,
      description: 'ARN of the execution role',
      exportName: 'RdKnowledgeSampleExecutionRoleArn',
    });
  }
}
```

---

## 7. セキュリティベストプラクティス

### 7.1 最小権限の原則

- 必要なアクションのみを許可
- リソース ARN を具体的に指定
- ワイルドカード (`*`) の使用を最小限に

### 7.2 条件キーの活用

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "bedrock:InvokeModel",
            "Resource": "arn:aws:bedrock:*::foundation-model/*",
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": ["us-west-2", "us-east-1"]
                }
            }
        }
    ]
}
```

### 7.3 タグベースのアクセス制御

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "bedrock:*",
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:ResourceTag/Project": "rd-knowledge-sample"
                }
            }
        }
    ]
}
```

---

## 8. コスト管理

### 8.1 予算アラート設定

```typescript
import * as budgets from 'aws-cdk-lib/aws-budgets';

new budgets.CfnBudget(this, 'MonthlyBudget', {
  budget: {
    budgetName: 'rd-knowledge-sample-monthly',
    budgetType: 'COST',
    timeUnit: 'MONTHLY',
    budgetLimit: {
      amount: 100,
      unit: 'USD',
    },
  },
  notificationsWithSubscribers: [
    {
      notification: {
        notificationType: 'ACTUAL',
        comparisonOperator: 'GREATER_THAN',
        threshold: 80,
        thresholdType: 'PERCENTAGE',
      },
      subscribers: [
        {
          subscriptionType: 'EMAIL',
          address: 'your-email@example.com',
        },
      ],
    },
  ],
});
```

### 8.2 サービス別コスト配分タグ

全リソースに以下のタグを付与することを推奨：

```typescript
const tags = {
  Project: 'rd-knowledge-sample',
  Environment: 'development',
  CostCenter: 'research',
};
```

