#!/usr/bin/env node
/**
 * rd-knowledge-sample CDK Application
 *
 * スタック構成:
 * - StorageStack: S3, Neo4j (AuraDB)
 * - PipelineStack: CodePipeline CI/CD (optional)
 *
 * Note: Compute (Lambda, API Gateway) と Frontend (CloudFront) は
 * Amplify Gen2 (AppSync) に移行済み。
 *
 * グラフDB: Neptune Serverless → Neo4j AuraDB に移行
 * コスト削減: ~$166/月 → $0〜65/月
 */

import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { StorageStack } from "../lib/stacks/storage-stack";
import { PipelineStack } from "../lib/stacks/pipeline-stack";
import { getEnvironmentConfig } from "../lib/config/environments";

const app = new cdk.App();

// 環境設定の取得
const envName = app.node.tryGetContext("env") || "dev";
const config = getEnvironmentConfig(envName);

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT || config.account,
  region: process.env.CDK_DEFAULT_REGION || config.region,
};

// タグ設定
const tags = {
  Project: "rd-knowledge-sample",
  Environment: envName,
  ManagedBy: "CDK",
};

// =============================================================================
// Storage Stack
// =============================================================================
const storageStack = new StorageStack(app, `RdKnowledge-Storage-${envName}`, {
  env,
  config,
  tags,
  description: "rd-knowledge-sample Storage Layer (S3, Neo4j config)",
});

// =============================================================================
// Note: Compute Stack と Frontend Stack は Amplify Gen2 に移行
// - AppSync GraphQL API (Lambda Resolvers)
// - Amplify Hosting (Next.js SSR)
//
// ⚠️ frontend-stack.ts はロールバック用に保持
// 完全移行確認後に削除予定
// =============================================================================

// =============================================================================
// Pipeline Stack (CI/CD)
// =============================================================================
if (config.enablePipeline) {
  const pipelineStack = new PipelineStack(
    app,
    `RdKnowledge-Pipeline-${envName}`,
    {
      env,
      config,
      tags,
      description: "rd-knowledge-sample CI/CD Pipeline",
    }
  );
}

app.synth();

