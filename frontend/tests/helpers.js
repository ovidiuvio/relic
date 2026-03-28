import { test as base, expect } from '@playwright/test';
import crypto from 'crypto';

// Export expect
export { expect };

// Fixed test client key so tests don't pollute the dev browser
export const TEST_CLIENT_KEY = '5cdb7b79c38385db9f5b5f6ad884c8ef'; // Same as ADMIN_CLIENT_IDS in backend tests
export const TEST_ADMIN_KEY = '5cdb7b79c38385db9f5b5f6ad884c8ef';

// Create a custom test fixture that automatically injects a specific client key
export const test = base.extend({
  // Override page fixture to inject localstorage before loading any page
  page: async ({ page, baseURL }, use) => {
    // Navigate to a blank page on the site's origin so we can set localStorage
    await page.goto(`${baseURL}/`);
    
    // Set a predictable client key for tests
    await page.evaluate((key) => {
      localStorage.setItem('relic_client_key', key);
    }, TEST_CLIENT_KEY);
    
    // Provide the configured page to tests
    await use(page);
  },
  
  // Create an admin page fixture that injects the admin key
  adminPage: async ({ browser, baseURL }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(`${baseURL}/`);
    await page.evaluate((key) => {
      localStorage.setItem('relic_client_key', key);
    }, TEST_ADMIN_KEY);
    await use(page);
    await context.close();
  },
  
  // Create a clean user page (no key, simulating first visit)
  cleanPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await use(page);
    await context.close();
  }
});

/**
 * Helper to create a test relic file via form upload on the UI
 */
export async function createRelic(page, content = "Test Content", name = "test.txt", visibility = "public") {
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  
  // Wait for monaco editor
  const editorLocator = page.locator('.monaco-editor').first();
  await editorLocator.waitFor();
  
  // Click into editor and type content (or paste)
  await editorLocator.click();
  // We can't easily type into monaco, sometimes best to evaluate
  await page.evaluate((text) => {
    // @ts-ignore
    window.monacoEditorInstance.setValue(text);
  }, content);

  // Fill name
  await page.fill('input[placeholder="Name/Filename"]', name);
  
  // Set visibility if not public (public is default)
  if (visibility !== 'public') {
    await page.getByText('Public').click();
    await page.getByText(visibility.charAt(0).toUpperCase() + visibility.slice(1)).click();
  }
  
  // Submit The form
  await page.getByRole('button', { name: "Save Relic" }).click();
  
  // Wait for redirect to viewer
  await page.waitForURL(/\/([a-f0-9]{32})/);
  
  // Return the relic ID from URL
  const url = page.url();
  const match = url.match(/\/([a-f0-9]{32})/);
  return match ? match[1] : null;
}
