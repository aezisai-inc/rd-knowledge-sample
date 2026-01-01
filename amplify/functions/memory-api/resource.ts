import { defineFunction } from "@aws-amplify/backend";

/**
 * Lambda function for Memory Architecture API
 * Wraps Python samples to provide REST API endpoints
 */
export const memoryApi = defineFunction({
  name: "memory-api",
  entry: "./handler.ts",
  timeoutSeconds: 30,
  memoryMB: 512,
  environment: {
    AWS_REGION: "us-west-2",
  },
  // IAM permissions for Bedrock, S3 Vectors, DynamoDB
  // Note: These will be added via CDK overrides in backend.ts
});




