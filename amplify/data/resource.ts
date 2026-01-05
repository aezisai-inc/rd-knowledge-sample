/**
 * Amplify Gen2 Data Schema Definition
 *
 * AppSync GraphQL API スキーマ定義
 * Clean Architecture の Infrastructure 層として機能
 */

import { type ClientSchema, a, defineData } from '@aws-amplify/backend';
import { memoryResolver } from '../functions/memory-resolver/resource';
import { vectorResolver } from '../functions/vector-resolver/resource';
import { graphResolver } from '../functions/graph-resolver/resource';
import { agentResolver } from '../functions/agent-resolver/resource';

const schema = a.schema({
  // ========================================
  // Memory Domain Types
  // ========================================
  MemorySession: a.customType({
    sessionId: a.string().required(),
    startTime: a.string().required(),
    endTime: a.string(),
    title: a.string(),
    tags: a.string().array(),
    messageCount: a.integer(),
    lastActive: a.string(),
    createdAt: a.string(),
  }),

  MemoryEvent: a.customType({
    id: a.string().required(),
    actorId: a.string().required(),
    sessionId: a.string().required(),
    role: a.string().required(),
    content: a.string().required(),
    timestamp: a.string().required(),
    metadata: a.json(),
  }),

  // ========================================
  // Search/Vector Domain Types
  // ========================================
  Vector: a.customType({
    id: a.string().required(),
    content: a.string().required(),
    vector: a.float().array(),
    metadata: a.json(),
  }),

  // ========================================
  // Graph Domain Types
  // ========================================
  Node: a.customType({
    id: a.string().required(),
    type: a.string().required(),
    properties: a.json(),
  }),

  Edge: a.customType({
    id: a.string().required(),
    sourceId: a.string().required(),
    targetId: a.string().required(),
    type: a.string().required(),
    properties: a.json(),
  }),

  // ========================================
  // Agent Domain Types
  // ========================================
  ImageOutput: a.customType({
    base64: a.string(),
    seed: a.integer(),
  }),

  VideoOutput: a.customType({
    status: a.string(),
    jobId: a.string(),
    url: a.string(),
  }),

  MultimodalResponse: a.customType({
    message: a.string(),
    images: a.ref('ImageOutput').array(),
    video: a.ref('VideoOutput'),
    metadata: a.json(),
  }),

  VoiceResponse: a.customType({
    transcript: a.string(),
    userText: a.string(),
    assistantText: a.string(),
    audio: a.string(),
    metadata: a.json(),
  }),

  // ========================================
  // Memory Queries & Mutations
  // ========================================
  getMemorySession: a
    .query()
    .arguments({ sessionId: a.string().required() })
    .returns(a.ref('MemorySession'))
    .handler(a.handler.function(memoryResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  // Get all sessions for a user (for session history)
  getMemorySessions: a
    .query()
    .arguments({
      actorId: a.string().required(),
      limit: a.integer(),
    })
    .returns(a.ref('MemorySession').array())
    .handler(a.handler.function(memoryResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  getMemoryEvents: a
    .query()
    .arguments({
      actorId: a.string().required(),
      sessionId: a.string(),
      limit: a.integer(),
    })
    .returns(a.ref('MemoryEvent').array())
    .handler(a.handler.function(memoryResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  createMemorySession: a
    .mutation()
    .arguments({
      title: a.string(),
      tags: a.string().array(),
    })
    .returns(a.ref('MemorySession'))
    .handler(a.handler.function(memoryResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  createMemoryEvent: a
    .mutation()
    .arguments({
      actorId: a.string().required(),
      sessionId: a.string().required(),
      role: a.string().required(),
      content: a.string().required(),
      metadata: a.json(),
    })
    .returns(a.ref('MemoryEvent'))
    .handler(a.handler.function(memoryResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  deleteMemorySession: a
    .mutation()
    .arguments({ sessionId: a.string().required() })
    .returns(a.boolean())
    .handler(a.handler.function(memoryResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  // ========================================
  // Vector/Search Queries & Mutations
  // ========================================
  searchVectors: a
    .query()
    .arguments({
      query: a.string().required(),
      k: a.integer(),
      minScore: a.float(),
    })
    .returns(a.ref('Vector').array())
    .handler(a.handler.function(vectorResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  indexDocument: a
    .mutation()
    .arguments({
      id: a.string(),
      content: a.string().required(),
      metadata: a.json(),
    })
    .returns(a.ref('Vector'))
    .handler(a.handler.function(vectorResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  // ========================================
  // Graph Queries & Mutations
  // ========================================
  getNode: a
    .query()
    .arguments({ id: a.string().required() })
    .returns(a.ref('Node'))
    .handler(a.handler.function(graphResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  getNodes: a
    .query()
    .arguments({ type: a.string() })
    .returns(a.ref('Node').array())
    .handler(a.handler.function(graphResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  queryGraph: a
    .query()
    .arguments({ cypherQuery: a.string().required() })
    .returns(a.json())
    .handler(a.handler.function(graphResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  createNode: a
    .mutation()
    .arguments({
      type: a.string().required(),
      properties: a.json(),
    })
    .returns(a.ref('Node'))
    .handler(a.handler.function(graphResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  updateNode: a
    .mutation()
    .arguments({
      id: a.string().required(),
      properties: a.json().required(),
    })
    .returns(a.ref('Node'))
    .handler(a.handler.function(graphResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  deleteNode: a
    .mutation()
    .arguments({ id: a.string().required() })
    .returns(a.ref('Node'))
    .handler(a.handler.function(graphResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  createEdge: a
    .mutation()
    .arguments({
      sourceId: a.string().required(),
      targetId: a.string().required(),
      type: a.string().required(),
      properties: a.json(),
    })
    .returns(a.ref('Edge'))
    .handler(a.handler.function(graphResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  deleteEdge: a
    .mutation()
    .arguments({ id: a.string().required() })
    .returns(a.ref('Edge'))
    .handler(a.handler.function(graphResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  // ========================================
  // Agent Queries & Mutations
  // ========================================
  invokeMultimodal: a
    .mutation()
    .arguments({
      sessionId: a.string().required(),
      prompt: a.string().required(),
      image: a.string(),
    })
    .returns(a.ref('MultimodalResponse'))
    .handler(a.handler.function(agentResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  sendVoiceText: a
    .mutation()
    .arguments({
      sessionId: a.string().required(),
      text: a.string().required(),
    })
    .returns(a.ref('VoiceResponse'))
    .handler(a.handler.function(agentResolver))
    .authorization((allow) => [allow.publicApiKey()]),

  // Voice Agent with audio input support
  invokeVoiceAgent: a
    .mutation()
    .arguments({
      sessionId: a.string().required(),
      text: a.string(),
      audio: a.string(),
      mode: a.string(), // 'TTS' | 'STT' | 'DIALOGUE'
    })
    .returns(a.ref('VoiceResponse'))
    .handler(a.handler.function(agentResolver))
    .authorization((allow) => [allow.publicApiKey()]),
});

export type Schema = ClientSchema<typeof schema>;

export const data = defineData({
  schema,
  authorizationModes: {
    defaultAuthorizationMode: 'apiKey',
    apiKeyAuthorizationMode: {
      expiresInDays: 30,
    },
  },
});
