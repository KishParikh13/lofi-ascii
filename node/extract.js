#!/usr/bin/env node
// extract.js — open a URL in headless Chrome and extract:
//   - text nodes (visible body copy + headings)
//   - button-like elements (anchors/buttons styled as buttons)
//   - nav link items (any <nav> descendants)
//   - image-bearing elements (picture, img, svg, video)
//
// Output: JSON to stdout. Screenshot to <out.png>.
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

      const isHidden = (el) => {
        const cs = getComputedStyle(el);
        return cs.visibility === 'hidden' || cs.display === 'none' ||
               parseFloat(cs.opacity) < 0.1;
      };

      // ── Pass 1: identify button-like elements ─────────────────────────────
      const buttonEls = new Set();
      const buttonRects = [];
      const isButtonish = (el) => {
        if (el.tagName === 'BUTTON') return true;
        if (el.getAttribute('role') === 'button') return true;
        if (el.tagName === 'A') {
          const cs = getComputedStyle(el);
          const bg = cs.backgroundColor;
          const br = parseFloat(cs.borderRadius) || 0;
          const bw = parseFloat(cs.borderTopWidth) || 0;
          const hasBg = bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent';
          if ((hasBg || bw > 0) && br >= 4) return true;
        }
        return false;
      };
      document.querySelectorAll('a, button, [role="button"]').forEach((el) => {
        if (isHidden(el)) return;
        const rect = el.getBoundingClientRect();
        if (!visible(rect)) return;
        if (rect.width < 40 || rect.height < 18) return;
        if (!isButtonish(el)) return;
        const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
        if (!text || text.length > 60) return;
        buttonEls.add(el);
        buttonRects.push({
          text,
          x: rect.x, y: rect.y, w: rect.width, h: rect.height,
          style: ((() => {
            const cs = getComputedStyle(el);
            const bg = cs.backgroundColor;
            const hasBg = bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent';
            return hasBg ? 'filled' : 'outline';
          })()),
        });
      });

      // ── Pass 2: identify nav items ────────────────────────────────────────
      const navEls = new Set();
      const navItems = [];
      document.querySelectorAll('nav a, [role="navigation"] a, header nav a, header a').forEach((el) => {
        if (isHidden(el)) return;
        if (buttonEls.has(el)) return;  // don't double-count
        const rect = el.getBoundingClientRect();
        if (!visible(rect)) return;
        const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
        if (!text || text.length > 30) return;
        navEls.add(el);
        navItems.push({
          text,
          x: rect.x, y: rect.y, w: rect.width, h: rect.height,
        });
      });

      // ── Pass 3: text nodes (skip those inside buttons + nav items) ────────
      const texts = [];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const node = walker.currentNode;
        const raw = node.nodeValue;
        if (!raw || !raw.trim()) continue;
        const parent = node.parentElement;
        if (!parent) continue;
        if (parent.closest('svg, [aria-hidden="true"], .visuallyhidden, .sr-only')) continue;
        // Skip if parent is inside a tracked button or nav item
        let p = parent;
        let inButtonOrNav = false;
        while (p) {
          if (buttonEls.has(p) || navEls.has(p)) { inButtonOrNav = true; break; }
          p = p.parentElement;
        }
        if (inButtonOrNav) continue;

        if (isHidden(parent)) continue;
        if (parent.offsetWidth <= 1 || parent.offsetHeight <= 1) continue;

        const range = document.createRange();
        range.selectNodeContents(node);
        const rects = Array.from(range.getClientRects()).filter(visible);
        if (rects.length === 0) continue;
        const cs = getComputedStyle(parent);
        const text = raw.replace(/\s+/g, ' ').trim();
        if (rects.length === 1) {
          const r = rects[0];
          texts.push({
            text, x: r.x, y: r.y, w: r.width, h: r.height,
            fontSize: parseFloat(cs.fontSize),
            weight: cs.fontWeight,
          });
        } else {
          const totalW = rects.reduce((s, r) => s + r.width, 0);
          const chars = text.length;
          let offset = 0;
          for (const r of rects) {
            const n = Math.max(1, Math.round((r.width / totalW) * chars));
            const slice = text.slice(offset, offset + n);
            offset += n;
            if (!slice.trim()) continue;
            texts.push({
              text: slice, x: r.x, y: r.y, w: r.width, h: r.height,
              fontSize: parseFloat(cs.fontSize),
              weight: cs.fontWeight,
            });
          }
        }
      }

      // ── Pass 4: image-bearing elements ────────────────────────────────────
      const images = [];
      const seen = new Set();
      document.querySelectorAll('img, picture, svg, video, [style*="background-image"]').forEach((el) => {
        if (seen.has(el)) return;
        seen.add(el);
        if (isHidden(el)) return;
        const rect = el.getBoundingClientRect();
        if (!visible(rect) || rect.width < 24 || rect.height < 24) return;
        // Skip SVG icons inside nav links / buttons (we render those structurally).
        if (el.closest('nav, header')) return;
        if (buttonEls.size > 0 && [...buttonEls].some((b) => b.contains(el))) return;
        images.push({
          x: rect.x, y: rect.y, w: rect.width, h: rect.height,
          tag: el.tagName.toLowerCase(),
        });
      });

      const sortByPos = (a, b) => (a.y - b.y) || (a.x - b.x);
      texts.sort(sortByPos);
      buttonRects.sort(sortByPos);
      navItems.sort(sortByPos);
      images.sort(sortByPos);

      return {
        viewport: { w: window.innerWidth, h: window.innerHeight },
        device_pixel_ratio: window.devicePixelRatio || 1,
        page: {
          w: document.documentElement.scrollWidth,
          h: document.documentElement.scrollHeight,
        },
        texts, buttons: buttonRects, nav: navItems, images,
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
