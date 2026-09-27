// Copyright 2026 OASIS Open
// SPDX-License-Identifier: Apache-2.0
// Authored by Michael Coletta, Technical Advisor to OASIS Open.
//
// HTML to PDF in headless Chrome, on the OASIS pipeline's page geometry
// (A4 portrait, 25mm top and bottom, 20mm sides, as .github/src/pipeline/
// pdf_renderer.py) with the footer of a published OASIS PDF: the document
// name and its track on the left, the copyright line in the centre, the
// document date and "Page x of y" on the right. No running header: the
// published PDFs have none, and a title there repeats on the cover page.
//
// Chrome, because GitHub's runners and most desktops have it; the pipeline's
// own PDF step prints the same footer with wkhtmltopdf (proposal 012).
//
//   CHROME=/path/to/chrome node print_pdf.mjs IN.html OUT.pdf FOOTER.json
//
// FOOTER.json is what render/footer.py prints for the Markdown source.
import puppeteer from 'puppeteer-core';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const [input, output, footerJson] = process.argv.slice(2);
const f = JSON.parse(readFileSync(footerJson, 'utf8'));
for (const k of ['name', 'track', 'copyright', 'date']) {
  if (!f[k]) { console.error(`print_pdf: ${footerJson} has no ${k}`); process.exit(2); }
}
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME, headless: true, args: ['--no-sandbox'],
});
const page = await browser.newPage();
await page.goto('file://' + resolve(input), { waitUntil: 'networkidle0', timeout: 180000 });
const small = 'font-family: Arial, sans-serif; font-size: 8pt; color: #333; width: 100%; margin: 0 20mm;';
await page.pdf({
  path: output,
  format: 'A4',
  margin: { top: '25mm', right: '20mm', bottom: '25mm', left: '20mm' },
  printBackground: true,
  displayHeaderFooter: true,
  headerTemplate: '<span></span>',
  footerTemplate: `<div style="${small} display: flex; justify-content: space-between; align-items: flex-end;">
    <span>${esc(f.name)}<br>${esc(f.track)}</span><span>${esc(f.copyright)}</span>
    <span style="text-align: right;">${esc(f.date)}<br>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>`,
});
await browser.close();
