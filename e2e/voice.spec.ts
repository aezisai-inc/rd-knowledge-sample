import { test, expect } from '@playwright/test';

test.describe('Voice Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.click('button:has-text("Voice")');
  });

  test('should display voice panel', async ({ page }) => {
    await expect(page.locator('text=Voice')).toBeVisible();
  });

  test('should have mode selection buttons', async ({ page }) => {
    // Check for TTS/STT/Dialogue mode buttons
    await expect(page.locator('button:has-text("TTS"), button:has-text("音声合成")')).toBeVisible();
  });
});
