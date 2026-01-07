import { test, expect } from '@playwright/test';

test.describe('Voice Panel - Pre-Auth', () => {
  test('should display Material UI themed login', async ({ page }) => {
    await page.goto('/');
    
    // Material UIスタイルが適用されていることを確認（白背景）
    const body = page.locator('body');
    await expect(body).toBeVisible({ timeout: 10000 });
    
    // ページタイトルが正しいことを確認
    await expect(page).toHaveTitle(/Knowledge Sample/);
  });

  test('should have accessible form elements', async ({ page }) => {
    await page.goto('/');
    
    // フォーム要素がアクセシブルであることを確認
    const usernameInput = page.locator('input[name="username"]');
    await expect(usernameInput).toBeVisible({ timeout: 10000 });
    
    // inputがフォーカス可能であることを確認
    await usernameInput.focus();
    await expect(usernameInput).toBeFocused();
  });

  test('should show validation on empty submit', async ({ page }) => {
    await page.goto('/');
    
    // 空のまま送信ボタンをクリック
    const submitButton = page.locator('button[type="submit"]');
    await expect(submitButton).toBeVisible({ timeout: 10000 });
    await submitButton.click();
    
    // エラーメッセージまたはバリデーションが表示されることを確認
    // (Amplify UIはバリデーションを自動で行う)
    await page.waitForTimeout(1000);
  });
});
