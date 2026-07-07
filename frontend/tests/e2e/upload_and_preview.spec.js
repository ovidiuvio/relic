import { test, expect } from '@playwright/test';
import { generateClientKey, injectClientKey } from './helpers.js';

test.describe('Upload & Preview Suite', () => {
  let clientKey;

  test.beforeEach(async ({ page }) => {
    clientKey = generateClientKey();
    await injectClientKey(page, clientKey);
  });

  test('should paste text/code and create a relic in public view', async ({ page }) => {
    await page.goto('/');

    // Ensure we are on the editor tab
    await expect(page.locator('#editor-container')).toBeVisible();

    // Type inside Monaco Editor textarea
    const codeContent = `def hello_world():\n    print("Hello from Relic E2E!")`;
    await page.locator('.monaco-editor textarea').fill(codeContent);

    // Set Title
    await page.fill('#title', 'E2E Code Relic');

    // Choose access level (select visibility is bound to "public" by default)
    await page.selectOption('select', 'public');

    // Submit form
    await page.click('button[type="submit"]');

    // Wait for redirect to relic viewer (URL pattern matches /[relic_id])
    await page.waitForURL(/\/([a-f0-9]{32})/);
    expect(page.url()).not.toContain('/recent');

    // Validate page content
    await expect(page.locator('h1')).toContainText('E2E Code Relic');
    await expect(page.locator('.monaco-editor')).toBeVisible();
    await expect(page.locator('.monaco-editor')).toContainText('hello_world');
  });

  test('should upload an image file and render the visual preview', async ({ page }) => {
    await page.goto('/');

    // Switch to Files tab
    await page.click('button:has-text("Files")');

    // Upload an image (simulated 1x1 base64 GIF)
    const base64Gif = 'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
    const buffer = Buffer.from(base64Gif, 'base64');

    await page.setInputFiles('input[type="file"]', {
      name: 'pixel.gif',
      mimeType: 'image/gif',
      buffer: buffer
    });

    // Verify it auto-switches to files listing in preview
    await expect(page.locator('text=pixel.gif')).toBeVisible();

    // Select Private visibility
    await page.selectOption('select', 'private');

    // Submit
    await page.click('button[type="submit"]');

    // Wait for viewer redirect
    await page.waitForURL(/\/([a-f0-9]{32})/);
    
    // Check that we render the image viewer
    await expect(page.locator('img')).toBeVisible();
    await expect(page.locator('text=image/gif')).toBeVisible();
  });

  test('should upload a CSV file and interact with the data table', async ({ page }) => {
    await page.goto('/');

    // Switch to Files tab
    await page.click('button:has-text("Files")');

    // Create CSV buffer
    const csvContent = 'id,name,role\n1,Alice,Developer\n2,Bob,Designer\n3,Charlie,Product Manager\n';
    const buffer = Buffer.from(csvContent, 'utf-8');

    await page.setInputFiles('input[type="file"]', {
      name: 'users.csv',
      mimeType: 'text/csv',
      buffer: buffer
    });

    await page.click('button[type="submit"]');

    // Wait for redirect
    await page.waitForURL(/\/([a-f0-9]{32})/);

    // Verify CSV renderer components
    await expect(page.locator('text=3 rows × 3 columns')).toBeVisible();
    
    // Verify rows are visible
    await expect(page.locator('table')).toContainText('Alice');
    await expect(page.locator('table')).toContainText('Bob');

    // Test text filter
    await page.fill('input[placeholder="Search all columns..."]', 'Designer');
    await expect(page.locator('table')).toContainText('Bob');
    await expect(page.locator('table')).not.toContainText('Alice'); // should be filtered out
  });

  test('should upload a ZIP archive and render folder structure', async ({ page }) => {
    await page.goto('/');

    // Switch to Files tab
    await page.click('button:has-text("Files")');

    // ZIP file signature (basic valid empty zip or very small zip)
    // A tiny valid zip file buffer
    const tinyZipBuffer = Buffer.from([
      0x50, 0x4b, 0x03, 0x04, 0x0a, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x74, 0x65,
      0x73, 0x74, 0x2e, 0x74, 0x78, 0x74, 0x50, 0x4b, 0x01, 0x02, 0x3f, 0x00, 0x0a, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x24, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x00, 0x00, 0x74, 0x65, 0x73, 0x74, 0x2e, 0x74, 0x78, 0x74, 0x50, 0x4b, 0x05, 0x06,
      0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x36, 0x00, 0x00, 0x00, 0x26, 0x00, 0x00, 0x00,
      0x00, 0x00
    ]);

    await page.setInputFiles('input[type="file"]', {
      name: 'archive.zip',
      mimeType: 'application/zip',
      buffer: tinyZipBuffer
    });

    await page.click('button[type="submit"]');

    // Wait for redirect
    await page.waitForURL(/\/([a-f0-9]{32})/);

    // Verify folder/file list representation is visible in tree renderer
    await expect(page.locator('text=test.txt')).toBeVisible();
  });
});
