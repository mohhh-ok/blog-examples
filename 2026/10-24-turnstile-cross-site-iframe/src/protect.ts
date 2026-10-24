// 対策の計測版。Origin の偽装を curl で示し、frame-ancestors と Sec-Fetch-Dest で iframe のページを守れるかを Playwright で見る。
// サーバーを立て、curl → Chromium → WebKit の順に 1 本ずつ流し、結果を jsonl に書いて止まる。
import https from "node:https";
import http from "node:http";
import fs from "node:fs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { parseArgs } from "node:util";
import { chromium, webkit, type BrowserType } from "playwright";

const { values } = parseArgs({
  options: {
    "widget-host": { type: "string" },
    "widget-port": { type: "string", default: "4719" },
    "embed-port": { type: "string", default: "4718" },
    cert: { type: "string" },
    key: { type: "string" },
    out: { type: "string" },
    browsers: { type: "string", default: "chromium,webkit" },
  },
});
const secret = process.env.TURNSTILE_SECRET_KEY;
if (!secret) throw new Error("TURNSTILE_SECRET_KEY を環境変数で渡してください (偽の token を Siteverify に送るのに使う)");
for (const name of ["widget-host", "cert", "key", "out"] as const) {
  if (!values[name]) throw new Error(`--${name} が必要です`);
}
const widgetOrigin = `https://${values["widget-host"]}:${values["widget-port"]}`;
const embedPort = Number(values["embed-port"]);
const registeredOrigin = `http://lvh.me:${embedPort}`;
const unregisteredOrigin = `http://localhost:${embedPort}`;
// public key → 設置を許したオリジン。本番では DB に置く
const sites: Record<string, string[]> = { "site-a": [registeredOrigin] };
// Turnstile のテスト用 sitekey (常に通る)。描画できたかを見るだけに使う
const TEST_SITEKEY = "1x00000000000000000000AA";
const outPath = values.out!;

function write(row: Record<string, unknown>) {
  const line = JSON.stringify({ at: new Date().toISOString(), ...row });
  fs.appendFileSync(outPath, line + "\n");
  console.log(line);
}

// ---- 自前ドメイン Y ----
const ySrv = https.createServer(
  { key: fs.readFileSync(values.key!), cert: fs.readFileSync(values.cert!) },
  async (req, res) => {
    const url = new URL(req.url ?? "/", widgetOrigin);
    if (url.pathname === "/widget.html") {
      const key = url.searchParams.get("key") ?? "";
      const allowed = sites[key];
      const dest = req.headers["sec-fetch-dest"] ?? null;
      const requestLog = { kind: "request", path: "/widget.html", key, secFetchDest: dest, secFetchSite: req.headers["sec-fetch-site"] ?? null, secFetchMode: req.headers["sec-fetch-mode"] ?? null, referer: req.headers.referer ?? null, ua: req.headers["user-agent"] ?? null };
      if (!allowed) { write({ ...requestLog, status: 404 }); res.writeHead(404); res.end("unknown key"); return; }
      // iframe 以外 (直接開いた・トップレベルで開いた・ヘッダーが無い) には返さない
      if (dest !== "iframe") { write({ ...requestLog, status: 403 }); res.writeHead(403, { "content-type": "text/plain; charset=utf-8" }); res.end("iframe の中でだけ開けます"); return; }
      write({ ...requestLog, status: 200 });
      res.writeHead(200, {
        "content-type": "text/html; charset=utf-8",
        // その key に登録したサイトの中にしか置かせない
        "content-security-policy": `frame-ancestors ${allowed.join(" ")}`,
      });
      res.end(widgetPage({ key }));
      return;
    }
    if (url.pathname === "/session" || url.pathname === "/session-origin-only") {
      let body = "";
      for await (const chunk of req) body += chunk;
      const input = JSON.parse(body || "{}") as { key?: string; turnstileToken?: string };
      const origin = req.headers.origin ?? null;
      const reply = (status: number, payload: Record<string, unknown>) => {
        res.writeHead(status, { "content-type": "application/json" });
        res.end(JSON.stringify(payload));
      };
      // 1. public key と Origin の確認
      if (!origin || !(sites[input.key ?? ""] ?? []).includes(origin)) { reply(403, { ok: false, stage: "origin", origin }); return; }
      if (url.pathname === "/session-origin-only") { reply(200, { ok: true, stage: "origin-only", origin }); return; }
      // 2. Turnstile の token。cData に入れた key と、会話を始める key が同じかも見る
      const siteverify = await verify({ token: input.turnstileToken ?? "" });
      if (siteverify.success !== true || siteverify.cdata !== input.key) { reply(403, { ok: false, stage: "turnstile", siteverify }); return; }
      reply(200, { ok: true, stage: "issued" });
      return;
    }
    res.writeHead(404); res.end();
  },
);

// ---- 設置先 X (lvh.me は登録済み、localhost は未登録として同じサーバーで返す) ----
const xSrv = http.createServer((req, res) => {
  const url = new URL(req.url ?? "/", "http://x");
  if (url.pathname !== "/embed.html") { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
  res.end(`<!doctype html><html><head><meta charset="utf-8"></head><body><h1>設置先</h1>
<iframe id="widget" src="${widgetOrigin}/widget.html?key=site-a" width="420" height="200"></iframe></body></html>`);
});

await new Promise<void>((resolve) => ySrv.listen(Number(values["widget-port"]), "127.0.0.1", resolve));
await new Promise<void>((resolve) => xSrv.listen(embedPort, "127.0.0.1", resolve));
write({ kind: "servers-up", widgetOrigin, registeredOrigin, unregisteredOrigin });

try {
  await runCurl();
  for (const name of values.browsers!.split(",")) {
    await runBrowser({ name, type: name === "webkit" ? webkit : chromium });
  }
} finally {
  ySrv.closeAllConnections(); xSrv.closeAllConnections();
  ySrv.close(); xSrv.close();
  write({ kind: "servers-closed" });
}

// ブラウザ以外からの呼び出し。Origin も Sec-Fetch-Dest も自由に付けられる
async function runCurl() {
  const run = promisify(execFile);
  const cases: { name: string; args: string[] }[] = [
    { name: "session_no_origin", args: ["-X", "POST", `${widgetOrigin}/session`, "-H", "content-type: application/json", "-d", '{"key":"site-a"}'] },
    { name: "origin_only_spoofed", args: ["-X", "POST", `${widgetOrigin}/session-origin-only`, "-H", "content-type: application/json", "-H", `Origin: ${registeredOrigin}`, "-d", '{"key":"site-a"}'] },
    { name: "session_spoofed_no_token", args: ["-X", "POST", `${widgetOrigin}/session`, "-H", "content-type: application/json", "-H", `Origin: ${registeredOrigin}`, "-d", '{"key":"site-a"}'] },
    { name: "session_spoofed_fake_token", args: ["-X", "POST", `${widgetOrigin}/session`, "-H", "content-type: application/json", "-H", `Origin: ${registeredOrigin}`, "-d", '{"key":"site-a","turnstileToken":"forged-token"}'] },
    { name: "widget_no_header", args: [`${widgetOrigin}/widget.html?key=site-a`] },
    { name: "widget_spoofed_dest", args: [`${widgetOrigin}/widget.html?key=site-a`, "-H", "Sec-Fetch-Dest: iframe"] },
  ];
  for (const testCase of cases) {
    // -k: 手元の証明書。-w でステータスだけを最後の行に出す
    const { stdout } = await run("curl", ["-sk", "-m", "20", "-w", "\n%{http_code}", ...testCase.args]);
    const lines = stdout.trimEnd().split("\n");
    const status = Number(lines.pop());
    const body = lines.join("\n");
    write({ kind: "curl", case: testCase.name, args: testCase.args, status, body: body.length > 300 ? `${body.slice(0, 300)}...(${body.length} chars)` : body });
  }
}

async function runBrowser(params: { name: string; type: BrowserType }) {
  const browser = await params.type.launch({ headless: true });
  write({ kind: "browser", browser: params.name, version: browser.version() });
  const cases = [
    { name: "registered_site", url: `${registeredOrigin}/embed.html` },
    { name: "unregistered_site", url: `${unregisteredOrigin}/embed.html` },
    { name: "direct_open", url: `${widgetOrigin}/widget.html?key=site-a` },
  ];
  try {
    for (const testCase of cases) {
      const context = await browser.newContext({ ignoreHTTPSErrors: true });
      const page = await context.newPage();
      const consoleMessages: string[] = [];
      page.on("console", (message) => consoleMessages.push(`[${message.type()}] ${message.text()}`));
      const responses: { url: string; status: number }[] = [];
      page.on("response", (response) => { if (response.url().includes("/widget.html")) responses.push({ url: response.url(), status: response.status() }); });
      const goto = await page.goto(testCase.url, { timeout: 20_000 });
      await page.waitForTimeout(5_000);
      // widget のページの中身 (目印の要素と Turnstile の結果) を、どのフレームにあるかに関係なく探す
      const frames = [];
      for (const frame of page.frames()) {
        const content = await frame.evaluate(() => ({
          marker: document.getElementById("marker")?.textContent ?? null,
          turnstile: (window as unknown as { __turnstile?: string }).__turnstile ?? null,
          bodyText: document.body?.innerText.slice(0, 80) ?? null,
        })).catch((error: Error) => ({ evaluateError: error.message.split("\n")[0] }));
        frames.push({ url: frame.url(), isMain: frame === page.mainFrame(), ...content });
      }
      write({ kind: "browser-case", browser: params.name, case: testCase.name, url: testCase.url, topStatus: goto?.status() ?? null, widgetResponses: responses, frames, console: consoleMessages });
      await context.close();
    }
  } finally {
    await browser.close();
  }
}

function widgetPage(params: { key: string }): string {
  return `<!doctype html><html><head><meta charset="utf-8">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" async defer onload="go()"></script></head>
<body><p id="marker">widget page for ${params.key}</p><div id="w"></div><script>
function go(){ turnstile.render('#w',{sitekey:${JSON.stringify(TEST_SITEKEY)}, cData:${JSON.stringify(params.key)},
  callback:()=>{ window.__turnstile = 'token'; },
  'error-callback':(c)=>{ window.__turnstile = 'error ' + c; return true; }}); }
</script></body></html>`;
}

async function verify(params: { token: string }): Promise<{ success?: boolean; cdata?: string; [key: string]: unknown }> {
  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ secret: secret!, response: params.token }),
  });
  return await response.json();
}
