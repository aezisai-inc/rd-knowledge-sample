/**
 * Pipeline Stack
 *
 * CodePipeline CI/CD を定義
 */

import * as cdk from "aws-cdk-lib";
import * as codepipeline from "aws-cdk-lib/aws-codepipeline";
import * as codepipeline_actions from "aws-cdk-lib/aws-codepipeline-actions";
import * as codebuild from "aws-cdk-lib/aws-codebuild";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";
import { EnvironmentConfig } from "../config/environments";

export interface PipelineStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  tags: Record<string, string>;
}

export class PipelineStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: PipelineStackProps) {
    super(scope, id, props);

    const { config } = props;

    if (!config.github) {
      throw new Error("GitHub configuration is required for Pipeline stack");
    }

    // =========================================================================
    // Artifact Bucket
    // =========================================================================
    const artifactBucket = new s3.Bucket(this, "ArtifactBucket", {
      bucketName: `rd-knowledge-artifacts-${config.envName}-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      lifecycleRules: [
        {
          id: "cleanup-old-artifacts",
          expiration: cdk.Duration.days(30),
        },
      ],
    });

    // =========================================================================
    // CodeBuild Project - Test
    // =========================================================================
    const testProject = new codebuild.PipelineProject(this, "TestProject", {
      projectName: `rd-knowledge-test-${config.envName}`,
      description: "Run tests for rd-knowledge-sample",
      environment: {
        buildImage: codebuild.LinuxBuildImage.AMAZON_LINUX_2_ARM_3,
        computeType: codebuild.ComputeType.SMALL,
        privileged: true, // Docker 使用のため
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: "0.2",
        phases: {
          install: {
            "runtime-versions": {
              python: "3.12",
              nodejs: "20",
            },
            commands: [
              "pip install uv",
              "uv sync",
              "cd infra && npm ci",
            ],
          },
          pre_build: {
            commands: [
              "echo 'Starting Docker services...'",
              "docker-compose -f docker-compose.local.yml up -d chromadb redis",
              "sleep 10",
            ],
          },
          build: {
            commands: [
              "echo 'Running Python linting...'",
              "uv run ruff check src/ tests/",
              "echo 'Running Python type checking...'",
              "uv run mypy src/ --ignore-missing-imports || true",
              "echo 'Running tests...'",
              "uv run pytest tests/ -v --tb=short --environment=local",
              "echo 'Running CDK synth...'",
              "cd infra && npm run synth -- --context env=${ENVIRONMENT}",
            ],
          },
          post_build: {
            commands: [
              "docker-compose -f docker-compose.local.yml down",
            ],
          },
        },
        cache: {
          paths: [".uv/cache/**/*", "infra/node_modules/**/*"],
        },
      }),
      environmentVariables: {
        ENVIRONMENT: { value: config.envName },
      },
      cache: codebuild.Cache.local(codebuild.LocalCacheMode.DOCKER_LAYER),
      timeout: cdk.Duration.minutes(30),
    });

    // =========================================================================
    // CodeBuild Project - Deploy
    // =========================================================================
    const deployProject = new codebuild.PipelineProject(this, "DeployProject", {
      projectName: `rd-knowledge-deploy-${config.envName}`,
      description: "Deploy rd-knowledge-sample infrastructure",
      environment: {
        buildImage: codebuild.LinuxBuildImage.AMAZON_LINUX_2_ARM_3,
        computeType: codebuild.ComputeType.SMALL,
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: "0.2",
        phases: {
          install: {
            "runtime-versions": {
              nodejs: "20",
            },
            commands: ["cd infra && npm ci", "npm install -g aws-cdk"],
          },
          build: {
            commands: [
              "cd infra",
              "cdk deploy --all --require-approval never --context env=${ENVIRONMENT}",
            ],
          },
        },
      }),
      environmentVariables: {
        ENVIRONMENT: { value: config.envName },
      },
      timeout: cdk.Duration.minutes(60),
    });

    // CDK デプロイ用の IAM 権限
    deployProject.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["sts:AssumeRole"],
        resources: [`arn:aws:iam::${this.account}:role/cdk-*`],
      })
    );

    // CloudFormation 権限
    deployProject.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "cloudformation:*",
          "s3:*",
          "lambda:*",
          "apigateway:*",
          "iam:*",
          "ec2:*",
          "logs:*",
          "neptune:*",
          "neptune-db:*",
          "bedrock:*",
        ],
        resources: ["*"],
      })
    );

    // =========================================================================
    // Pipeline
    // =========================================================================
    const sourceOutput = new codepipeline.Artifact("SourceOutput");
    const testOutput = new codepipeline.Artifact("TestOutput");

    const pipeline = new codepipeline.Pipeline(this, "Pipeline", {
      pipelineName: `rd-knowledge-pipeline-${config.envName}`,
      artifactBucket,
      pipelineType: codepipeline.PipelineType.V2,
      stages: [
        {
          stageName: "Source",
          actions: [
            new codepipeline_actions.CodeStarConnectionsSourceAction({
              actionName: "GitHub_Source",
              owner: config.github.owner,
              repo: config.github.repo,
              branch: config.github.branch,
              output: sourceOutput,
              connectionArn: `arn:aws:codestar-connections:${this.region}:${this.account}:connection/*`,
              triggerOnPush: true,
            }),
          ],
        },
        {
          stageName: "Test",
          actions: [
            new codepipeline_actions.CodeBuildAction({
              actionName: "Test",
              project: testProject,
              input: sourceOutput,
              outputs: [testOutput],
            }),
          ],
        },
        {
          stageName: "Deploy",
          actions: [
            new codepipeline_actions.CodeBuildAction({
              actionName: "Deploy",
              project: deployProject,
              input: sourceOutput,
            }),
          ],
        },
      ],
    });

    // =========================================================================
    // Outputs
    // =========================================================================
    new cdk.CfnOutput(this, "PipelineName", {
      value: pipeline.pipelineName,
      description: "CodePipeline name",
      exportName: `${config.envName}-PipelineName`,
    });

    new cdk.CfnOutput(this, "PipelineArn", {
      value: pipeline.pipelineArn,
      description: "CodePipeline ARN",
      exportName: `${config.envName}-PipelineArn`,
    });
  }
}

