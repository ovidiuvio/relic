/**
 * Generates a cryptographically secure-looking random 32-character hex key.
 */
export function generateClientKey() {
  const chars = '0123456789abcdef';
  let key = '';
  for (let i = 0; i < 32; i++) {
    key += chars[Math.floor(Math.random() * 16)];
  }
  return key;
}

/**
 * Pre-injects a client key into localStorage before the page content loads.
 * This lets the Svelte app read it and register/migrate it to the SW vault.
 * 
 * @param {import('@playwright/test').Page} page 
 * @param {string} key 
 */
export async function injectClientKey(page, key) {
  await page.addInitScript((clientKey) => {
    window.localStorage.setItem('relic_client_key', clientKey);
  }, key);
}
