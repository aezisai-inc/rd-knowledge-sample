import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['amplify/**/*.test.ts', 'app/**/*.test.ts', 'app/**/*.test.tsx', 'tests/**/*.test.ts'],
    exclude: ['**/node_modules/**', '.next/**', '**/amplify_outputs.json'],
  },
});
