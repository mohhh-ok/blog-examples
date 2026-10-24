// Playwright 版。同じ 3 ページ (と localhost への直接描画) を開き、出なければチェックボックスを押して結果を待つ。
// 手元では headless・headed・本体の Chrome (--channel chrome) のどれでも、押すと 600010 になり token は取れなかった。
import { chromium, webkit } from "playwright";
import { readConfig } from "./config.ts";
import { startServers } from "./servers.ts";

const { config, values } = readConfig({ browser: { type: "string" }, channel: { type: "string" }, headed: { type: "string" } });
const browserType = values.browser === "webkit" ? webkit : chromium;
const servers = await startServers(config, () => {});
const cases = [
  { name: "Y_direct", url: servers.urls.yDirect },
  { name: "X_iframe_Y", url: servers.urls.xIframe },
  { name: "X_direct", url: servers.urls.xDirect },
  { name: "X_direct_localhost", url: `http://localhost:${config.embedPort}/direct.html` },
];

const browser = await browserType.launch({ headless: values.headed !== "1", channel: values.channel });
try {
  for (const testCase of cases) {
    const context = await browser.newContext({ ignoreHTTPSErrors: true });
    const page = await context.newPage();
    await page.goto(testCase.url, { timeout: 20_000 });
    let clicked = false;
    let result: { token?: string; error?: string } | null = null;
    for (let i = 0; i < 14 && !result; i++) {
      // iframe の中の結果は widget のページ (Y) の window にある
      for (const frame of page.frames()) {
        result ??= await frame.evaluate(() => (window as unknown as { __result: { token?: string; error?: string } | null }).__result ?? null).catch(() => null);
      }
      if (!result && !clicked && i >= 2) {
        const challenge = page.frames().find((frame) => frame.url().startsWith("https://challenges.cloudflare.com"));
        const box = challenge ? await (await challenge.frameElement()).boundingBox() : null;
        if (box) { await page.mouse.click(box.x + 20, box.y + box.height / 2); clicked = true; }
      }
      console.log(new Date().toISOString(), testCase.name, "poll", i, result ? "result" : "none");
      if (!result) await page.waitForTimeout(3_000);
    }
    console.log(JSON.stringify({ case: testCase.name, gotToken: Boolean(result?.token), clicked, error: result?.error ?? (result ? null : "no-result") }));
    await context.close();
  }
} finally {
  await browser.close();
  servers.close();
}
