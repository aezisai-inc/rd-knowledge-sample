# Multimodal テストケース設計書

## 📋 概要

| 項目 | 内容 |
|------|------|
| **タスクID** | TASK-040 〜 TASK-046 |
| **目的** | AWS Nova シリーズを活用したマルチモーダル AI 機能の技術検証 |
| **対象モデル** | Nova Lite, Nova Pro, Nova Canvas, Nova Reel |
| **作成日** | 2026-01-02 |

---

## 🎯 検証目標

### 機能別検証項目

| # | 機能 | 入力 | 出力 | AWS サービス |
|---|------|------|------|-------------|
| 1 | **画像理解** | 画像 + テキスト | テキスト | Nova Pro / Nova Lite |
| 2 | **画像生成** | テキスト | 画像 | Nova Canvas |
| 3 | **動画理解** | 動画 + テキスト | テキスト | Nova Pro |
| 4 | **動画生成** | テキスト / 画像 | 動画 | Nova Reel |
| 5 | **複合入力** | テキスト + 画像 + 動画 | テキスト | Nova Pro |

---

## 🏗️ Amazon Nova モデルファミリー

### Understanding モデル（理解系）

| モデル | 特徴 | ユースケース | 価格帯 |
|--------|------|-------------|--------|
| **Nova Micro** | テキストのみ、最低遅延 | チャットボット、テキスト処理 | 最安 |
| **Nova Lite** | マルチモーダル、低コスト | 画像/動画/テキスト処理 | 低〜中 |
| **Nova Pro** | 高精度マルチモーダル | 複雑なタスク、高精度要求 | 中 |
| **Nova Premier** | 最高性能、マルチエージェント | 複雑な推論、教師モデル | 高 |

### Creative モデル（生成系）

| モデル | 特徴 | 出力形式 | 制限 |
|--------|------|---------|------|
| **Nova Canvas** | 画像生成・編集 | PNG/JPEG | 最大 4096x4096 |
| **Nova Reel** | 動画生成 | MP4 | 最大 2分、6秒クリップ |

---

## 📐 システムアーキテクチャ

### 全体構成

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
│                    API Gateway (REST)                            │
│  POST /v1/multimodal/understand    (画像/動画理解)               │
│  POST /v1/multimodal/generate      (画像/動画生成)               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Multimodal Lambda                              │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  handler.py                                             │     │
│  │  ├── understand_image()   # Nova Pro/Lite               │     │
│  │  ├── understand_video()   # Nova Pro                    │     │
│  │  ├── generate_image()     # Nova Canvas                 │     │
│  │  └── generate_video()     # Nova Reel                   │     │
│  └────────────────────────────────────────────────────────┘     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Bedrock    │  │   S3         │  │   S3         │
│   Runtime    │  │   (Input)    │  │   (Output)   │
│   (Nova)     │  │   Bucket     │  │   Bucket     │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 🔧 API 設計

### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| `POST` | `/v1/multimodal/understand` | 画像/動画理解 |
| `POST` | `/v1/multimodal/generate/image` | 画像生成 |
| `POST` | `/v1/multimodal/generate/video` | 動画生成 |
| `GET` | `/v1/multimodal/status/{jobId}` | 非同期ジョブ状態確認 |

### リクエスト/レスポンス仕様

#### 画像理解 API

```json
// POST /v1/multimodal/understand
// Request
{
  "type": "image",
  "prompt": "この画像に写っているものを説明してください",
  "image": {
    "source": "base64" | "s3",
    "data": "<base64_encoded_image>",  // source=base64 の場合
    "s3Uri": "s3://bucket/key"          // source=s3 の場合
  },
  "model": "nova-pro" | "nova-lite"
}

// Response
{
  "result": "この画像には...",
  "model": "amazon.nova-pro-v1:0",
  "usage": {
    "inputTokens": 150,
    "outputTokens": 200
  }
}
```

#### 動画理解 API

```json
// POST /v1/multimodal/understand
// Request
{
  "type": "video",
  "prompt": "この動画を要約してください",
  "video": {
    "s3Uri": "s3://bucket/video.mp4"
  },
  "model": "nova-pro"
}

// Response
{
  "result": "この動画では...",
  "model": "amazon.nova-pro-v1:0",
  "timestamps": [
    {"time": "00:00:05", "description": "..."},
    {"time": "00:00:15", "description": "..."}
  ]
}
```

#### 画像生成 API

```json
// POST /v1/multimodal/generate/image
// Request
{
  "prompt": "夕日に照らされた富士山の美しい風景",
  "negativePrompt": "低品質、ぼやけた",
  "width": 1024,
  "height": 1024,
  "numberOfImages": 1,
  "seed": 12345
}

// Response
{
  "images": [
    {
      "base64": "<base64_encoded_image>",
      "s3Uri": "s3://output-bucket/generated/xxx.png"
    }
  ],
  "model": "amazon.nova-canvas-v1:0"
}
```

#### 動画生成 API

```json
// POST /v1/multimodal/generate/video
// Request
{
  "prompt": "海辺で波が打ち寄せる様子",
  "durationSeconds": 6,
  "fps": 24,
  "dimension": "1280x720"
}

// Response (非同期)
{
  "jobId": "job-12345",
  "status": "IN_PROGRESS",
  "statusUrl": "/v1/multimodal/status/job-12345"
}

// GET /v1/multimodal/status/job-12345
// Response (完了時)
{
  "jobId": "job-12345",
  "status": "COMPLETED",
  "video": {
    "s3Uri": "s3://output-bucket/generated/xxx.mp4",
    "durationSeconds": 6
  }
}
```

---

## 📂 ファイル形式・制限

### 入力ファイル形式

| コンテンツタイプ | 対応形式 | 最大サイズ | 入力方法 |
|----------------|---------|----------|---------|
| **画像** | PNG, JPG, JPEG, GIF, WebP | 25MB (Base64), 1GB (S3) | Base64 / S3 URI |
| **動画** | MP4, MOV, MKV, WebM, FLV, MPEG, WMV, 3GP | 25MB (Base64), 1GB (S3) | Base64 / S3 URI |
| **ドキュメント** | PDF, DOCX, CSV, XLS, HTML, TXT, MD | 25MB | Bytes / S3 URI |

### 出力制限

| 機能 | 制限 |
|------|------|
| **Nova Canvas (画像生成)** | 最大 4096x4096 px |
| **Nova Reel (動画生成)** | 最大 2分、6秒クリップ単位 |
| **動画サンプリング** | 1 FPS (16分以下)、960フレーム固定 (16分超) |

---

## 🐍 Lambda 実装設計

### ファイル構成

```
infra/lambda/multimodal-api/
├── handler.py           # メインハンドラー
├── understand.py        # 画像/動画理解ロジック
├── generate.py          # 画像/動画生成ロジック
├── s3_utils.py          # S3 操作ユーティリティ
└── requirements.txt     # 依存関係
```

### handler.py 骨格

```python
"""
Multimodal API Lambda Handler

AWS Nova を使用したマルチモーダル処理。
"""

import json
import logging
import os
import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

bedrock_runtime = boto3.client("bedrock-runtime", region_name="ap-northeast-1")
s3_client = boto3.client("s3")


def lambda_handler(event: dict, context) -> dict:
    """Lambda エントリーポイント"""
    path = event.get("path", "")
    method = event.get("httpMethod", "GET")
    body = json.loads(event.get("body") or "{}")

    try:
        if path.endswith("/understand") and method == "POST":
            return handle_understand(body)
        elif path.endswith("/generate/image") and method == "POST":
            return handle_generate_image(body)
        elif path.endswith("/generate/video") and method == "POST":
            return handle_generate_video(body)
        elif "/status/" in path and method == "GET":
            job_id = path.split("/")[-1]
            return handle_status(job_id)
        else:
            return response(404, {"error": "Not Found"})
    except Exception as e:
        logger.exception(f"Error: {e}")
        return response(500, {"error": str(e)})


def handle_understand(body: dict) -> dict:
    """画像/動画理解"""
    content_type = body.get("type", "image")
    prompt = body.get("prompt", "")
    model_id = get_model_id(body.get("model", "nova-pro"))

    if content_type == "image":
        image_data = body.get("image", {})
        result = understand_image(model_id, prompt, image_data)
    elif content_type == "video":
        video_data = body.get("video", {})
        result = understand_video(model_id, prompt, video_data)
    else:
        return response(400, {"error": f"Unknown type: {content_type}"})

    return response(200, result)


def handle_generate_image(body: dict) -> dict:
    """画像生成 (Nova Canvas)"""
    prompt = body.get("prompt", "")
    negative_prompt = body.get("negativePrompt", "")
    width = body.get("width", 1024)
    height = body.get("height", 1024)
    num_images = body.get("numberOfImages", 1)
    seed = body.get("seed")

    result = generate_image(prompt, negative_prompt, width, height, num_images, seed)
    return response(200, result)


def handle_generate_video(body: dict) -> dict:
    """動画生成 (Nova Reel) - 非同期"""
    prompt = body.get("prompt", "")
    duration = body.get("durationSeconds", 6)

    job_id = start_video_generation(prompt, duration)
    return response(202, {
        "jobId": job_id,
        "status": "IN_PROGRESS",
        "statusUrl": f"/v1/multimodal/status/{job_id}"
    })


def handle_status(job_id: str) -> dict:
    """非同期ジョブ状態確認"""
    status = get_job_status(job_id)
    return response(200, status)


def get_model_id(model: str) -> str:
    """モデル名からモデルIDを取得"""
    models = {
        "nova-micro": "amazon.nova-micro-v1:0",
        "nova-lite": "amazon.nova-lite-v1:0",
        "nova-pro": "amazon.nova-pro-v1:0",
        "nova-premier": "amazon.nova-premier-v1:0",
        "nova-canvas": "amazon.nova-canvas-v1:0",
        "nova-reel": "amazon.nova-reel-v1:0",
    }
    return models.get(model, "amazon.nova-pro-v1:0")


def response(status_code: int, body: dict) -> dict:
    """API Gateway レスポンス"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }


# === 理解系処理 ===

def understand_image(model_id: str, prompt: str, image_data: dict) -> dict:
    """画像理解"""
    # 画像ソースの準備
    source = image_data.get("source", "base64")
    
    if source == "base64":
        image_content = {
            "image": {
                "format": "png",
                "source": {"bytes": image_data.get("data", "")}
            }
        }
    else:
        image_content = {
            "image": {
                "format": "png",
                "source": {"s3Location": {"uri": image_data.get("s3Uri", "")}}
            }
        }

    # Bedrock Runtime API 呼び出し
    response = bedrock_runtime.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    image_content,
                    {"text": prompt}
                ]
            }
        ]
    )

    return {
        "result": response["output"]["message"]["content"][0]["text"],
        "model": model_id,
        "usage": response.get("usage", {})
    }


def understand_video(model_id: str, prompt: str, video_data: dict) -> dict:
    """動画理解"""
    s3_uri = video_data.get("s3Uri", "")
    
    response = bedrock_runtime.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "video": {
                            "format": "mp4",
                            "source": {"s3Location": {"uri": s3_uri}}
                        }
                    },
                    {"text": prompt}
                ]
            }
        ]
    )

    return {
        "result": response["output"]["message"]["content"][0]["text"],
        "model": model_id,
        "usage": response.get("usage", {})
    }


# === 生成系処理 ===

def generate_image(prompt: str, negative_prompt: str, width: int, height: int, num_images: int, seed: int = None) -> dict:
    """画像生成 (Nova Canvas)"""
    model_id = "amazon.nova-canvas-v1:0"
    
    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": prompt,
            "negativeText": negative_prompt,
        },
        "imageGenerationConfig": {
            "width": width,
            "height": height,
            "numberOfImages": num_images,
        }
    }
    
    if seed is not None:
        body["imageGenerationConfig"]["seed"] = seed

    response = bedrock_runtime.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json"
    )

    result = json.loads(response["body"].read())
    
    return {
        "images": [{"base64": img} for img in result.get("images", [])],
        "model": model_id
    }


def start_video_generation(prompt: str, duration: int) -> str:
    """動画生成開始 (非同期)"""
    model_id = "amazon.nova-reel-v1:0"
    output_bucket = os.environ.get("OUTPUT_BUCKET", "rd-knowledge-multimodal-output")
    
    import uuid
    job_id = str(uuid.uuid4())
    
    body = {
        "taskType": "TEXT_VIDEO",
        "textToVideoParams": {
            "text": prompt,
        },
        "videoGenerationConfig": {
            "durationSeconds": duration,
            "fps": 24,
            "dimension": "1280x720",
            "seed": 12345,
        }
    }

    # StartAsyncInvoke で非同期実行
    response = bedrock_runtime.start_async_invoke(
        modelId=model_id,
        modelInput=body,
        outputDataConfig={
            "s3OutputDataConfig": {
                "s3Uri": f"s3://{output_bucket}/generated/{job_id}/"
            }
        }
    )
    
    return response.get("invocationArn", job_id)


def get_job_status(job_id: str) -> dict:
    """非同期ジョブ状態取得"""
    try:
        response = bedrock_runtime.get_async_invoke(
            invocationArn=job_id
        )
        
        status = response.get("status", "UNKNOWN")
        result = {"jobId": job_id, "status": status}
        
        if status == "Completed":
            result["video"] = {
                "s3Uri": response.get("outputDataConfig", {}).get("s3OutputDataConfig", {}).get("s3Uri", "")
            }
        elif status == "Failed":
            result["error"] = response.get("failureMessage", "Unknown error")
            
        return result
    except Exception as e:
        return {"jobId": job_id, "status": "UNKNOWN", "error": str(e)}
```

---

## 🎨 フロントエンド UI 設計

### コンポーネント構成

```
app/components/Multimodal/
├── MultimodalTester.tsx      # メインコンポーネント
├── ImageUnderstand.tsx       # 画像理解パネル
├── ImageGenerate.tsx         # 画像生成パネル
├── VideoUnderstand.tsx       # 動画理解パネル
├── VideoGenerate.tsx         # 動画生成パネル
├── FileUploader.tsx          # ファイルアップロード
├── ResultDisplay.tsx         # 結果表示
└── index.ts                  # エクスポート
```

### UI ワイヤーフレーム

```
┌─────────────────────────────────────────────────────────────┐
│  🎨 Multimodal Tester                                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ 画像理解 │ │ 画像生成 │ │ 動画理解 │ │ 動画生成 │           │
│  │ (Active)│ │         │ │         │ │         │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  📤 ファイルアップロード                              │   │
│  │  ┌───────────────────────────────────────────────┐   │   │
│  │  │                                               │   │   │
│  │  │   ドラッグ&ドロップ または クリックで選択      │   │   │
│  │  │                                               │   │   │
│  │  └───────────────────────────────────────────────┘   │   │
│  │                                                       │   │
│  │  プロンプト: [_________________________________]      │   │
│  │                                                       │   │
│  │  [🚀 実行]                                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  📊 結果                                             │   │
│  │  ┌───────────────────────────────────────────────┐   │   │
│  │  │  [画像/動画プレビュー]                         │   │   │
│  │  └───────────────────────────────────────────────┘   │   │
│  │                                                       │   │
│  │  説明: この画像には...                                │   │
│  │                                                       │   │
│  │  使用トークン: 入力 150 / 出力 200                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 💰 コスト見積もり

### Nova モデル価格 (ap-northeast-1)

| モデル | 入力 (1K tokens) | 出力 (1K tokens) | 画像 (1枚) |
|--------|-----------------|-----------------|-----------|
| Nova Micro | $0.000035 | $0.00014 | - |
| Nova Lite | $0.00006 | $0.00024 | - |
| Nova Pro | $0.0008 | $0.0032 | - |
| Nova Canvas | - | - | $0.04 |
| Nova Reel | - | - | $0.08/秒 |

### 月額見積もり（検証用途）

| 項目 | 使用量 | 月額コスト |
|------|-------|----------|
| 画像理解 (Nova Pro) | 1,000回 | ~$5 |
| 動画理解 (Nova Pro) | 100回 | ~$30 |
| 画像生成 (Nova Canvas) | 500枚 | ~$20 |
| 動画生成 (Nova Reel) | 50回 (6秒) | ~$24 |
| S3 ストレージ | 10GB | ~$0.25 |
| Lambda | 10,000回 | ~$1 |
| API Gateway | 10,000回 | ~$0.35 |
| **合計** | | **~$80/月** |

---

## 🔐 IAM ポリシー

### Lambda 実行ロール追加ポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:StartAsyncInvoke",
        "bedrock:GetAsyncInvoke"
      ],
      "Resource": [
        "arn:aws:bedrock:ap-northeast-1::foundation-model/amazon.nova-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::rd-knowledge-multimodal-*",
        "arn:aws:s3:::rd-knowledge-multimodal-*/*"
      ]
    }
  ]
}
```

---

## ✅ 実装チェックリスト

### Phase 7 タスク

- [x] TASK-040: Nova Vision 調査・設計 (本ドキュメント)
- [ ] TASK-041: 画像認識 Lambda 実装
- [ ] TASK-042: 画像生成 Lambda 実装
- [ ] TASK-043: 動画認識 Lambda 実装
- [ ] TASK-044: 動画生成 Lambda 実装
- [ ] TASK-045: Multimodal CDK 更新
- [ ] TASK-046: Multimodal UI 実装

---

## 📚 参考リンク

- [Amazon Nova User Guide](https://docs.aws.amazon.com/nova/latest/userguide/)
- [Multimodal support for Amazon Nova](https://docs.aws.amazon.com/nova/latest/userguide/modalities.html)
- [Vision understanding prompting best practices](https://docs.aws.amazon.com/nova/latest/userguide/prompting-video-understanding.html)
- [Amazon Bedrock Knowledge Bases - Multimodal](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-multimodal.html)
- [Nova Canvas (画像生成)](https://docs.aws.amazon.com/nova/latest/userguide/image-gen-access.html)
- [Nova Reel (動画生成)](https://docs.aws.amazon.com/nova/latest/userguide/video-generation.html)

