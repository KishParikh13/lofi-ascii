#!/usr/bin/env node
// extract.js — open a URL in headless Chrome, extract visible text nodes and
// image bounding boxes, save a full-viewport screenshot, write JSON to stdout.
//
// Usage: node extract.js <url> <out.png> [viewport=1440x900] [waitMs=2500]

const puppeteer = require('puppeteer-core');

const CHROME = process.env.CHROME_PATH ||
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

(async () => {
  const url = process.argv[2];
  const out = process.argv[3];
  const viewport = (process.argv[4] || '1440x900').split('x').map(Number);
  const waitMs = Number(process.argv[5] || 2500);
  if (!url || !out) {
    console.error('usage: node extract.js <url> <out.png> [viewport=WxH] [waitMs=N]');
    process.exit(2);
  }

  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars'],
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: viewport[0], height: viewport[1] });
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    await new Promise(r => setTimeout(r, waitMs));

    const data = await page.evaluate(() => {
      const visible = (rect) =>
        rect.width > 0 && rect.height > 0 &&
        rect.bottom > 0 && rect.right > 0 &&
        rect.top < window.innerHeight && rect.left < window.innerWidth;

      // ── text nodes ─────────────────────────────────────────────────────
      const texts = [];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const node = walker.currentNode;
        const raw = node.nodeValue;
        if (!raw || !raw.trim()) continue;
        const parent = node.parentElement;
        if (!parent) continue;
        // Skip text inside SVGs (it's usually aria labels for icons — visually invisible).
        if (parent.closest('svg, [aria-hidden="true"], .visuallyhidden, .sr-only')) continue;
        // Skip hidden parents
        const cs = getComputedStyle(parent);
        if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) < 0.1) continue;
        // Skip text styled to be off-screen / 1px (common accessibility-only patterns)
        if (parent.offsetWidth <= 1 || parent.offsetHeight <= 1) continue;
        // Per-line bounding boxes using Range.getClientRects() (handles wrapping).
        const range = document.createRange();
        range.selectNodeContents(node);
        const rects = Array.from(range.getClientRects()).filter(visible);
        if (rects.length === 0) continue;
        // Collapse whitespace
        const text = raw.replace(/\s+/g, ' ').trim();
        // Single-rect: easy. Multi-rect: split by approximate proportional offset.
        if (rects.length === 1) {
          const r = rects[0];
          texts.push({
            text,
            x: r.x, y: r.y, w: r.width, h: r.height,
            fontSize: parseFloat(cs.fontSize),
            color: cs.color,
            weight: cs.fontWeight,
          });
        } else {
          // Approximate: distribute characters across rects proportionally to width.
          const totalW = rects.reduce((s, r) => s + r.width, 0);
          const chars = text.length;
          let offset = 0;
          for (const r of rects) {
            const n = Math.max(1, Math.round((r.width / totalW) * chars));
            const slice = text.slice(offset, offset + n);
            offset += n;
            if (!slice.trim()) continue;
            texts.push({
              text: slice,
              x: r.x, y: r.y, w: r.width, h: r.height,
              fontSize: parseFloat(cs.fontSize),
              color: cs.color,
              weight: cs.fontWeight,
            });
          }
        }
      }

      // ── image / media nodes ────────────────────────────────────────────
      const images = [];
      const seen = new Set();
      const sel = 'img, picture, svg, video, [style*="background-image"]';
      document.querySelectorAll(sel).forEach((el) => {
        if (seen.has(el)) return;
        seen.add(el);
        const rect = el.getBoundingClientRect();
        if (!visible(rect) || rect.width < 24 || rect.height < 24) return;
        const cs = getComputedStyle(el);
        if (cs.visibility === 'hidden' || cs.display === 'none') return;
        images.push({
          x: rect.x, y: rect.y, w: rect.width, h: rect.height,
          tag: el.tagName.toLowerCase(),
        });
      });

      // Sort: top-to-bottom, left-to-right
      texts.sort((a, b) => (a.y - b.y) || (a.x - b.x));
      images.sort((a, b) => (a.y - b.y) || (a.x - b.x));

      return {
        viewport: { w: window.innerWidth, h: window.innerHeight },
        device_pixel_ratio: window.devicePixelRatio || 1,
        page: { w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight },
        texts, images,
      };
    });

    await page.screenshot({ path: out, fullPage: false });
    console.log(JSON.stringify(data));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error('extract failed:', e.message);
  process.exit(1);
});
