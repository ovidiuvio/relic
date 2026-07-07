import { test, expect } from '@playwright/test';
import { generateClientKey, injectClientKey } from './helpers.js';

test.describe('Discussions & Comments Suite', () => {
  let clientKey;

  test.beforeEach(async ({ page }) => {
    clientKey = generateClientKey();
    await injectClientKey(page, clientKey);
  });

  test('should add a line-anchored comment, render it, and persist on reload', async ({ page }) => {
    // 1. Create a relic
    await page.goto('/');
    await page.locator('.monaco-editor textarea').fill('Line 1\nLine 2\nLine 3\nLine 4\nLine 5');
    await page.fill('#title', 'Comment Test Relic');
    await page.click('button[type="submit"]');

    // Wait for redirect
    await page.waitForURL(/\/([a-f0-9]{32})/);

    // 2. Click the glyph margin on Line 3 to open the comment form
    const lineMargin = page.locator('.monaco-editor .margin-view-overlays > div').nth(2); // Line 3
    await lineMargin.click({ position: { x: 5, y: 10 } });

    // Verify Comment Editor is displayed
    await expect(page.locator('.comment-editor textarea')).toBeVisible();

    // Write a comment
    await page.locator('.comment-editor textarea').fill('This is an E2E test comment on line 3');

    // Submit comment
    await page.click('.comment-editor button.submit-btn:has-text("Comment")');

    // Verify comment badge count in header
    await expect(page.locator('span[title="Comments"]')).toContainText('1');

    // Verify the comment text is rendered in the editor's widget zone
    await expect(page.locator('.comment-widget-zone')).toContainText('This is an E2E test comment on line 3');

    // 3. Reload page to verify persistence
    await page.reload();

    // Verify comments count is still 1 and comment is still displayed
    await expect(page.locator('span[title="Comments"]')).toContainText('1');
    await expect(page.locator('.comment-widget-zone')).toContainText('This is an E2E test comment on line 3');
  });
});
