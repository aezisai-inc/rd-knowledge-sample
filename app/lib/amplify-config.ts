/**
 * Amplify Client Configuration
 *
 * フロントエンドで Amplify を使用するための設定
 */

'use client';

import { Amplify } from 'aws-amplify';
import { generateClient } from 'aws-amplify/data';
import type { Schema } from '../amplify/data/resource';

// Amplify 設定を読み込み
// amplify_outputs.json は npx ampx sandbox / npx ampx pipeline-deploy で自動生成
let configured = false;

export function configureAmplify() {
  if (configured) return;

  try {
    // 動的インポートで amplify_outputs.json を読み込み
    // Sandbox / Production で自動生成される
    const outputs = require('../amplify_outputs.json');
    Amplify.configure(outputs);
    configured = true;
    console.log('Amplify configured successfully');
  } catch (error) {
    // Sandbox 未起動時のフォールバック（開発用）
    console.warn('amplify_outputs.json not found. Run "npx ampx sandbox" to generate.');

    // 開発用の最小設定（API エンドポイントなし）
    Amplify.configure({
      API: {
        GraphQL: {
          endpoint: process.env.NEXT_PUBLIC_APPSYNC_URL || '',
          region: process.env.NEXT_PUBLIC_AWS_REGION || 'ap-northeast-1',
          defaultAuthMode: 'apiKey',
          apiKey: process.env.NEXT_PUBLIC_APPSYNC_API_KEY || '',
        },
      },
    });
    configured = true;
  }
}

// 型安全な GraphQL クライアント
export function getAmplifyClient() {
  configureAmplify();
  return generateClient<Schema>();
}

export { generateClient };
export type { Schema };
