# Multimodal テストケース設計書

## 📋 概要

| 項目 | 内容 |
|------|------|
| **タスクID** | TASK-040 〜 TASK-046 |
| **目的** | AWS Nova シリーズを活用したマルチモーダル AI 機能の技術検証 |
| **アーキテクチャ** | **StrandsAgents + AgentCore** (Lambda + boto3 は不採用) |
| **対象モデル** | Nova Lite, Nova Pro, Nova Canvas, Nova Reel |
| **作成日** | 2026-01-02 |
| **更新日** | 2026-01-02 |

---

## ⚠️ 設計原則

```
┌─────────────────────────────────────────────────────────────────┐
│  Agentic エージェント開発基準                                    │
├─────────────────────────────────────────────────────────────────┤
│  ✅ 必須: AgentCore + StrandsAgents + BedrockAPI               │
│  ✅ 必須: AgentCore_Observability / CloudTrail 追跡可能        │
│  ✅ 必須: AgentCore_Memory + S3Vector (コスト最小)             │
│  ❌ 禁止: boto3 / cli / script / sh での直接処理               │
│  ❌ 禁止: OpenSearch (エンプラ規模でない場合)                   │
│  ⚠️ 許容: StrandsAgents に存在しないメソッドのみ手動実装        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 検証目標

### 機能別検証項目

| # | 機能 | 入力 | 出力 | StrandsAgents 対応 |
|---|------|------|------|-------------------|
| 1 | **画像理解** | 画像 + テキスト | テキスト | ✅ マルチモーダル対応 |
| 2 | **画像生成** | テキスト | 画像 | ✅ Tool として実装 |
| 3 | **動画理解** | 動画 + テキスト | テキスト | ✅ マルチモーダル対応 |
| 4 | **動画生成** | テキスト / 画像 | 動画 | ✅ Tool として実装 |
| 5 | **複合入力** | テキスト + 画像 + 動画 | テキスト | ✅ マルチモーダル対応 |

---

## 🏗️ システムアーキテクチャ

### StrandsAgents + AgentCore 構成

```
┌─────────────────────────────────────────────────────────────────┐
│                      Next.js Frontend                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Multimodal Tester                        │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐            │   │
│  │  │ 画像   │ │ 画像   │ │ 動画   │ │ 動画   │            │   │
│  │  │ 理解   │ │ 生成   │ │ 理解   │ │ 生成   │            │   │
│  │  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘            │   │
│  └──────┼──────────┼──────────┼──────────┼──────────────────┘   │
└─────────┼──────────┼──────────┼──────────┼──────────────────────┘
          │          │          │          │
          ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 AgentCore Gateway (API)                          │
│  POST /v1/agent/multimodal/invoke                               │
│  WebSocket /v1/agent/multimodal/stream                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AgentCore Runtime                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           StrandsAgents Multimodal Agent                 │    │
│  │                                                          │    │
│  │  ┌────────────────────────────────────────────────────┐ │    │
│  │  │  Model: Amazon Nova Pro (BedrockModel)             │ │    │
│  │  │  - Multimodal input (text, image, video)           │ │    │
│  │  │  - 200+ languages support                          │ │    │
│  │  └────────────────────────────────────────────────────┘ │    │
│  │                                                          │    │
│  │  ┌────────────────────────────────────────────────────┐ │    │
│  │  │  Tools (Toolbelt)                                  │ │    │
│  │  │  ├── image_generate (Nova Canvas)                  │ │    │
│  │  │  ├── video_generate (Nova Reel)                    │ │    │
│  │  │  ├── s3_upload (S3 操作)                           │ │    │
│  │  │  └── s3_download (S3 操作)                         │ │    │
│  │  └────────────────────────────────────────────────────┘ │    │
│  │                                                          │    │
│  │  ┌────────────────────────────────────────────────────┐ │    │
│  │  │  Memory: AgentCore Memory                          │ │    │
│  │  │  - Session memory (会話履歴)                       │ │    │
│  │  │  - Long-term memory (学習済み知識)                 │ │    │
│  │  └────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              AgentCore Observability                     │    │
│  │  - Step-by-step execution trace                         │    │
│  │  - CloudTrail integration                               │    │
│  │  - Custom scoring & metadata                            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AWS Services                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  Bedrock   │  │  S3        │  │ CloudTrail │                │
│  │  Nova      │  │  (Assets)  │  │  (Audit)   │                │
│  └────────────┘  └────────────┘  └────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🐍 StrandsAgents 実装設計

### ファイル構成

```
src/agents/
├── __init__.py
├── multimodal_agent.py      # Multimodal Agent 定義
├── tools/
│   ├── __init__.py
│   ├── image_generate.py    # Nova Canvas Tool
│   ├── video_generate.py    # Nova Reel Tool
│   └── s3_operations.py     # S3 操作 Tool
└── config.py                # AgentCore 設定
```

### multimodal_agent.py

```python
"""
Multimodal Agent using StrandsAgents SDK

AWS Nova Pro を使用したマルチモーダル AI エージェント。
AgentCore Runtime でホスト、AgentCore Memory で記憶管理。
"""

from strands import Agent
from strands.models import BedrockModel
from strands_tools import s3_tool

from .tools import image_generate_tool, video_generate_tool


# =============================================================================
# Model Configuration
# =============================================================================

model = BedrockModel(
    model_id="amazon.nova-pro-v1:0",
    region_name="ap-northeast-1",
    # マルチモーダル入力を有効化
    multimodal=True,
)


# =============================================================================
# System Prompt
# =============================================================================

SYSTEM_PROMPT = """あなたは AWS Nova を活用したマルチモーダル AI アシスタントです。

## 能力
- 画像の理解・分析（Nova Pro）
- 動画の理解・要約（Nova Pro）
- 画像の生成（Nova Canvas）
- 動画の生成（Nova Reel）

## 使用可能なツール
- image_generate: テキストから画像を生成
- video_generate: テキストから動画を生成
- s3_upload: ファイルを S3 にアップロード
- s3_download: S3 からファイルをダウンロード

## 指示
1. ユーザーの要求を理解し、適切な処理を行う
2. 画像/動画の理解は直接行い、生成はツールを使用
3. 結果は日本語で分かりやすく説明する
4. エラーが発生した場合は原因と対処法を説明する
"""


# =============================================================================
# Agent Definition
# =============================================================================

multimodal_agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[
        image_generate_tool,
        video_generate_tool,
        s3_tool,
    ],
)


# =============================================================================
# Entry Points
# =============================================================================

async def understand_image(image_data: bytes, prompt: str) -> str:
    """
    画像理解

    Args:
        image_data: 画像バイナリデータ
        prompt: ユーザープロンプト

    Returns:
        理解結果テキスト
    """
    response = await multimodal_agent.arun(
        prompt,
        images=[image_data],
    )
    return response.content


async def understand_video(video_s3_uri: str, prompt: str) -> str:
    """
    動画理解

    Args:
        video_s3_uri: 動画の S3 URI
        prompt: ユーザープロンプト

    Returns:
        理解結果テキスト
    """
    response = await multimodal_agent.arun(
        f"{prompt}\n\n動画: {video_s3_uri}",
        videos=[video_s3_uri],
    )
    return response.content


async def generate_image(prompt: str, **kwargs) -> dict:
    """
    画像生成

    Args:
        prompt: 生成プロンプト
        **kwargs: 追加パラメータ（width, height, etc.）

    Returns:
        生成結果（base64, s3_uri）
    """
    response = await multimodal_agent.arun(
        f"以下のプロンプトで画像を生成してください: {prompt}",
        tool_choice="image_generate",
    )
    return response.tool_results


async def generate_video(prompt: str, **kwargs) -> dict:
    """
    動画生成

    Args:
        prompt: 生成プロンプト
        **kwargs: 追加パラメータ

    Returns:
        生成結果（job_id, status）
    """
    response = await multimodal_agent.arun(
        f"以下のプロンプトで動画を生成してください: {prompt}",
        tool_choice="video_generate",
    )
    return response.tool_results
```

### tools/image_generate.py

```python
"""
Image Generation Tool using Nova Canvas

StrandsAgents Tool として Nova Canvas を呼び出す。
"""

from strands.tool import tool
from strands.models import BedrockModel
import json


@tool
def image_generate(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    num_images: int = 1,
    seed: int | None = None,
) -> dict:
    """
    Nova Canvas を使用して画像を生成します。

    Args:
        prompt: 生成する画像の説明
        negative_prompt: 生成から除外したい要素
        width: 画像の幅（ピクセル）
        height: 画像の高さ（ピクセル）
        num_images: 生成する画像の数
        seed: 再現性のためのシード値

    Returns:
        生成された画像情報（base64エンコード）
    """
    import boto3

    bedrock = boto3.client("bedrock-runtime", region_name="ap-northeast-1")

    request_body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {"text": prompt},
        "imageGenerationConfig": {
            "width": width,
            "height": height,
            "numberOfImages": num_images,
        },
    }

    if negative_prompt:
        request_body["textToImageParams"]["negativeText"] = negative_prompt
    if seed is not None:
        request_body["imageGenerationConfig"]["seed"] = seed

    response = bedrock.invoke_model(
        modelId="amazon.nova-canvas-v1:0",
        body=json.dumps(request_body),
        contentType="application/json",
        accept="application/json",
    )

    result = json.loads(response["body"].read())
    return {
        "images": [{"base64": img} for img in result.get("images", [])],
        "model": "amazon.nova-canvas-v1:0",
    }
```

### tools/video_generate.py

```python
"""
Video Generation Tool using Nova Reel

StrandsAgents Tool として Nova Reel を呼び出す（非同期）。
"""

from strands.tool import tool
import uuid


@tool
def video_generate(
    prompt: str,
    duration_seconds: int = 6,
    output_bucket: str = "rd-knowledge-multimodal-output",
) -> dict:
    """
    Nova Reel を使用して動画を生成します（非同期）。

    Args:
        prompt: 生成する動画の説明
        duration_seconds: 動画の長さ（秒）
        output_bucket: 出力先 S3 バケット

    Returns:
        ジョブ情報（job_id, status, status_url）
    """
    import boto3

    bedrock = boto3.client("bedrock-runtime", region_name="ap-northeast-1")
    job_id = str(uuid.uuid4())

    request_body = {
        "taskType": "TEXT_VIDEO",
        "textToVideoParams": {"text": prompt},
        "videoGenerationConfig": {
            "durationSeconds": duration_seconds,
            "fps": 24,
            "dimension": "1280x720",
            "seed": 12345,
        },
    }

    try:
        response = bedrock.start_async_invoke(
            modelId="amazon.nova-reel-v1:0",
            modelInput=request_body,
            outputDataConfig={
                "s3OutputDataConfig": {
                    "s3Uri": f"s3://{output_bucket}/generated/videos/{job_id}/",
                }
            },
        )

        return {
            "job_id": response.get("invocationArn", job_id),
            "status": "IN_PROGRESS",
            "status_url": f"/v1/multimodal/status/{response.get('invocationArn', job_id)}",
        }
    except Exception as e:
        return {
            "job_id": job_id,
            "status": "FAILED",
            "error": str(e),
        }
```

---

## 🚀 AgentCore デプロイ設定

### AgentCore Runtime 設定

```python
# src/agents/config.py

from strands_agentcore import AgentCoreRuntime, AgentCoreMemory

# AgentCore Runtime 設定
runtime_config = {
    "agent_name": "multimodal-agent",
    "region": "ap-northeast-1",
    "timeout_seconds": 300,  # 動画生成用に長め
    "max_payload_size_mb": 100,  # マルチモーダル対応
}

# AgentCore Memory 設定
memory_config = {
    "memory_id": "rd-knowledge-multimodal-memory",
    "strategies": [
        "session_summarizer",
        "preference_learner",
    ],
}

# 初期化
runtime = AgentCoreRuntime(**runtime_config)
memory = AgentCoreMemory(**memory_config)
```

### CDK デプロイ（AgentCore は SDK 経由で設定）

```typescript
// infra/lib/stacks/agentcore-stack.ts

import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";

export class AgentCoreStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Multimodal 出力用 S3 バケット
    const outputBucket = new s3.Bucket(this, "MultimodalOutputBucket", {
      bucketName: `rd-knowledge-multimodal-output-${this.account}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // AgentCore 用 IAM ロール
    const agentCoreRole = new iam.Role(this, "AgentCoreRole", {
      roleName: "rd-knowledge-agentcore-role",
      assumedBy: new iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
    });

    // Bedrock Nova アクセス権限
    agentCoreRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:StartAsyncInvoke",
          "bedrock:GetAsyncInvoke",
        ],
        resources: ["arn:aws:bedrock:ap-northeast-1::foundation-model/amazon.nova-*"],
      })
    );

    // S3 アクセス権限
    outputBucket.grantReadWrite(agentCoreRole);

    // CloudTrail 自動トレース（AgentCore Observability）
    // → AgentCore SDK 経由で自動設定

    new cdk.CfnOutput(this, "OutputBucketName", {
      value: outputBucket.bucketName,
      description: "Multimodal output S3 bucket",
    });
  }
}
```

---

## 🔧 API 設計（AgentCore Gateway 経由）

### エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| `POST` | `/v1/agent/multimodal/invoke` | 同期呼び出し |
| `WebSocket` | `/v1/agent/multimodal/stream` | ストリーミング |
| `GET` | `/v1/agent/multimodal/status/{jobId}` | 非同期ジョブ確認 |

### リクエスト例

```json
// POST /v1/agent/multimodal/invoke
{
  "message": "この画像に写っているものを説明してください",
  "attachments": [
    {
      "type": "image",
      "source": "base64",
      "data": "<base64_encoded_image>"
    }
  ],
  "session_id": "session-123"
}
```

### レスポンス例

```json
{
  "response": "この画像には富士山が写っています...",
  "usage": {
    "input_tokens": 150,
    "output_tokens": 200
  },
  "trace_id": "trace-abc123",
  "session_id": "session-123"
}
```

---

## 💰 コスト見積もり

### StrandsAgents + AgentCore 構成

| サービス | 月額コスト | 備考 |
|---------|----------|------|
| AgentCore Runtime | ~$50 | 従量課金（preview期間無料） |
| AgentCore Memory | ~$20 | セッション + 長期記憶 |
| Bedrock Nova Pro | ~$80 | 画像/動画理解 |
| Bedrock Nova Canvas | ~$20 | 画像生成 |
| Bedrock Nova Reel | ~$25 | 動画生成 |
| S3 | ~$5 | マルチモーダルアセット |
| **合計** | **~$200/月** | ※ 検証用途 |

※ Lambda + boto3 構成との比較: 開発工数が大幅削減、保守性向上

---

## ✅ 実装チェックリスト

### Phase 7 タスク（更新）

- [x] TASK-040: Nova Vision 調査・設計 (本ドキュメント)
- [ ] TASK-041: StrandsAgents Multimodal Agent 実装
- [ ] TASK-042: Image Generate Tool 実装
- [ ] TASK-043: Video Generate Tool 実装
- [ ] TASK-044: AgentCore Memory 統合
- [ ] TASK-045: AgentCore Runtime デプロイ設定
- [ ] TASK-046: Multimodal UI 実装

---

## 📚 参考リンク

### StrandsAgents
- [Strands Agents - AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-frameworks/strands-agents.html)
- [Strands Agents SDK GitHub](https://github.com/strands-agents/strands-agents-sdk)
- [Strands Agents 1.0 Announcement](https://aws.amazon.com/blogs/opensource/introducing-strands-agents-1-0-production-ready-multi-agent-orchestration-made-simple/)

### AgentCore
- [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html)
- [AgentCore Memory with Strands SDK](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/strands-sdk-memory.html)

### Amazon Nova
- [Amazon Nova User Guide](https://docs.aws.amazon.com/nova/latest/userguide/)
- [Multimodal support for Amazon Nova](https://docs.aws.amazon.com/nova/latest/userguide/modalities.html)
