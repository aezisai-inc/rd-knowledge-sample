/**
 * Storage Stack
 *
 * S3 などのストレージリソースを定義
 *
 * NOTE: グラフデータベースは Neo4j AuraDB（外部マネージドサービス）を使用
 * AWS Neptune は廃止（コスト削減: ~$166/月）
 */

import * as cdk from "aws-cdk-lib";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Construct } from "constructs";
import { EnvironmentConfig } from "../config/environments";

export interface StorageStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  tags: Record<string, string>;
}

export class StorageStack extends cdk.Stack {
  /** データソース用 S3 バケット */
  public readonly dataSourceBucket: s3.Bucket;
  /** VPC */
  public readonly vpc: ec2.Vpc;
  /** Neo4j 接続情報シークレット */
  public readonly neo4jSecret: secretsmanager.Secret;

  constructor(scope: Construct, id: string, props: StorageStackProps) {
    super(scope, id, props);

    const { config } = props;

    // =========================================================================
    // S3 Bucket (Knowledge Base データソース)
    // =========================================================================
    this.dataSourceBucket = new s3.Bucket(this, "DataSourceBucket", {
      bucketName: `rd-knowledge-datasource-${config.envName}-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      lifecycleRules: [
        {
          id: "delete-old-versions",
          noncurrentVersionExpiration: cdk.Duration.days(30),
        },
      ],
      removalPolicy:
        config.envName === "prod"
          ? cdk.RemovalPolicy.RETAIN
          : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: config.envName !== "prod",
    });

    // =========================================================================
    // VPC (Lambda 用 - Neo4j AuraDB は VPC 不要)
    // =========================================================================
    this.vpc = new ec2.Vpc(this, "Vpc", {
      vpcName: `rd-knowledge-vpc-${config.envName}`,
      maxAzs: 2,
      // NAT Gateway は不要（Neo4j AuraDB はパブリックエンドポイント）
      natGateways: 0,
      subnetConfiguration: [
        {
          name: "Public",
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: "Private",
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
          cidrMask: 24,
        },
      ],
    });

    // =========================================================================
    // Neo4j 接続情報 (Secrets Manager)
    //
    // Neo4j AuraDB の接続情報を安全に保存
    // 事前に AuraDB コンソールで作成した接続情報を設定
    // =========================================================================
    this.neo4jSecret = new secretsmanager.Secret(this, "Neo4jSecret", {
      secretName: `rd-knowledge-neo4j-${config.envName}`,
      description: "Neo4j AuraDB connection credentials",
      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          uri: config.neo4j?.uri || "bolt://localhost:7687",
          user: config.neo4j?.user || "neo4j",
          database: config.neo4j?.database || "neo4j",
        }),
        generateStringKey: "password",
        excludePunctuation: true,
        passwordLength: 32,
      },
    });

    // =========================================================================
    // Outputs
    // =========================================================================
    new cdk.CfnOutput(this, "DataSourceBucketName", {
      value: this.dataSourceBucket.bucketName,
      description: "Knowledge Base data source bucket",
      exportName: `${config.envName}-DataSourceBucketName`,
    });

    new cdk.CfnOutput(this, "VpcId", {
      value: this.vpc.vpcId,
      description: "VPC ID",
      exportName: `${config.envName}-VpcId`,
    });

    new cdk.CfnOutput(this, "Neo4jSecretArn", {
      value: this.neo4jSecret.secretArn,
      description: "Neo4j connection secret ARN",
      exportName: `${config.envName}-Neo4jSecretArn`,
    });

    // =========================================================================
    // Neo4j AuraDB セットアップ手順 (README用)
    // =========================================================================
    /*
    Neo4j AuraDB のセットアップ:

    1. Neo4j AuraDB コンソールにアクセス:
       https://console.neo4j.io/

    2. 新しいインスタンスを作成:
       - Free Tier (開発用): 無料
       - Professional (本番用): ~$65/月〜

    3. 接続情報を取得:
       - Connection URI: neo4j+s://xxxxx.databases.neo4j.io
       - Username: neo4j
       - Password: (生成されたパスワード)

    4. Secrets Manager を更新:
       aws secretsmanager put-secret-value \
         --secret-id rd-knowledge-neo4j-${config.envName} \
         --secret-string '{
           "uri": "neo4j+s://xxxxx.databases.neo4j.io",
           "user": "neo4j",
           "password": "your-aura-password",
           "database": "neo4j"
         }'

    コスト比較:
    - Neptune Serverless: ~$166/月 (最低1NCU)
    - Neo4j AuraDB Free: $0/月 (開発用)
    - Neo4j AuraDB Professional: ~$65/月〜 (本番用)
    */
  }
}
