const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const failures = [];
  page.on('pageerror', (error) => failures.push(error.message));
  page.on('dialog', (dialog) => dialog.accept());
  let documents = 0;
  page.on('request', (request) => { if (request.isNavigationRequest() && request.frame() === page.mainFrame()) documents += 1; });
  const base = process.env.TERRAPEER_TEST_URL;
  const screenshot = async (name) => {
    fs.mkdirSync('test-results', { recursive: true });
    await page.screenshot({ path: `test-results/${name}.png`, fullPage: true });
  };
  const waitPath = (pattern) => page.waitForURL(pattern);
  const checkResponsive = async (screen) => {
    for (const width of [320, 390, 768, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      const layout = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > innerWidth + 1,
        duplicates: [...document.querySelectorAll('#main-content [id]')].map((node) => node.id)
          .filter((id, index, ids) => ids.indexOf(id) !== index),
      }));
      assert.equal(layout.overflow, false, `${screen}: horizontal overflow at ${width}px`);
      assert.deepEqual(layout.duplicates, [], `${screen}: duplicate element IDs`);
    }
  };
  const create = async (name) => {
    await page.getByRole('link', { name: 'Add a plant', exact: true }).click();
    await waitPath('**/my-plants/add/');
    await checkResponsive('Create form');
    await page.getByLabel('Nickname', { exact: false }).fill(name);
    await page.locator('#id_species_name').fill('Tomato');
    await page.getByRole('button', { name: 'Add to My Plants' }).click();
    await page.locator('h1').filter({ hasText: name }).waitFor();
  };
  try {
    await page.goto(`${base}/login/?next=/my-plants/`);
    await page.locator('[name=username]').fill('browser-gardener');
    await page.locator('[name=password]').fill('Browser-Test-2026!');
    await page.locator('button[type=submit]').click();
    await waitPath('**/my-plants/');
    await page.waitForFunction(() => document.documentElement.classList.contains('js'));
    const initialDocuments = documents;
    await create('Browser Tomato');
    await page.getByRole('link', { name: 'Edit', exact: true }).click();
    await waitPath('**/edit/');
    await checkResponsive('Edit form');
    await page.locator('#id_growth_stage').selectOption('flowering');
    await page.getByRole('button', { name: 'Save changes' }).click();
    await page.locator('[data-field-error=photo]').filter({ hasText: 'Add a photo' }).waitFor();
    await page.locator('#id_growth_stage').selectOption('growing');
    await page.locator('#id_name').fill('Browser Tomato edited');
    await page.getByRole('button', { name: 'Save changes' }).click();
    await page.locator('h1').filter({ hasText: 'Browser Tomato edited' }).waitFor();
    const detailURL = page.url();
    await page.goBack();
    await waitPath('**/edit/');
    await page.locator('[data-plant-form]').waitFor();
    await page.goForward();
    await waitPath(detailURL);
    await page.locator('[data-stage-form]').waitFor();
    await page.locator('[data-stage-form] select').selectOption('flowering');
    await page.locator('[data-stage-form] input[type=file]').setInputFiles({
      name: 'plant.png', mimeType: 'image/png', buffer: Buffer.from(process.env.TERRAPEER_TEST_PHOTO, 'base64'),
    });
    await page.locator('[data-stage-form] button[type=submit]').click();
    await page.locator('[data-stage-badge]').filter({ hasText: 'Flowering' }).waitFor();
    await checkResponsive('Detail and photo diary');
    // Hold the real request long enough to observe the pending optimistic row.
    await page.route('**/check-ins/', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 250));
      await route.continue();
    });
    await page.locator('label[for=id_condition_1]').click();
    await page.getByRole('button', { name: 'Save check-in' }).click();
    await page.locator('[data-pending-check-in]').waitFor();
    await page.locator('[data-check-in-list] [data-check-in]').waitFor();
    await page.locator('label[for=id_condition_0]').click();
    await page.getByRole('button', { name: 'Save check-in' }).click();
    await page.locator('[data-check-in-error]').filter({ hasText: 'today' }).waitFor();
    assert.equal(await page.locator('[data-pending-check-in]').count(), 0);
    assert.match(await page.locator('[data-check-in-count]').innerText(), /^1 check-in$/);
    await page.getByRole('link', { name: 'Back to My Plants' }).click();
    await waitPath('**/my-plants/');
    await page.getByText('More filters', { exact: true }).click();
    await page.locator('#id_health').selectOption('attention');
    await page.waitForFunction(() => location.search.includes('health=attention'));
    assert.equal(await page.locator('.mp-card').count(), 1);
    await page.getByRole('link', { name: 'Reset', exact: true }).click();
    await page.waitForFunction(() => !location.search);
    await create('Second Browser Tomato');
    await page.getByRole('link', { name: 'Back to My Plants' }).click();
    await waitPath('**/my-plants/');
    await page.locator('[data-select-page]').check();
    // Simulate a protected relation. The optimistic removal must roll back.
    await page.route('**/bulk-delete/', (route) => route.fulfill({ status: 409,
      contentType: 'application/json', body: JSON.stringify({ error: 'Linked records prevent deletion.' }) }), { times: 1 });
    await page.getByRole('button', { name: 'Delete selected' }).click();
    await page.locator('[data-bulk-error]').filter({ hasText: 'Linked records' }).waitFor();
    assert.equal(await page.locator('.mp-card:visible').count(), 2);
    await checkResponsive('List and bulk selection');
    await screenshot('my-plants-desktop');
    await page.getByRole('button', { name: 'Delete selected' }).click();
    await page.getByText('Every garden starts with one plant.', { exact: true }).waitFor();
    await create('Single deletion test');
    await page.getByRole('link', { name: 'Delete plant', exact: true }).click();
    await page.getByRole('button', { name: 'Delete plant', exact: true }).click();
    await page.getByText('Every garden starts with one plant.', { exact: true }).waitFor();
    assert.equal(documents, initialDocuments, 'CRUD must not reload the document');
    assert.deepEqual(failures, []);
    console.log('PASS: AJAX create/edit/stage/delete, photo upload, daily check-in rollback, filters, bulk rollback/delete, Back/Forward and responsive layout; no document reloads.');
  } catch (error) {
    await screenshot('my-plants-failure');
    throw error;
  } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exitCode = 1; });
