import { test, expect } from './helpers.js';

test.describe('Core Interactions', () => {

  test('create a new plain text relic and verify viewing it', async ({ page }) => {
    await page.goto('/');

    const expectedName = `test-relic-${Date.now()}.txt`;
    const expectedContent = `Hello world!\nIt is ${new Date().toISOString()}`;

    // Fill in the name
    await page.fill('input[placeholder="Name/Filename"]', expectedName);

    // Type in monaco
    await page.waitForSelector('.monaco-editor');
    await page.evaluate((text) => {
        // @ts-ignore
        window.monacoEditorInstance.setValue(text);
    }, expectedContent);

    // Add some tags
    await page.fill('input[placeholder="Add a tag..."]', 'e2e-test');
    await page.keyboard.press('Enter');

    // Save
    await page.getByRole('button', { name: "Save Relic" }).click();

    // Verify it redirects to the viewer and shows success
    await expect(page.locator('.toast')).toContainText(/Created successfully/i);
    await expect(page).toHaveURL(/\/([a-f0-9]{32})/);
    
    // Verify viewer content
    // wait for line numbers to signify monaco editor rendering the new relic
    await page.waitForSelector('.view-lines');
    
    // Header should contain the name
    await expect(page.locator('h1.font-medium, .text-xl.font-medium')).toContainText(expectedName);
    
    // Code should contain the text
    const textContent = await page.evaluate(() => {
        // @ts-ignore
        return window.monacoViewerInstance.getValue();
    });
    expect(textContent).toBe(expectedContent);
  });

  test('verify fork functionality', async ({ page }) => {
    await page.goto('/');
    
    // 1. Create a parent relic
    const expectedContent = 'Original text';
    await page.waitForSelector('.monaco-editor');
    await page.evaluate((text) => {
        // @ts-ignore
        window.monacoEditorInstance.setValue(text);
    }, expectedContent);
    await page.getByRole('button', { name: "Save Relic" }).click();
    
    // Wait for creation and grab ID
    await page.waitForURL(/\/([a-f0-9]{32})/);
    const parentUrl = page.url();
    const parentIdMatch = parentUrl.match(/\/([a-f0-9]{32})/);
    expect(parentIdMatch).not.toBeNull();
    const parentId = parentIdMatch[1];
    
    // 2. Click Fork
    await page.getByRole('button', { name: "Fork" }).click();
    
    // Verify modal appears
    const forkModal = page.locator('.modal, [role="dialog"]').filter({ hasText: 'Fork' });
    if (await forkModal.isVisible()) {
        await forkModal.getByRole('button', { name: "Create Fork" }).click();
    }
    
    // Verify we are at the fork editor page
    await page.waitForURL(/\/([a-f0-9]{32})\/fork/);
    
    // Add text to the fork
    const addedContent = '\nForked text';
    await page.evaluate((text) => {
        // @ts-ignore
        const current = window.monacoEditorInstance.getValue();
        // @ts-ignore
        window.monacoEditorInstance.setValue(current + text);
    }, addedContent);
    
    // Submit fork
    await page.getByRole('button', { name: 'Commit Changes' }).click();
    
    // Verify redirect to the new relic
    await page.waitForURL(/\/([a-f0-9]{32})/);
    expect(page.url()).not.toContain(parentId); // Should be a new ID
    
    // Verify the visual diff chain exists
    // The Lineage modal/button should be visibly active or clickable since it has a parent
    await expect(page.getByRole('button', { name: 'Lineage' })).toBeVisible();
  });

  test('bookmark a relic from viewer', async ({ page }) => {
    // Create first
    await page.goto('/');
    await page.waitForSelector('.monaco-editor');
    await page.evaluate(() => {
        // @ts-ignore
        window.monacoEditorInstance.setValue('Bookmark this test');
    });
    await page.getByRole('button', { name: "Save Relic" }).click();
    await page.waitForURL(/\/([a-f0-9]{32})/);
    
    const urlId = page.url().match(/\/([a-f0-9]{32})/)[1];

    // Click Bookmark button
    // It might be an SVG icon or button
    const bookmarkBtn = page.locator('button[title="Bookmark"]');
    await bookmarkBtn.click();
    
    // Verify toast
    await expect(page.locator('.toast')).toContainText(/bookmark/i);
    
    // Go to My Bookmarks
    await page.goto('/my-bookmarks');
    
    // Table should contain our ID
    await expect(page.locator('table')).toContainText(urlId);
  });

});
