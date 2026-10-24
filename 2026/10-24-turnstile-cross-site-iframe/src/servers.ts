// 自前ドメイン Y (https) と設置先 X (http) のサーバー。届いた token ごとに Siteverify を投げて jsonl に書く
import https from "node:https";
import http from "node:http";
import fs from "node:fs";
import { embedPage, widgetPage, type PageName } from "./pages.ts";

export type Config = {
  sitekey: string;
  secret: string;
  widgetHost: string; // Turnstile の widget に登録したホスト名 (127.0.0.1 に向け、証明書を用意したもの)
  widgetPort: number;
  embedHost: string; // 設置先として使う、widget に登録していないホスト名 (lvh.me など)
  embedPort: number;
  certPath: string;
  keyPath: string;
  outPath: string;
};

export type Row = {
  at: string; browser: string; page: PageName; location: string; referrer: string | null;
  ancestorOrigins: string[] | null; ua: string; requestOrigin: string | null;
  gotToken: boolean; tokenLen: number | null; error: string | null; siteverify: unknown;
};

export async function startServers(config: Config, onRow: (row: Row) => void) {
  const widgetOrigin = `https://${config.widgetHost}:${config.widgetPort}`;
  const reportUrl = `${widgetOrigin}/report`;
  const pages: Record<"y" | "x", Record<string, string>> = {
    y: {
      "/direct.html": widgetPage({ sitekey: config.sitekey, page: "Y_direct", reportUrl, instruction: "手順 1: チェックボックスを押してください (自動で済んだときは押さなくてよい)。" }),
      "/widget.html": widgetPage({ sitekey: config.sitekey, page: "X_iframe_Y", reportUrl, instruction: "" }),
    },
    x: {
      "/embed.html": embedPage({ widgetOrigin }),
      "/direct.html": widgetPage({ sitekey: config.sitekey, page: "X_direct", reportUrl, instruction: "手順 3 (対照): 何も押さず、出るエラーの番号を見るだけです。" }),
    },
  };

  const handler = (site: "y" | "x") => async (req: http.IncomingMessage, res: http.ServerResponse) => {
    const path = new URL(req.url ?? "/", "http://x").pathname;
    if (site === "y" && path === "/report") {
      res.setHeader("access-control-allow-origin", "*");
      res.setHeader("access-control-allow-headers", "content-type");
      if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return; }
      let body = "";
      for await (const chunk of req) body += chunk;
      const report = JSON.parse(body);
      const verify = report.token ? await siteverify({ secret: config.secret, token: report.token }) : null;
      const row: Row = {
        at: new Date().toISOString(), browser: browserName(report.ua), page: report.page, location: report.location,
        referrer: report.referrer || null, ancestorOrigins: report.ancestorOrigins, ua: report.ua,
        requestOrigin: req.headers.origin ?? null, gotToken: Boolean(report.token),
        tokenLen: report.token ? report.token.length : null, error: report.error ?? null, siteverify: verify,
      };
      fs.appendFileSync(config.outPath, JSON.stringify(row) + "\n");
      res.writeHead(204); res.end();
      onRow(row);
      return;
    }
    const html = pages[site][path];
    if (!html) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    res.end(html);
  };

  const ySrv = https.createServer({ key: fs.readFileSync(config.keyPath), cert: fs.readFileSync(config.certPath) }, handler("y"));
  const xSrv = http.createServer(handler("x"));
  await new Promise<void>((resolve) => ySrv.listen(config.widgetPort, "127.0.0.1", resolve));
  await new Promise<void>((resolve) => xSrv.listen(config.embedPort, "127.0.0.1", resolve));
  return {
    urls: {
      yDirect: `${widgetOrigin}/direct.html`,
      xIframe: `http://${config.embedHost}:${config.embedPort}/embed.html`,
      xDirect: `http://${config.embedHost}:${config.embedPort}/direct.html`,
    },
    close() {
      ySrv.closeAllConnections(); xSrv.closeAllConnections();
      ySrv.close(); xSrv.close();
    },
  };
}

async function siteverify(params: { secret: string; token: string }): Promise<unknown> {
  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ secret: params.secret, response: params.token }),
  });
  return await response.json();
}

function browserName(ua: string): string {
  if (/Edg\//.test(ua)) return "edge";
  if (/Firefox\//.test(ua)) return "firefox";
  if (/Chrome\//.test(ua)) return "chrome";
  if (/Safari\//.test(ua)) return "safari";
  return "other";
}
