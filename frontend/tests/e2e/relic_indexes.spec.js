import { test, expect } from '@playwright/test';
import { generateClientKey, injectClientKey } from './helpers.js';

test.describe('Relic Indexes Suite', () => {
  let clientKey;

  test.beforeEach(async ({ page }) => {
    clientKey = generateClientKey();
    await injectClientKey(page, clientKey);
  });

  test('should parse .rix index files, load relics progressively, and apply overrides', async ({ page }) => {
    // 1. Create a base relic to include in our index
    await page.goto('/');
    await page.locator('.monaco-editor textarea').fill('Original index item content');
    await page.fill('#title', 'Base Item Title');
    await page.click('button[type="submit"]');

    // Parse relic ID from redirect URL
    await page.waitForURL(/\/([a-f0-9]{32})/);
    const url = page.url();
    const match = url.match(/\/([a-f0-9]{32})/);
    const relicId = match[1];

    // 2. Upload a .rix file containing the relic ID with an override title
    await page.goto('/');
    await page.click('button:has-text("Files")');

    const indexContent = `title: Custom Index
description: A collection of E2E relics
relics:
  - id: ${relicId}
    title: Overridden Title
    description: Overridden Description
`;
    const buffer = Buffer.from(indexContent, 'utf-8');

    await page.setInputFiles('input[type="file"]', {
      name: 'collection.rix',
      mimeType: 'application/x-relic-index',
      buffer: buffer
    });

    await page.click('button[type="submit"]');

    // Wait for redirect to index viewer
    await page.waitForURL(/\/([a-f0-9]{32})/);

    // Verify index progressive rendering is active
    await expect(page.locator('text=Custom Index')).toBeVisible();
    await expect(page.locator('text=A collection of E2E relics')).toBeVisible();
    
    // Verify overridden title is displayed in the list table instead of 'Base Item Title'
    await expect(page.locator('table')).toContainText('Overridden Title');
    await expect(page.locator('table')).not.toContainText('Base Item Title');
  });
});
