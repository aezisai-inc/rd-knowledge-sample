/**
 * Amplify Client Configuration
 *
 * フロントエンドで Amplify を使用するための設定
 * このモジュールがインポートされた時点で設定が実行される
 */

'use client';

import { Amplify } from 'aws-amplify';
import { generateClient } from 'aws-amplify/data';
import type { Schema } from '../../amplify/data/resource';
import outputs from '../amplify_outputs.json';

// モジュールレベルで即座に設定（Authenticatorより先に実行される）
Amplify.configure(outputs);
console.log('Amplify configured successfully');

// 互換性のための関数（もはや何もしない）
export function configureAmplify() {
  // 既にモジュールレベルで設定済み
}

// 型安全な GraphQL クライアント
export function getAmplifyClient() {
  configureAmplify();
  return generateClient<Schema>();
}

export { generateClient };
export type { Schema };
