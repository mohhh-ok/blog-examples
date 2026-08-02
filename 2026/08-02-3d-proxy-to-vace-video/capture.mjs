import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs/promises';
import { createReadStream, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = __dirname;
const PASS = process.argv[2] || 'rgb'; // 'rgb' or 'depth'
const FRAMES_DIR = path.join(ROOT, PASS === 'depth' ? 'frames-depth' : 'frames');
const PORT = 4823;

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.json': 'application/json', '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.css': 'text/css', '.wasm': 'application/wasm',
};

function serve() {
  return new Promise((resolve) => {
    const server = http.createServer(async (req, res) => {
      try {
        const url = new URL(req.url, `http://localhost:${PORT}`);
        let pathname = decodeURIComponent(url.pathname);
        if (pathname === '/') pathname = '/index.html';
        const filePath = path.join(ROOT, pathname);
        if (!filePath.startsWith(ROOT)) { res.statusCode = 403; return res.end('forbidden'); }
        const st = statSync(filePath);
        if (!st.isFile()) { res.statusCode = 404; return res.end('not found'); }
        const ext = path.extname(filePath).toLowerCase();
        res.setHeader('Content-Type', MIME[ext] || 'application/octet-stream');
        res.setHeader('Cache-Control', 'no-store');
        createReadStream(filePath).pipe(res);
      } catch (e) {
        res.statusCode = 404; res.end('not found: ' + e.message);
      }
    });
    server.listen(PORT, () => resolve(server));
  });
}

async function main() {
  await fs.rm(FRAMES_DIR, { recursive: true, force: true });
  await fs.mkdir(FRAMES_DIR, { recursive: true });

  const server = await serve();
  console.log(`http://localhost:${PORT}`);

  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.on('console', (msg) => console.log('[page]', msg.type(), msg.text()));
  page.on('pageerror', (err) => console.error('[pageerror]', err));

  await page.goto(`http://localhost:${PORT}/?pass=${encodeURIComponent(PASS)}`, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__ready && window.__setFrame && window.__meta);
  await page.evaluate(() => window.__ready);

  const meta = await page.evaluate(() => window.__meta);
  console.log('meta', meta);

  for (let f = 0; f < meta.TOTAL_FRAMES; f++) {
    await page.evaluate((n) => window.__setFrame(n), f);
    const buf = await page.locator('canvas').first().screenshot({ type: 'png', omitBackground: false });
    const name = String(f).padStart(4, '0') + '.png';
    await fs.writeFile(path.join(FRAMES_DIR, name), buf);
    if (f % 30 === 0) console.log('frame', f);
  }

  await browser.close();
  server.close();
  console.log('done');
}

main().catch((e) => { console.error(e); process.exit(1); });
