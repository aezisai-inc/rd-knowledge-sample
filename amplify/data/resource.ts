import { type ClientSchema, a, defineData } from "@aws-amplify/backend";

/**
 * Data schema for Memory Architecture testing
 */
const schema = a.schema({
  // Test result storage
  TestResult: a
    .model({
      service: a.string().required(),  // "agentcore" | "bedrock-kb" | "s3-vectors"
      operation: a.string().required(), // "create" | "query" | "retrieve"
      input: a.string(),
      output: a.string(),
      latencyMs: a.integer(),
      success: a.boolean(),
      errorMessage: a.string(),
      timestamp: a.datetime(),
    })
    .authorization((allow) => [allow.owner()]),

  // Service availability check results
  ServiceStatus: a
    .model({
      service: a.string().required(),
      available: a.boolean().required(),
      region: a.string(),
      checkedAt: a.datetime(),
    })
    .authorization((allow) => [allow.authenticated()]),
});

export type Schema = ClientSchema<typeof schema>;

export const data = defineData({
  schema,
  authorizationModes: {
    defaultAuthorizationMode: "userPool",
  },
});

