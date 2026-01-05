import { defineFunction } from '@aws-amplify/backend';

export const agentResolver = defineFunction({
  name: 'agentResolver',
  entry: './handler.ts',
  runtime: 20, // NodeJS 20
  timeoutSeconds: 120, // Longer for AI model invocations
  memoryMB: 1024,
  environment: {
    AGENTCORE_MEMORY_ID: process.env.AGENTCORE_MEMORY_ID || '',
    OUTPUT_BUCKET: process.env.OUTPUT_BUCKET || '',
    LOG_LEVEL: process.env.LOG_LEVEL || 'INFO',
  },
  bundling: {
    externalModules: ['@aws-sdk/*'], // AWS SDK is included in Lambda runtime
  },
});
