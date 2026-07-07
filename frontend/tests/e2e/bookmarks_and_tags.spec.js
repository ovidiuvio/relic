import { test, expect } from '@playwright/test';
import { generateClientKey, injectClientKey } from './helpers.js';

test.describe('Bookmarks & Tags Suite', () => {
  let clientKey;

  test.beforeEach(async ({ page }) => {
    clientKey = generateClientKey();
    await injectClientKey(page, clientKey);
  });

  test('should create a relic with tags, search by tag, bookmark it, and verify bookmarked state', async ({ page }) => {
    // 1. Create a relic with tags
    await page.goto('/');
    await page.locator('.monaco-editor textarea').fill('Code with tag annotations');
    await page.fill('#title', 'Tagged Relic Item');
    await page.fill('#tags', 'tag-python, tag-ai');
    await page.click('button[type="submit"]');

    // Wait for redirect to viewer
    await page.waitForURL(/\/([a-f0-9]{32})/);
    const relicId = page.url().match(/\/([a-f0-9]{32})/)[1];

    // Verify tags are visible in the viewer
    await expect(page.locator('text=tag-python')).toBeVisible();
    await expect(page.locator('text=tag-ai')).toBeVisible();

    // 2. Click tag to trigger search
    await page.click('text=tag-python');

    // Should redirect to public search filter
    await page.waitForURL(/\/recent\?tag=tag-python/);
    await expect(page.locator('table')).toContainText('Tagged Relic Item');

    // 3. Open relic again, bookmark it
    await page.goto(`/${relicId}`);
    await page.click('button[title="Bookmark this relic"]');

    // Check count updates to 1
    await expect(page.locator('span[title="Bookmarks"]')).toContainText('1');

    // Navigate to "My Bookmarks" panel
    await page.click('button:has-text("Bookmarks")');
    await page.waitForURL(/\/my-bookmarks/);
    
    // Verify bookmarked item is listed
    await expect(page.locator('table')).toContainText('Tagged Relic Item');

    // 4. Open Bookmarkers modal from the relic view page
    await page.goto(`/${relicId}`);
    await page.click('span[title="Bookmarks"]');

    // Verify modal is visible
    await expect(page.locator('text=Bookmarked By')).toBeVisible();
  });
});
