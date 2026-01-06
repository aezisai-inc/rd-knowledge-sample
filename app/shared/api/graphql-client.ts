/**
 * GraphQL Client Configuration
 *
 * Amplify Gen2 AppSync GraphQL クライアント
 * FSD shared/api 層として機能
 */

import { generateClient } from 'aws-amplify/api';
import type { Schema } from '../../../amplify/data/resource';

// Singleton client instance
let client: ReturnType<typeof generateClient<Schema>> | null = null;

/**
 * Get GraphQL client instance
 */
export function getGraphQLClient() {
  if (!client) {
    client = generateClient<Schema>();
  }
  return client;
}

/**
 * Type-safe query helper
 */
export type GraphQLClient = ReturnType<typeof getGraphQLClient>;

/**
 * Error handling wrapper
 */
export async function executeQuery<T>(
  operation: () => Promise<{ data?: T; errors?: Array<{ message: string }> }>
): Promise<T> {
  try {
    const result = await operation();

    if (result.errors && result.errors.length > 0) {
      throw new Error(result.errors.map((e) => e.message).join(', '));
    }

    if (!result.data) {
      throw new Error('No data returned');
    }

    return result.data;
  } catch (error) {
    console.error('GraphQL operation failed:', error);
    throw error;
  }
}
