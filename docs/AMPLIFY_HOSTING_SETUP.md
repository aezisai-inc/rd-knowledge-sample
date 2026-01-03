# Amplify Hosting 本番デプロイガイド

## 概要

このドキュメントでは、rd-knowledge-sample を Amplify Hosting にデプロイする手順を説明します。

## 前提条件

- AWS アカウントへのアクセス権限
- GitHub リポジトリへのアクセス権限
- AWS CLI がインストール済み

## デプロイ方法

### Option 1: AWS Console (推奨)

1. **Amplify Console へアクセス**
   ```
   https://ap-northeast-1.console.aws.amazon.com/amplify/home?region=ap-northeast-1
   ```

2. **新しいアプリを作成**
   - 「Create new app」をクリック
   - 「Host web app」を選択
   - GitHub を選択し、リポジトリを接続

3. **リポジトリ設定**
   - Repository: `aez-core`
   - Branch: `main`
   - App root: `40-research-develop/rd-knowledge-sample`

4. **ビルド設定**
   - `amplify.yml` が自動検出されます
   - ビルド設定を確認

5. **環境変数の設定**
   ```
   AGENTCORE_MEMORY_ID=<AgentCore Memory ID>
   OUTPUT_BUCKET=<S3 Bucket Name>
   NEO4J_URI=<Neo4j URI>
   NEO4J_USERNAME=<Neo4j Username>
   NEO4J_PASSWORD=<Neo4j Password>
   LOG_LEVEL=INFO
   ```

6. **デプロイ実行**
   - 「Save and deploy」をクリック

### Option 2: GitHub Actions (CI/CD)

1. **GitHub Secrets の設定**
   
   リポジトリの Settings > Secrets and variables > Actions で以下を設定:
   
   ```
   AWS_ROLE_ARN: arn:aws:iam::<account-id>:role/amplify-deploy-role
   AMPLIFY_APP_ID: <Amplify App ID>
   GRAPHQL_ENDPOINT: https://xxx.appsync-api.ap-northeast-1.amazonaws.com/graphql
   GRAPHQL_API_KEY: <API Key>
   ```

2. **OIDC プロバイダーの設定**
   
   GitHub Actions から AWS へのアクセスに OIDC を使用:
   
   ```bash
   aws iam create-open-id-connect-provider \
     --url https://token.actions.githubusercontent.com \
     --client-id-list sts.amazonaws.com \
     --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
   ```

3. **IAM ロールの作成**
   
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": {
             "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
           },
           "StringLike": {
             "token.actions.githubusercontent.com:sub": "repo:<org>/<repo>:*"
           }
         }
       }
     ]
   }
   ```

4. **プッシュでデプロイ**
   
   `main` ブランチへのプッシュで自動デプロイが実行されます。

## Sandbox から本番への移行

現在の Sandbox 環境:
- AppSync API: `https://xume65igfnemxeu3lwjorup3de.appsync-api.ap-northeast-1.amazonaws.com/graphql`
- API Key: `da2-djxjfyzfgbekpfwr74ajscj464`

**注意**: Sandbox は開発用環境です。本番環境では新しいスタックがデプロイされます。

## 検証済み機能

- ✅ Memory Resolver (AgentCore Memory)
- ✅ Agent Resolver (Bedrock Claude 3 Haiku)
- ✅ Vector Resolver (S3 Vector Search)
- ✅ Graph Resolver (DynamoDB/Neo4j)

## トラブルシューティング

### Nova モデルの inference profile エラー

```
ValidationException: Invocation of model ID amazon.nova-pro-v1:0 with on-demand throughput isn't supported.
```

**解決策**: Claude モデルを使用するか、Nova モデル用の inference profile を作成してください。

### CORS エラー

AppSync + Amplify Gen2 構成では CORS は自動的に処理されます。
カスタム設定が必要な場合は `app/amplify/data/resource.ts` を確認してください。

## リソースのクリーンアップ

Sandbox 環境の削除:
```bash
cd app && npx ampx sandbox --delete
```

本番環境の削除:
```bash
aws cloudformation delete-stack --stack-name amplify-<app-id>-<branch>-<hash>
```
