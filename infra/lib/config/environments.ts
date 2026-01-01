/**
 * 環境設定
 *
 * グラフDB: Neptune → Neo4j AuraDB に移行
 * コスト削減: ~$166/月 → $0〜65/月
 */

export interface EnvironmentConfig {
  /** 環境名 */
  envName: string;
  /** AWS アカウント ID */
  account?: string;
  /** AWS リージョン */
  region: string;
  /** CI/CD パイプライン有効化 */
  enablePipeline: boolean;
  /** Neo4j 設定 (AuraDB or Local) */
  neo4j?: {
    /** 接続 URI (neo4j+s://xxx for AuraDB, bolt://localhost:7687 for local) */
    uri: string;
    /** ユーザー名 */
    user: string;
    /** データベース名 */
    database: string;
  };
  /** Lambda 設定 */
  lambda: {
    /** メモリサイズ (MB) */
    memorySize: number;
    /** タイムアウト (秒) */
    timeout: number;
  };
  /** API Gateway 設定 */
  apiGateway: {
    /** ステージ名 */
    stageName: string;
    /** スロットリング (リクエスト/秒) */
    throttlingRateLimit: number;
    /** バースト制限 */
    throttlingBurstLimit: number;
  };
  /** GitHub リポジトリ (CI/CD用) */
  github?: {
    owner: string;
    repo: string;
    branch: string;
  };
}

const environments: Record<string, EnvironmentConfig> = {
  dev: {
    envName: "dev",
    region: "ap-northeast-1",
    enablePipeline: false,
    neo4j: {
      // ローカル Docker Neo4j（開発用）
      // 本番用は AuraDB の URI に変更
      uri: "bolt://localhost:7687",
      user: "neo4j",
      database: "neo4j",
    },
    lambda: {
      memorySize: 256,
      timeout: 30,
    },
    apiGateway: {
      stageName: "dev",
      throttlingRateLimit: 100,
      throttlingBurstLimit: 200,
    },
  },
  staging: {
    envName: "staging",
    region: "ap-northeast-1",
    enablePipeline: true,
    neo4j: {
      // Neo4j AuraDB Professional
      uri: "neo4j+s://staging.databases.neo4j.io",
      user: "neo4j",
      database: "neo4j",
    },
    lambda: {
      memorySize: 512,
      timeout: 30,
    },
    apiGateway: {
      stageName: "staging",
      throttlingRateLimit: 500,
      throttlingBurstLimit: 1000,
    },
    github: {
      owner: "aezisai-inc",
      repo: "rd-knowledge-sample",
      branch: "develop",
    },
  },
  prod: {
    envName: "prod",
    region: "ap-northeast-1",
    enablePipeline: true,
    neo4j: {
      // Neo4j AuraDB Professional
      uri: "neo4j+s://prod.databases.neo4j.io",
      user: "neo4j",
      database: "neo4j",
    },
    lambda: {
      memorySize: 1024,
      timeout: 30,
    },
    apiGateway: {
      stageName: "prod",
      throttlingRateLimit: 1000,
      throttlingBurstLimit: 2000,
    },
    github: {
      owner: "aezisai-inc",
      repo: "rd-knowledge-sample",
      branch: "main",
    },
  },
};

export function getEnvironmentConfig(envName: string): EnvironmentConfig {
  const config = environments[envName];
  if (!config) {
    throw new Error(
      `Unknown environment: ${envName}. Available: ${Object.keys(environments).join(", ")}`
    );
  }
  return config;
}
