/**
 * 環境設定
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
  /** Neptune 設定 */
  neptune: {
    /** 最小 NCU */
    minCapacity: number;
    /** 最大 NCU */
    maxCapacity: number;
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
    region: "us-west-2",
    enablePipeline: false,
    neptune: {
      minCapacity: 1,
      maxCapacity: 2.5,
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
    region: "us-west-2",
    enablePipeline: true,
    neptune: {
      minCapacity: 2.5,
      maxCapacity: 4,
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
    region: "us-west-2",
    enablePipeline: true,
    neptune: {
      minCapacity: 2.5,
      maxCapacity: 8,
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

