import { test, expect } from '@playwright/test';

test.describe('Multimodal Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.click('button:has-text("Multimodal")');
  });

  test('should display multimodal tabs', async ({ page }) => {
    await expect(page.locator('button:has-text("画像解析")')).toBeVisible();
    await expect(page.locator('button:has-text("画像生成")')).toBeVisible();
    await expect(page.locator('button:has-text("動画生成")')).toBeVisible();
  });

  test('should switch to image generation tab', async ({ page }) => {
    await page.click('button:has-text("画像生成")');
    await expect(page.locator('text=生成したい画像を説明してください')).toBeVisible();
  });

  test('should enable generate button when prompt entered', async ({ page }) => {
    await page.click('button:has-text("画像生成")');
    const input = page.locator('input[placeholder*="生成したい画像"]');
    await input.fill('美しい富士山');
    await expect(page.locator('button:has-text("生成")')).toBeEnabled();
  });
});
