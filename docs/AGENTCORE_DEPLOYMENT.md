# AgentCore Runtime デプロイガイド

## 概要

本ドキュメントでは、StrandsAgents ベースの Multimodal Agent を Amazon Bedrock AgentCore Runtime にデプロイする手順を説明します。

## 前提条件

### AWS アカウント設定
- AWS アカウントと適切な IAM 権限
- Amazon Bedrock で以下のモデルを有効化:
  - Amazon Nova Pro (`amazon.nova-pro-v1:0`)
  - Amazon Nova Canvas (`amazon.nova-canvas-v1:0`)
  - Amazon Nova Reel (`amazon.nova-reel-v1:0`)

### ローカル環境
- Python 3.12+
- AWS CLI 設定済み
- Docker (コンテナベースデプロイの場合)

## セットアップ

### 1. 依存パッケージのインストール

```bash
cd 40-research-develop/rd-knowledge-sample

# uv でパッケージ管理
uv sync

# AgentCore Starter Toolkit をインストール
uv add bedrock-agentcore-starter-toolkit
```

### 2. 環境変数の設定

```bash
export AWS_REGION=ap-northeast-1
export AWS_PROFILE=your-profile  # オプション
```

## デプロイ方法

### Option A: Direct Code Deployment (推奨)

Docker 不要のシンプルなデプロイ方法。

```bash
# 1. プロジェクト構造を確認
agentcore validate

# 2. ローカルテスト
agentcore dev

# 3. AWS にデプロイ
agentcore launch --mode direct

# 4. デプロイ確認
agentcore status
```

### Option B: Container Deployment

Docker コンテナを使用したデプロイ。

```bash
# 1. Dockerfile 生成
agentcore init --docker

# 2. ローカルビルド＆テスト
agentcore dev --docker

# 3. AWS にデプロイ
agentcore launch --mode container

# 4. デプロイ確認
agentcore status
```

## ローカル開発

### 開発サーバー起動

```bash
# デフォルト (http://localhost:8080)
agentcore dev

# ポート指定
agentcore dev --port 8000
```

### テストリクエスト

```bash
# テキストのみ
curl -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "こんにちは"}'

# 画像生成
curl -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "富士山と桜の風景を生成してください"}'
```

## AWS 操作

### エージェント呼び出し

```bash
# CLI
agentcore invoke --message "こんにちは"

# Python SDK
from bedrock_agentcore import AgentCoreClient

client = AgentCoreClient(region_name="ap-northeast-1")
response = client.invoke_agent_runtime(
    agent_arn="arn:aws:bedrock-agentcore:ap-northeast-1:ACCOUNT:agent/AGENT_ID",
    input={"message": "こんにちは"}
)
print(response["response"])
```

### リソース削除

```bash
agentcore destroy
```

## モニタリング

### CloudWatch Logs

```bash
# ログ確認
aws logs tail /aws/bedrock-agentcore/rd-knowledge-multimodal-agent --follow
```

### AgentCore Observability

AWS Console → Bedrock → AgentCore → Observability で以下を確認:
- 実行トレース
- ツール呼び出し履歴
- メモリ操作履歴
- エラーログ

## トラブルシューティング

### よくあるエラー

| エラー | 原因 | 対処 |
|-------|------|------|
| `AccessDeniedException` | IAM 権限不足 | Bedrock モデル・S3 権限を確認 |
| `ResourceNotFoundException` | モデル未有効化 | Bedrock コンソールでモデルを有効化 |
| `ValidationException` | 入力形式エラー | リクエスト形式を確認 |
| `ThrottlingException` | レート制限 | リトライ or クォータ引き上げ |

### デバッグモード

```bash
# 詳細ログを有効化
export LOG_LEVEL=DEBUG
agentcore dev
```

## コスト見積もり

| サービス | 月額概算 | 備考 |
|---------|---------|------|
| AgentCore Runtime | ~$50 | Preview 期間は無料 |
| AgentCore Memory | ~$20 | セッション数依存 |
| Bedrock Nova Pro | ~$80 | リクエスト数依存 |
| Bedrock Nova Canvas | ~$20 | 画像生成数依存 |
| Bedrock Nova Reel | ~$25 | 動画生成数依存 |
| S3 | ~$5 | ストレージ使用量 |
| **合計** | **~$200/月** | 検証用途の概算 |

## 参考リンク

- [AgentCore Runtime ドキュメント](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html)
- [AgentCore Starter Toolkit](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-toolkit.html)
- [Strands Agents SDK](https://strandsagents.com/)
- [Direct Code Deployment](https://aws.amazon.com/blogs/machine-learning/iterate-faster-with-amazon-bedrock-agentcore-runtime-direct-code-deployment/)

