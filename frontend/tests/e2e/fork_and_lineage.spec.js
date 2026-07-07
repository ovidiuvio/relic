import { test, expect } from '@playwright/test';
import { generateClientKey, injectClientKey } from './helpers.js';

test.describe('Fork & Lineage Suite', () => {
  let clientKey;

  test.beforeEach(async ({ page }) => {
    clientKey = generateClientKey();
    await injectClientKey(page, clientKey);
  });

  test('should create a relic, fork it, and verify the fork lineage', async ({ page }) => {
    // 1. Create original relic
    await page.goto('/');
    await page.locator('.monaco-editor textarea').fill('Original Parent Code content');
    await page.fill('#title', 'Parent Relic');
    await page.click('button[type="submit"]');

    // Wait for redirect to view original relic
    await page.waitForURL(/\/([a-f0-9]{32})/);
    const parentUrl = page.url();
    const parentMatch = parentUrl.match(/\/([a-f0-9]{32})/);
    const parentId = parentMatch[1];

    // 2. Trigger the Fork action
    await page.click('button[title="Create fork"]');

    // Wait for Fork Modal to appear
    await expect(page.locator('text=Fork Relic')).toBeVisible();

    // Verify parent content is loaded in the fork editor
    await expect(page.locator('.fork-editor-container .monaco-editor')).toContainText('Original Parent Code content');

    // Modify the content in Monaco inside the Fork Modal
    await page.locator('.fork-editor-container .monaco-editor textarea').fill('Original Parent Code content\n\nModified Fork Code content');

    // Update Fork Name
    await page.fill('#forkName', 'Forked Child Relic');

    // Submit the Fork form
    await page.click('button:has-text("Create Fork")');

    // Wait for redirection to the newly created child fork relic
    await page.waitForURL(/\/([a-f0-9]{32})/);
    const childUrl = page.url();
    const childMatch = childUrl.match(/\/([a-f0-9]{32})/);
    const childId = childMatch[1];

    expect(childId).not.toEqual(parentId);

    // 3. Verify lineage is rendered
    await expect(page.locator('h1')).toContainText('Forked Child Relic');
    await expect(page.locator('text=Fork of')).toBeVisible();

    // Open lineage modal
    await page.click('button[title="View full lineage"]');
    
    // Verify modal title
    await expect(page.locator('#lineage-modal-title')).toBeVisible();
    await expect(page.locator('.lineage-graph-container')).toBeVisible();
  });
});
