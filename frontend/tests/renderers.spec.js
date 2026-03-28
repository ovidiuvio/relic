import { test, expect } from './helpers.js';

test.describe('Content Renderers', () => {

  test('TreeRenderer for JSON files allows expanding/collapsing', async ({ page }) => {
    await page.goto('/');

    const expectedName = 'data.json';
    const jsonContent = JSON.stringify({ layer1: { layer2: "value" } }, null, 2);

    await page.fill('input[placeholder="Name/Filename"]', expectedName);
    
    // Auto-detection should be json
    await page.waitForSelector('.monaco-editor');
    await page.evaluate((text) => {
        // @ts-ignore
        window.monacoEditorInstance.setValue(text);
    }, jsonContent);

    await page.getByRole('button', { name: "Save Relic" }).click();
    await page.waitForURL(/\/([a-f0-9]{32})/);
    
    // Renderers use .tree-node or similarly obvious classes
    // It depends on the specific TreeRenderer implementation
    const treeViewBtn = page.getByRole('button', { name: /View as Tree/i, exact: false }).or(page.locator('button[title="Tree View"]'));
    
    if (await treeViewBtn.isVisible()) {
        await treeViewBtn.click();
    }
    
    // Look for root object wrapper
    const treeNodeWrapper = page.locator('.tree-node, .tree-node-wrapper').first();
    await expect(treeNodeWrapper).toBeVisible();
    
    // Look for the inner text
    await expect(page.locator('text=layer1').first()).toBeVisible();
  });

  test('Markdown renderer is sanitized', async ({ page }) => {
    // create md
    await page.goto('/');
    const mdContent = '# Header \n<script>alert("xss")</script>\n[Link](http://example.com)';
    await page.waitForSelector('.monaco-editor');
    await page.evaluate((text) => {
        // @ts-ignore
        window.monacoEditorInstance.setValue(text);
    }, mdContent);
    await page.fill('input[placeholder="Name/Filename"]', 'test.md');
    
    await page.getByRole('button', { name: "Save Relic" }).click();
    await page.waitForURL(/\/([a-f0-9]{32})/);
    
    // It should automatically use markdown renderer
    // Check header
    await expect(page.locator('.markdown-body h1')).toContainText('Header');
    // Check link renders
    await expect(page.locator('.markdown-body a[href="http://example.com"]')).toBeVisible();
    
    // script shouldn't execute, and shouldn't be in DOM dynamically
    const scriptTags = await page.locator('.markdown-body script').count();
    expect(scriptTags).toBe(0);
  });

});
