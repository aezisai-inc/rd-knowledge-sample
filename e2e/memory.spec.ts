import { test, expect } from '@playwright/test';

test.describe('Memory Chat Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display memory chat UI', async ({ page }) => {
    await expect(page.locator('text=RAG Memory Chat')).toBeVisible();
    await expect(page.locator('input[placeholder*="メッセージを入力"]')).toBeVisible();
  });

  test('should show anonymous session warning', async ({ page }) => {
    await expect(page.locator('text=匿名セッション')).toBeVisible();
  });

  test('should enable send button when message entered', async ({ page }) => {
    const input = page.locator('input[placeholder*="メッセージを入力"]');
    await input.fill('テストメッセージ');
    await expect(page.locator('button:has-text("送信")')).toBeEnabled();
  });

  test('should show processing logs panel', async ({ page }) => {
    await expect(page.locator('text=Processing Logs')).toBeVisible();
  });
});
