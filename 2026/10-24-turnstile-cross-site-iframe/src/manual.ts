// 手で押す版。サーバーを立て、ブラウザで 3 ページを開いて押してもらい、届いた結果を jsonl に書く。
// --browsers に並べたブラウザすべてで 3 ページの結果が揃うか、--max-minutes を過ぎたら止まる。
import { readConfig } from "./config.ts";
import { startServers } from "./servers.ts";

const { config, values } = readConfig({ browsers: { type: "string" }, "max-minutes": { type: "string" } });
const browsers = (values.browsers ?? "chrome,safari").split(",");
const maxMinutes = Number(values["max-minutes"] ?? "10");
const pages = ["Y_direct", "X_iframe_Y", "X_direct"];
const seen = new Set<string>();

const servers = await startServers(config, (row) => {
  console.log(JSON.stringify(row));
  // token が取れたページは Siteverify の成功、X_direct はエラーが届いた時点で揃ったとみなす
  const done = row.page === "X_direct" ? row.error !== null : (row.siteverify as { success?: boolean } | null)?.success === true;
  if (done) seen.add(`${row.browser}:${row.page}`);
  if (browsers.every((browser) => pages.every((page) => seen.has(`${browser}:${page}`)))) stop("all pages collected");
});
console.log(new Date().toISOString(), "servers up. 開く順:", servers.urls);

const heartbeat = setInterval(() => console.log(new Date().toISOString(), "waiting", [...seen]), 30_000);
const timer = setTimeout(() => stop(`${maxMinutes} min timeout`), maxMinutes * 60_000);

function stop(reason: string) {
  clearInterval(heartbeat);
  clearTimeout(timer);
  servers.close();
  console.log(new Date().toISOString(), "servers closed:", reason, [...seen]);
}
