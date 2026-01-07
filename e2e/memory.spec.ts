import { test, expect } from '@playwright/test';

test.describe('Authentication & Memory Chat', () => {
  test('should display login page with Cognito Authenticator', async ({ page }) => {
    await page.goto('/');
    
    // 認証画面が表示されることを確認
    await expect(page.locator('text=Knowledge Sample')).toBeVisible({ timeout: 10000 });
    
    // ログインフォームの要素確認
    await expect(page.locator('input[name="username"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show sign up option', async ({ page }) => {
    await page.goto('/');
    
    // サインアップリンクが表示されることを確認
    await expect(page.locator('text=Create Account').or(page.locator('text=Sign up'))).toBeVisible({ timeout: 10000 });
  });

  test('should show forgot password option', async ({ page }) => {
    await page.goto('/');
    
    // パスワードリセットリンクが表示されることを確認
    await expect(page.locator('text=Forgot your password').or(page.locator('text=Reset Password'))).toBeVisible({ timeout: 10000 });
  });
});
