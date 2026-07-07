import { test, expect } from '@playwright/test';
import { generateClientKey, injectClientKey } from './helpers.js';

test.describe('Admin Dashboard Suite', () => {
  const ADMIN_KEY = '09d85e5f91316a66233d97e1b5936399';

  test('should block non-admin users from accessing /admin', async ({ page }) => {
    // Inject a normal client key
    const clientKey = generateClientKey();
    await injectClientKey(page, clientKey);

    await page.goto('/admin');

    // Wait for redirect or access denied warning
    await expect(page.locator('text=Admin privileges required')).toBeVisible();
  });

  test('should grant access to admin users and support configurations and backup views', async ({ page }) => {
    // Inject Admin client key
    await injectClientKey(page, ADMIN_KEY);

    await page.goto('/admin');

    // Verify Admin title is visible
    await expect(page.locator('h1')).toContainText('Admin Dashboard');

    // Verify the tabs are displayed
    await expect(page.locator('button:has-text("Overview")')).toBeVisible();
    await expect(page.locator('button:has-text("Relics")')).toBeVisible();
    await expect(page.locator('button:has-text("Users")')).toBeVisible();
    await expect(page.locator('button:has-text("Backups")')).toBeVisible();
    await expect(page.locator('button:has-text("Config")')).toBeVisible();

    // 1. Overview tab verification
    await expect(page.locator('text=Total Relics')).toBeVisible();
    await expect(page.locator('text=Total Size')).toBeVisible();

    // 2. Config tab verification
    await page.click('button:has-text("Config")');
    await expect(page.locator('text=S3_BUCKET_NAME')).toBeVisible();
    await expect(page.locator('text=MAX_UPLOAD_SIZE')).toBeVisible();

    // 3. Backups tab verification
    await page.click('button:has-text("Backups")');
    await expect(page.locator('text=Database backups stored in S3')).toBeVisible();
  });
});
