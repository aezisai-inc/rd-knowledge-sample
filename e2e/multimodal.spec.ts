import { test, expect } from '@playwright/test';

test.describe('Multimodal Panel - Pre-Auth', () => {
  test('should load application without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    
    await page.goto('/');
    
    // ページがロードされることを確認
    await expect(page).toHaveTitle(/Knowledge Sample/);
    
    // 重大なJSエラーがないことを確認
    const criticalErrors = errors.filter(e => 
      e.includes('Amplify has not been configured') === false && // これは認証前に発生する可能性あり
      e.includes('fetch') === false // ネットワークエラーは認証前に発生する可能性あり
    );
    expect(criticalErrors).toHaveLength(0);
  });

  test('should not have CORS errors on initial load', async ({ page }) => {
    const corsErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.text().toLowerCase().includes('cors')) {
        corsErrors.push(msg.text());
      }
    });
    
    await page.goto('/');
    await page.waitForTimeout(2000);
    
    expect(corsErrors).toHaveLength(0);
  });

  test('should have proper page structure', async ({ page }) => {
    await page.goto('/');
    
    // HTMLが正しくレンダリングされることを確認
    await expect(page.locator('html')).toBeVisible();
    await expect(page.locator('body')).toBeVisible();
  });
});
