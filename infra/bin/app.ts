#!/usr/bin/env node
/**
 * rd-knowledge-sample CDK Application
 *
 * スタック構成:
 * - StorageStack: S3, Neptune Serverless
 * - ComputeStack: Lambda, API Gateway
 * - PipelineStack: CodePipeline CI/CD
 */

import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { StorageStack } from "../lib/stacks/storage-stack";
import { ComputeStack } from "../lib/stacks/compute-stack";
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
  description: "rd-knowledge-sample Storage Layer (S3, Neptune)",
});

// =============================================================================
// Compute Stack
// =============================================================================
const computeStack = new ComputeStack(app, `RdKnowledge-Compute-${envName}`, {
  env,
  config,
  tags,
  storageStack,
  description: "rd-knowledge-sample Compute Layer (Lambda, API Gateway)",
});

computeStack.addDependency(storageStack);

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

