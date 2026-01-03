import { defineFunction } from '@aws-amplify/backend';

export const vectorResolver = defineFunction({
  name: 'vectorResolver',
  entry: './handler.ts',
  runtime: 20, // NodeJS 20
  timeoutSeconds: 60,
  memoryMB: 1024,
  environment: {
    OUTPUT_BUCKET: process.env.OUTPUT_BUCKET || '',
    LOG_LEVEL: process.env.LOG_LEVEL || 'INFO',
  },
});
