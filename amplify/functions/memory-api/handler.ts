import type { Handler } from "aws-lambda";

/**
 * Memory API Lambda Handler
 * 
 * Provides endpoints for testing memory services:
 * - POST /check-availability - Check service availability
 * - POST /agentcore/create-memory - Create AgentCore memory
 * - POST /agentcore/create-event - Create event in memory
 * - POST /agentcore/retrieve - Retrieve memory records
 * - POST /bedrock-kb/retrieve - Retrieve from Knowledge Base
 * - POST /s3-vectors/query - Query S3 Vectors
 */

interface APIEvent {
  httpMethod: string;
  path: string;
  body: string | null;
  headers: Record<string, string>;
}

interface ServiceStatus {
  service: string;
  available: boolean;
  error?: string;
}

// Check service availability (simulated for now)
async function checkAvailability(): Promise<ServiceStatus[]> {
  const services = [
    { service: "bedrock-agentcore-control", available: true },
    { service: "bedrock-agentcore", available: true },
    { service: "bedrock-agent", available: true },
    { service: "bedrock-agent-runtime", available: true },
    { service: "s3vectors", available: true },
  ];
  
  return services;
}

// Mock responses for UI development
const mockResponses = {
  agentcoreMemory: {
    memoryId: "mem-demo-12345",
    status: "ACTIVE",
    strategies: ["SEMANTIC_MEMORY", "SUMMARY_MEMORY"],
  },
  agentcoreEvent: {
    eventId: "evt-demo-67890",
    actorId: "user-123",
    timestamp: new Date().toISOString(),
  },
  bedrockRetrieve: {
    results: [
      { content: "Sample document content...", score: 0.95 },
      { content: "Another relevant document...", score: 0.87 },
    ],
  },
  s3VectorsQuery: {
    vectors: [
      { key: "doc-001", score: 0.92, metadata: { source: "manual.pdf" } },
      { key: "doc-002", score: 0.85, metadata: { source: "guide.pdf" } },
    ],
  },
};

export const handler: Handler<APIEvent> = async (event) => {
  const { httpMethod, path, body } = event;
  
  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  };

  // Handle CORS preflight
  if (httpMethod === "OPTIONS") {
    return { statusCode: 200, headers: corsHeaders, body: "" };
  }

  try {
    let response: unknown;

    switch (path) {
      case "/check-availability":
        response = await checkAvailability();
        break;
        
      case "/agentcore/create-memory":
        response = mockResponses.agentcoreMemory;
        break;
        
      case "/agentcore/create-event":
        response = mockResponses.agentcoreEvent;
        break;
        
      case "/agentcore/retrieve":
        response = { records: [], message: "No records found (demo mode)" };
        break;
        
      case "/bedrock-kb/retrieve":
        response = mockResponses.bedrockRetrieve;
        break;
        
      case "/s3-vectors/query":
        response = mockResponses.s3VectorsQuery;
        break;
        
      default:
        return {
          statusCode: 404,
          headers: corsHeaders,
          body: JSON.stringify({ error: `Unknown path: ${path}` }),
        };
    }

    return {
      statusCode: 200,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
      body: JSON.stringify(response),
    };
  } catch (error) {
    console.error("Error:", error);
    return {
      statusCode: 500,
      headers: corsHeaders,
      body: JSON.stringify({ 
        error: error instanceof Error ? error.message : "Unknown error" 
      }),
    };
  }
};

