/**
 * Storage Stack
 *
 * S3, Neptune Serverless などのストレージリソースを定義
 */

import * as cdk from "aws-cdk-lib";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as neptune from "aws-cdk-lib/aws-neptune";
import * as iam from "aws-cdk-lib/aws-iam";
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
  /** Neptune クラスター */
  public readonly neptuneCluster: neptune.CfnDBCluster;
  /** Neptune セキュリティグループ */
  public readonly neptuneSecurityGroup: ec2.SecurityGroup;
  /** Neptune エンドポイント */
  public readonly neptuneEndpoint: string;

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
    // VPC (Neptune 用)
    // =========================================================================
    this.vpc = new ec2.Vpc(this, "Vpc", {
      vpcName: `rd-knowledge-vpc-${config.envName}`,
      maxAzs: 2,
      natGateways: config.envName === "prod" ? 2 : 0,
      subnetConfiguration: [
        {
          name: "Public",
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: "Private",
          subnetType:
            config.envName === "prod"
              ? ec2.SubnetType.PRIVATE_WITH_EGRESS
              : ec2.SubnetType.PRIVATE_ISOLATED,
          cidrMask: 24,
        },
      ],
    });

    // =========================================================================
    // Neptune Security Group
    // =========================================================================
    this.neptuneSecurityGroup = new ec2.SecurityGroup(
      this,
      "NeptuneSecurityGroup",
      {
        vpc: this.vpc,
        securityGroupName: `rd-knowledge-neptune-sg-${config.envName}`,
        description: "Security group for Neptune cluster",
        allowAllOutbound: true,
      }
    );

    // Lambda からのアクセスを許可
    this.neptuneSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(this.vpc.vpcCidrBlock),
      ec2.Port.tcp(8182),
      "Allow Neptune access from VPC"
    );

    // =========================================================================
    // Neptune Serverless Cluster
    // =========================================================================
    const neptuneSubnetGroup = new neptune.CfnDBSubnetGroup(
      this,
      "NeptuneSubnetGroup",
      {
        dbSubnetGroupDescription: `Neptune subnet group for ${config.envName}`,
        dbSubnetGroupName: `rd-knowledge-neptune-subnet-${config.envName}`,
        subnetIds: this.vpc.selectSubnets({
          subnetType:
            config.envName === "prod"
              ? ec2.SubnetType.PRIVATE_WITH_EGRESS
              : ec2.SubnetType.PRIVATE_ISOLATED,
        }).subnetIds,
      }
    );

    this.neptuneCluster = new neptune.CfnDBCluster(this, "NeptuneCluster", {
      dbClusterIdentifier: `rd-knowledge-neptune-${config.envName}`,
      engineVersion: "1.3.2.1",
      dbSubnetGroupName: neptuneSubnetGroup.dbSubnetGroupName,
      vpcSecurityGroupIds: [this.neptuneSecurityGroup.securityGroupId],
      serverlessScalingConfiguration: {
        minCapacity: config.neptune.minCapacity,
        maxCapacity: config.neptune.maxCapacity,
      },
      iamAuthEnabled: true,
      storageEncrypted: true,
      deletionProtection: config.envName === "prod",
    });

    this.neptuneCluster.addDependency(neptuneSubnetGroup);

    this.neptuneEndpoint = this.neptuneCluster.attrEndpoint;

    // =========================================================================
    // Outputs
    // =========================================================================
    new cdk.CfnOutput(this, "DataSourceBucketName", {
      value: this.dataSourceBucket.bucketName,
      description: "Knowledge Base data source bucket",
      exportName: `${config.envName}-DataSourceBucketName`,
    });

    new cdk.CfnOutput(this, "NeptuneEndpoint", {
      value: this.neptuneEndpoint,
      description: "Neptune cluster endpoint",
      exportName: `${config.envName}-NeptuneEndpoint`,
    });

    new cdk.CfnOutput(this, "VpcId", {
      value: this.vpc.vpcId,
      description: "VPC ID",
      exportName: `${config.envName}-VpcId`,
    });
  }
}

