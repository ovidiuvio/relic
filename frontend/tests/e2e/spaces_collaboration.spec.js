import { test, expect } from '@playwright/test';
import { generateClientKey, injectClientKey } from './helpers.js';

test.describe('Spaces Collaboration Suite', () => {
  test('should support private spaces, access control, and user role promotions', async ({ browser }) => {
    // Setup User A Page
    const userAContext = await browser.newContext();
    const userAPage = await userAContext.newPage();
    const userAKey = generateClientKey();
    await injectClientKey(userAPage, userAKey);

    // Register User A and get public ID
    const userARegPromise = userAPage.waitForResponse(
      resp => resp.url().includes('/client/register') && resp.status() === 200
    );
    await userAPage.goto('/');
    const userAReg = await userARegPromise;
    const userAPublicId = (await userAReg.json()).public_id;

    // Setup User B Page
    const userBContext = await browser.newContext();
    const userBPage = await userBContext.newPage();
    const userBKey = generateClientKey();
    await injectClientKey(userBPage, userBKey);

    // Register User B and get public ID
    const userBRegPromise = userBPage.waitForResponse(
      resp => resp.url().includes('/client/register') && resp.status() === 200
    );
    await userBPage.goto('/');
    const userBReg = await userBRegPromise;
    const userBPublicId = (await userBReg.json()).public_id;

    // 1. User A creates a private space
    await userAPage.goto('/spaces');
    await userAPage.click('button:has-text("Create Space")');
    await userAPage.fill('#newSpaceName', 'Secret Shared Project');
    await userAPage.click('label[for="vis-private"]');
    await userAPage.click('button:has-text("Create Space")');

    // Wait for space to appear in list and click to open it
    await expect(userAPage.locator('table')).toContainText('Secret Shared Project');
    await userAPage.click('text=Secret Shared Project');

    // Wait for viewer redirect to /spaces/[space_id]
    await userAPage.waitForURL(/\/spaces\/([a-f0-9]{32})/);
    const spaceUrl = userAPage.url();
    const spaceId = spaceUrl.match(/\/spaces\/([a-f0-9]{32})/)[1];

    // 2. User B tries to view the space, expects 403 / Access Denied
    await userBPage.goto(`/spaces/${spaceId}`);
    await expect(userBPage.locator('text=Access Denied')).toBeVisible();

    // 3. User A adds User B as Viewer
    await userAPage.fill('#grantClientId', userBPublicId);
    await userAPage.selectOption('#grantRole', 'viewer');
    await userAPage.click('button:has-text("Add User")');

    // Verify User B is added in User A's access list
    await expect(userAPage.locator('.space-access-list')).toContainText('viewer');

    // 4. User B reloads, can view the space, but upload buttons are hidden (view-only)
    await userBPage.reload();
    await expect(userBPage.locator('text=Access Denied')).not.toBeVisible();
    await expect(userBPage.locator('h1')).toContainText('Secret Shared Project');
    await expect(userBPage.locator('button[title="New Relic"]')).not.toBeVisible();

    // 5. User A promotes User B to Editor
    // Locate User B's row in the access list select box and change to Editor
    await userAPage.selectOption(`select[data-user-id="${userBPublicId}"]`, 'editor');

    // User B reloads, upload buttons should appear
    await userBPage.reload();
    await expect(userBPage.locator('button[title="New Relic"]')).toBeVisible();

    // User B uploads a relic to the space
    await userBPage.click('button[title="New Relic"]');
    await userBPage.waitForURL(new RegExp(`/?space=${spaceId}`));
    await userBPage.locator('.monaco-editor textarea').fill('E2E Editor Code relic');
    await userBPage.fill('#title', 'Editor Relic');
    await userBPage.click('button[type="submit"]');

    // Verify User B's relic appears in the Space table
    await userBPage.goto(`/spaces/${spaceId}`);
    await expect(userBPage.locator('table')).toContainText('Editor Relic');

    // Cleanup Contexts
    await userAContext.close();
    await userBContext.close();
  });
});
