import { test, expect } from './helpers.js';

test.describe('Admin Panel features', () => {
  // Use generic visitor context first
  test('Non-admins cannot access admin panel', async ({ page }) => {
    // Navigate without setting localstorage admin key
    await page.goto('/admin');
    
    // Attempting to visit /admin should redirect to / (or display 404/Home)
    await expect(page).not.toHaveURL(/\/admin/);
    
    // And "Admin" tab shouldn't be in the navbar
    const header = page.locator('header');
    await expect(header.getByText('Admin')).not.toBeVisible();
  });

  // Use admin visitor context
  test('Admins can view health dashboard', async ({ adminPage }) => {
    // Expected to work due to the specific adminPage fixture setting TEST_ADMIN_KEY
    await adminPage.goto('/admin');
    
    // "Overview" section should load with standard elements
    await expect(adminPage.locator('h1')).toContainText(/System Dashboard/i);
    
    // Check that System Health numbers load
    const storageMetrics = adminPage.locator('text=Total Storage');
    await expect(storageMetrics).toBeVisible();
    
    // Admins Tab visible in Header
    const header = adminPage.locator('header');
    await expect(header.getByText('Admin')).toBeVisible();
  });

  test('Admins can switch to users list and see other clients', async ({ adminPage }) => {
    await adminPage.goto('/admin');
    
    // Click "Users" tab
    await adminPage.getByText('Users', { exact: true }).click();
    
    // Verify a table of users appears
    const table = adminPage.locator('table');
    await expect(table).toBeVisible();
    await expect(table.locator('thead th').filter({ hasText: 'Client ID' })).toBeVisible();
  });

});
