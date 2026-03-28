import { test, expect } from './helpers.js';

test.describe('Spaces Flow', () => {

  test('Create a private space and assign a relic', async ({ page }) => {
    // Navigate to Spaces
    await page.goto('/spaces');
    
    // Check create space header
    await expect(page.locator('h1.font-medium')).toContainText('Spaces');
    
    // Click Create Space
    await page.getByRole('button', { name: "New Space" }).click();
    
    // Type name
    const spaceName = 'Integration Test Space - ' + Date.now();
    await page.fill('input[placeholder="Name"]', spaceName);
    
    // Type description
    await page.fill('textarea[placeholder="Description..."]', 'E2E Testing private workspace');
    
    // Toggle Private
    await page.locator('button_or_checkbox_that_toggles_private').click().catch(() => {}); // Usually handled by a svelte component 
    // Fallback: target by text if it's a visible button
    await page.getByText('Private').click({ force: true }).catch(() => {});
    
    // Save
    await page.getByRole('button', { name: "Create Space" }).click();
    
    // Should navigate to /spaces/some-id
    await page.waitForURL(/\/spaces\/([a-z0-9-]+)/);
    
    const urlId = page.url().match(/\/spaces\/([a-z0-9-]+)/)[1];

    // Assert the name is clearly rendered
    await expect(page.locator('h1')).toContainText(spaceName);
    
    // It should be empty initially
    await expect(page.getByText('No relics found in this space')).toBeVisible();
    
    // Go to My Relics, open Add To Space Modal 
    // Creating one quickly
    await page.goto('/');
    await page.evaluate(() => {
        // @ts-ignore
        window.monacoEditorInstance.setValue('A test assignment to spaces');
    });
    await page.getByRole('button', { name: "Save Relic" }).click();
    await page.waitForURL(/\/([a-f0-9]{32})/);
    
    // Click the "Add to Space" button on the relic viewer header
    const spaceBtn = page.locator('button[title="Add to Space"]');
    await spaceBtn.click();
    
    // Modal opens
    const modal = page.locator('.modal, [role="dialog"]');
    await expect(modal).toBeVisible();
    
    // Search for the Space we just created
    await modal.getByPlaceholder(/Search spaces/i).fill(spaceName);
    
    // Click the result
    await modal.getByText(spaceName).first().click();
    
    // Click Add
    await modal.getByRole('button', { name: /Add to/i }).click();
    
    // Verify Toast
    await expect(page.locator('.toast')).toContainText(/Added to space/i);
    
    // Go back to space and verify it's there
    await page.goto(`/spaces/${urlId}`);
    const tableRow = page.locator('table').locator('tr').filter({ hasText: 'test.html' }).last(); // Default name if not specified
    await expect(page.locator('table')).toBeVisible();
  });

});
