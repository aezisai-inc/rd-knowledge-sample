import { defineBackend } from "@aws-amplify/backend";
import { auth } from "./auth/resource";
import { data } from "./data/resource";
import { memoryApi } from "./functions/memory-api/resource";

/**
 * Amplify Gen2 Backend for Memory Architecture Sample
 * 
 * Provides API endpoints to test:
 * - AgentCore Memory
 * - Bedrock Knowledge Bases
 * - S3 Vectors
 */
export const backend = defineBackend({
  auth,
  data,
  memoryApi,
});

