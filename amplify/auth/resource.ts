import { defineAuth } from "@aws-amplify/backend";

/**
 * Authentication configuration
 * Uses email-based sign-in for simplicity
 */
export const auth = defineAuth({
  loginWith: {
    email: true,
  },
});




