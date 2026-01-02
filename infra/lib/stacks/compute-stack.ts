/**
 * Compute Stack
 *
 * Lambda, API Gateway を定義
 *
 * グラフDB: Neptune → Neo4j AuraDB に移行
 */

import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { Construct } from "constructs";
import { EnvironmentConfig } from "../config/environments";
import { StorageStack } from "./storage-stack";
import * as path from "path";

export interface ComputeStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  tags: Record<string, string>;
  storageStack: StorageStack;
}

export class ComputeStack extends cdk.Stack {
  /** Memory API Lambda */
  public readonly memoryApiLambda: lambda.Function;
  /** Vector API Lambda */
  public readonly vectorApiLambda: lambda.Function;
  /** Graph API Lambda */
  public readonly graphApiLambda: lambda.Function;
  /** Agent API Lambda (Multimodal/Voice placeholder) */
  public readonly agentApiLambda: lambda.Function;
  /** API Gateway */
  public readonly api: apigateway.RestApi;
  /** API Gateway endpoint URL */
  public readonly apiEndpoint: string;

  constructor(scope: Construct, id: string, props: ComputeStackProps) {
    super(scope, id, props);

    const { config, storageStack } = props;

    // =========================================================================
    // Lambda Security Group
    // =========================================================================
    const lambdaSecurityGroup = new ec2.SecurityGroup(
      this,
      "LambdaSecurityGroup",
      {
        vpc: storageStack.vpc,
        securityGroupName: `rd-knowledge-lambda-sg-${config.envName}`,
        description: "Security group for Lambda functions",
        allowAllOutbound: true,
      }
    );

    // =========================================================================
    // Lambda Execution Role
    // =========================================================================
    const lambdaRole = new iam.Role(this, "LambdaExecutionRole", {
      roleName: `rd-knowledge-lambda-role-${config.envName}`,
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AWSLambdaBasicExecutionRole"
        ),
      ],
    });

    // S3 アクセス権限
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["s3:GetObject", "s3:ListBucket", "s3:PutObject"],
        resources: [
          storageStack.dataSourceBucket.bucketArn,
          `${storageStack.dataSourceBucket.bucketArn}/*`,
        ],
      })
    );

    // Bedrock 権限 (Knowledge Base, AgentCore Memory)
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "bedrock:Retrieve",
          "bedrock:RetrieveAndGenerate",
          "bedrock:InvokeModel",
          "bedrock:CreateMemory",
          "bedrock:GetMemory",
          "bedrock:CreateEvent",
          "bedrock:RetrieveMemoryRecords",
        ],
        resources: ["*"],
      })
    );

    // Secrets Manager 権限 (Neo4j 接続情報)
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["secretsmanager:GetSecretValue"],
        resources: [storageStack.neo4jSecret.secretArn],
      })
    );

    // S3 Vectors 権限 (Preview)
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["s3vectors:*"],
        resources: [`arn:aws:s3vectors:*:${this.account}:vector-bucket/*`],
      })
    );

    // =========================================================================
    // Lambda Layer (共通依存関係)
    // =========================================================================
    const dependenciesLayer = new lambda.LayerVersion(
      this,
      "DependenciesLayer",
      {
        layerVersionName: `rd-knowledge-deps-${config.envName}`,
        description: "Common dependencies for Lambda functions",
        code: lambda.Code.fromAsset(
          path.join(__dirname, "../../lambda/layers/dependencies")
        ),
        compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
        compatibleArchitectures: [lambda.Architecture.ARM_64],
      }
    );

    // =========================================================================
    // Memory API Lambda
    // =========================================================================
    this.memoryApiLambda = new lambda.Function(this, "MemoryApiLambda", {
      functionName: `rd-knowledge-memory-api-${config.envName}`,
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      handler: "handler.lambda_handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "../../lambda/memory-api")
      ),
      memorySize: config.lambda.memorySize,
      timeout: cdk.Duration.seconds(config.lambda.timeout),
      role: lambdaRole,
      layers: [dependenciesLayer],
      environment: {
        ENVIRONMENT: config.envName,
        NEO4J_SECRET_ARN: storageStack.neo4jSecret.secretArn,
        DATA_SOURCE_BUCKET: storageStack.dataSourceBucket.bucketName,
        LOG_LEVEL: config.envName === "prod" ? "INFO" : "DEBUG",
      },
      logRetention: logs.RetentionDays.TWO_WEEKS,
      tracing: lambda.Tracing.ACTIVE,
    });

    // =========================================================================
    // Vector API Lambda
    // =========================================================================
    this.vectorApiLambda = new lambda.Function(this, "VectorApiLambda", {
      functionName: `rd-knowledge-vector-api-${config.envName}`,
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      handler: "handler.lambda_handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "../../lambda/vector-api")
      ),
      memorySize: config.lambda.memorySize,
      timeout: cdk.Duration.seconds(config.lambda.timeout),
      role: lambdaRole,
      layers: [dependenciesLayer],
      environment: {
        ENVIRONMENT: config.envName,
        DATA_SOURCE_BUCKET: storageStack.dataSourceBucket.bucketName,
        LOG_LEVEL: config.envName === "prod" ? "INFO" : "DEBUG",
      },
      logRetention: logs.RetentionDays.TWO_WEEKS,
      tracing: lambda.Tracing.ACTIVE,
    });

    // =========================================================================
    // Graph API Lambda
    // =========================================================================
    this.graphApiLambda = new lambda.Function(this, "GraphApiLambda", {
      functionName: `rd-knowledge-graph-api-${config.envName}`,
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      handler: "handler.lambda_handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "../../lambda/graph-api")
      ),
      memorySize: config.lambda.memorySize,
      timeout: cdk.Duration.seconds(config.lambda.timeout),
      role: lambdaRole,
      layers: [dependenciesLayer],
      environment: {
        ENVIRONMENT: config.envName,
        NEO4J_SECRET_ARN: storageStack.neo4jSecret.secretArn,
        LOG_LEVEL: config.envName === "prod" ? "INFO" : "DEBUG",
      },
      logRetention: logs.RetentionDays.TWO_WEEKS,
      tracing: lambda.Tracing.ACTIVE,
    });

    // =========================================================================
    // Agent API Lambda (Multimodal/Voice placeholder)
    // =========================================================================
    this.agentApiLambda = new lambda.Function(this, "AgentApiLambda", {
      functionName: `rd-knowledge-agent-api-${config.envName}`,
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      handler: "handler.lambda_handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "../../lambda/agent-api")
      ),
      memorySize: config.lambda.memorySize,
      timeout: cdk.Duration.seconds(config.lambda.timeout),
      role: lambdaRole,
      layers: [dependenciesLayer],
      environment: {
        ENVIRONMENT: config.envName,
        DATA_SOURCE_BUCKET: storageStack.dataSourceBucket.bucketName,
        LOG_LEVEL: config.envName === "prod" ? "INFO" : "DEBUG",
      },
      logRetention: logs.RetentionDays.TWO_WEEKS,
      tracing: lambda.Tracing.ACTIVE,
    });

    // =========================================================================
    // API Gateway
    // =========================================================================
    this.api = new apigateway.RestApi(this, "Api", {
      restApiName: `rd-knowledge-api-${config.envName}`,
      description: "rd-knowledge-sample API",
      deployOptions: {
        stageName: config.apiGateway.stageName,
        throttlingRateLimit: config.apiGateway.throttlingRateLimit,
        throttlingBurstLimit: config.apiGateway.throttlingBurstLimit,
        tracingEnabled: true,
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ["Content-Type", "Authorization", "X-Amz-Date"],
      },
    });

    // API Endpoint URL を公開
    this.apiEndpoint = this.api.url;

    // API リソース定義
    const v1 = this.api.root.addResource("v1");

    // /v1/memory
    const memoryResource = v1.addResource("memory");
    memoryResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(this.memoryApiLambda)
    );
    memoryResource.addMethod(
      "GET",
      new apigateway.LambdaIntegration(this.memoryApiLambda)
    );

    // /v1/memory/{actorId}
    const memoryActorResource = memoryResource.addResource("{actorId}");
    memoryActorResource.addMethod(
      "GET",
      new apigateway.LambdaIntegration(this.memoryApiLambda)
    );
    memoryActorResource.addMethod(
      "DELETE",
      new apigateway.LambdaIntegration(this.memoryApiLambda)
    );

    // /v1/vectors
    const vectorResource = v1.addResource("vectors");
    vectorResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(this.vectorApiLambda)
    );
    vectorResource.addMethod(
      "GET",
      new apigateway.LambdaIntegration(this.vectorApiLambda)
    );

    // /v1/vectors/query
    const vectorQueryResource = vectorResource.addResource("query");
    vectorQueryResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(this.vectorApiLambda)
    );

    // /v1/graph
    const graphResource = v1.addResource("graph");

    // /v1/graph/nodes
    const nodesResource = graphResource.addResource("nodes");
    nodesResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(this.graphApiLambda)
    );
    nodesResource.addMethod(
      "GET",
      new apigateway.LambdaIntegration(this.graphApiLambda)
    );

    // /v1/graph/nodes/{nodeId}
    const nodeResource = nodesResource.addResource("{nodeId}");
    nodeResource.addMethod(
      "GET",
      new apigateway.LambdaIntegration(this.graphApiLambda)
    );
    nodeResource.addMethod(
      "PUT",
      new apigateway.LambdaIntegration(this.graphApiLambda)
    );
    nodeResource.addMethod(
      "DELETE",
      new apigateway.LambdaIntegration(this.graphApiLambda)
    );

    // /v1/graph/edges
    const edgesResource = graphResource.addResource("edges");
    edgesResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(this.graphApiLambda)
    );

    // /v1/graph/query
    const graphQueryResource = graphResource.addResource("query");
    graphQueryResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(this.graphApiLambda)
    );

    // /v1/agent (Multimodal/Voice placeholder)
    const agentResource = v1.addResource("agent");

    // /v1/agent/multimodal
    const multimodalResource = agentResource.addResource("multimodal");

    // /v1/agent/multimodal/invoke
    const multimodalInvokeResource = multimodalResource.addResource("invoke");
    multimodalInvokeResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(this.agentApiLambda)
    );

    // /v1/agent/voice
    const voiceResource = agentResource.addResource("voice");

    // /v1/agent/voice/process
    const voiceProcessResource = voiceResource.addResource("process");
    voiceProcessResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(this.agentApiLambda)
    );

    // /v1/agent/voice/text
    const voiceTextResource = voiceResource.addResource("text");
    voiceTextResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(this.agentApiLambda)
    );

    // =========================================================================
    // Outputs
    // =========================================================================
    new cdk.CfnOutput(this, "ApiEndpoint", {
      value: this.api.url,
      description: "API Gateway endpoint URL",
      exportName: `${config.envName}-ApiEndpoint`,
    });

    new cdk.CfnOutput(this, "MemoryApiLambdaArn", {
      value: this.memoryApiLambda.functionArn,
      description: "Memory API Lambda ARN",
      exportName: `${config.envName}-MemoryApiLambdaArn`,
    });
  }
}
