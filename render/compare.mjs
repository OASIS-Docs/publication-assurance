// Copyright 2026 OASIS Open
// SPDX-License-Identifier: Apache-2.0
// Authored by Michael Coletta, Technical Advisor to OASIS Open.
//
// Side by side: the published HTML and a rendered edition, at the anchors
// you name. For each anchor it scrolls both pages to the same element and
// captures the viewport as <n>-<anchor>-published.png and
// <n>-<anchor>-rendered.png, for a person to compare.
//
//   CHROME=/path/to/chrome node compare.mjs PUBLISHED RENDERED OUT_DIR [ANCHOR,...]
//
// PUBLISHED and RENDERED are URLs or files. ANCHOR is an element id; "cover"
// is the top of the page, and "toc" finds the contents (DocBook div.toc or
// the Markdown template's #table-of-contents). Default: cover,toc.
// Exit 1 when an anchor is missing on either side: the two editions do not
// have the same structure there, and the pair would compare nothing.
import puppeteer from 'puppeteer-core';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

const [published, rendered, out, list] = process.argv.slice(2);
if (!out) { console.error('usage: compare.mjs PUBLISHED RENDERED OUT_DIR [ANCHOR,...]'); process.exit(2); }
const anchors = (list || 'cover,toc').split(',').map((s) => s.trim()).filter(Boolean);
const url = (s) => (/^https?:\/\//.test(s) ? s : 'file://' + resolve(s));
mkdirSync(out, { recursive: true });
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME, headless: true, args: ['--no-sandbox'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1100, height: 1400, deviceScaleFactor: 1 });
let missing = 0;
for (const [side, src] of [['published', published], ['rendered', rendered]]) {
  await page.goto(url(src), { waitUntil: 'networkidle0', timeout: 120000 });
  for (const [i, id] of anchors.entries()) {
    const found = await page.evaluate((id) => {
      if (id === 'cover') { window.scrollTo(0, 0); return true; }
      const el = id === 'toc'
        ? (document.getElementById('table-of-contents') || document.querySelector('div.toc'))
        : (document.getElementById(id) || document.querySelector(`[name="${CSS.escape(id)}"]`));
      if (!el) return false;
      const box = el.getBoundingClientRect();
      if (!el.getClientRects().length || (box.width === 0 && box.height === 0)) return false; // not rendered
      el.scrollIntoView({ block: 'start' });
      window.scrollBy(0, -12);
      return true;
    }, id);
    if (!found) { console.log(`MISSING ${side} #${id} (absent or not rendered)`); missing++; continue; }
    await new Promise((r) => setTimeout(r, 400));
    const file = `${out}/${i + 1}-${id.replace(/[^A-Za-z0-9._-]/g, '_')}-${side}.png`;
    await page.screenshot({ path: file });
    console.log(`captured ${file}`);
  }
}
await browser.close();
process.exit(missing ? 1 : 0);
