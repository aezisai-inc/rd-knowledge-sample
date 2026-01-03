import { defineFunction } from '@aws-amplify/backend';

export const graphResolver = defineFunction({
  name: 'graphResolver',
  entry: './handler.ts',
  runtime: 20, // NodeJS 20
  timeoutSeconds: 30,
  memoryMB: 512,
  environment: {
    NODES_TABLE: process.env.NODES_TABLE || 'rd-knowledge-nodes',
    EDGES_TABLE: process.env.EDGES_TABLE || 'rd-knowledge-edges',
    LOG_LEVEL: process.env.LOG_LEVEL || 'INFO',
  },
});
