import puppeteer from 'puppeteer-core';
import { access } from 'node:fs/promises';

const candidates = [
  process.env.CHROME_BIN,
  '/usr/bin/google-chrome',
  '/usr/bin/google-chrome-stable',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
].filter(Boolean);
let executablePath = null;
for (const path of candidates) {
  try { await access(path); executablePath = path; break; } catch {}
}
if (!executablePath) throw new Error('No Chrome/Chromium executable found');

const browser = await puppeteer.launch({
  executablePath,
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});

const base = process.env.SMOKE_BASE || 'http://127.0.0.1:4173';
const failures = [];

async function open(path, check) {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', err => errors.push(String(err?.stack || err)));
  page.on('response', response => {
    const status = response.status();
    const url = response.url();
    if (status >= 400 && !/\/favicon\.ico(?:\?|$)/i.test(url) && !/googletagmanager\.com/i.test(url)) {
      errors.push(`HTTP ${status}: ${url}`);
    }
  });
  page.on('requestfailed', request => {
    const url = request.url();
    if (!/googletagmanager\.com|google-analytics\.com|\/favicon\.ico(?:\?|$)/i.test(url)) {
      errors.push(`request failed: ${url} — ${request.failure()?.errorText || 'unknown'}`);
    }
  });
  page.on('console', msg => {
    const text = msg.text();
    if (msg.type() === 'error' && !/Failed to load resource|googletagmanager|ERR_BLOCKED_BY_CLIENT/i.test(text)) {
      errors.push(`console: ${text}`);
    }
  });
  try {
    const response = await page.goto(`${base}${path}`, { waitUntil: 'domcontentloaded', timeout: 20000 });
    if (!response?.ok()) throw new Error(`HTTP ${response?.status()} for ${path}`);
    await check(page);
    await new Promise(r => setTimeout(r, 500));
    if (errors.length) throw new Error(errors.join('\n'));
    console.log(`PASS ${path}`);
  } catch (error) {
    failures.push(`${path}: ${error.stack || error}`);
    console.error(`FAIL ${path}`, error);
  } finally {
    await page.close();
  }
}

await open('/pv-sites/pixel-lite/', async page => {
  await page.waitForSelector('#canvas');
  await page.waitForSelector('#layerList .layer-row');
  const before = await page.$$eval('#layerList .layer-row', rows => rows.length);
  await page.click('#addLayer');
  const after = await page.$$eval('#layerList .layer-row', rows => rows.length);
  if (after !== before + 1) throw new Error(`layer add failed: ${before} -> ${after}`);
  await page.click('[data-tool="select"]');
  const box = await page.$eval('#canvas', el => {
    const r = el.getBoundingClientRect();
    return { x: r.left, y: r.top, w: r.width, h: r.height };
  });
  await page.mouse.move(box.x + box.w * .2, box.y + box.h * .2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.w * .45, box.y + box.h * .4, { steps: 4 });
  await page.mouse.up();
  const selection = await page.$eval('#selectionInfo', el => el.textContent.trim());
  if (!selection || selection === '—') throw new Error('marquee selection did not initialize');
});

await open('/pv-sites/audio-master-lite/', async page => {
  await page.waitForSelector('#waveCanvas');
  for (const selector of ['#trimSelection','#fadeIn','#fadeOut','#normalize','#undoEdit','#redoEdit','#playSelection','#exportSelection','#exportWav']) {
    if (!await page.$(selector)) throw new Error(`missing ${selector}`);
  }
  const disabled = await page.$eval('#trimSelection', el => el.disabled);
  if (!disabled) throw new Error('trim should be disabled before audio is loaded');
});

await open('/pv-sites/pdf-workbench/', async page => {
  await page.waitForSelector('#pdfCanvas');
  await page.waitForFunction(() => Boolean(window.pdfjsLib && window.PDFLib), { timeout: 20000 });
  for (const selector of ['[data-tool="select"]','[data-tool="whiteout"]','#exportTop','#undoTop','#redoTop']) {
    if (!await page.$(selector)) throw new Error(`missing ${selector}`);
  }
  const label = await page.$eval('[data-tool="whiteout"]', el => el.textContent.trim());
  if (!label) throw new Error('redaction control has no label');
});

await browser.close();
if (failures.length) {
  console.error('\nBrowser smoke failures:\n' + failures.join('\n\n'));
  process.exit(1);
}
