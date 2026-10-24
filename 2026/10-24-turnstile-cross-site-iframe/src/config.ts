import { parseArgs } from "node:util";
import type { Config } from "./servers.ts";

export function readConfig(extraOptions: Record<string, { type: "string" }> = {}) {
  const { values } = parseArgs({
    options: {
      "widget-host": { type: "string" },
      "widget-port": { type: "string", default: "4719" },
      "embed-host": { type: "string", default: "lvh.me" },
      "embed-port": { type: "string", default: "4718" },
      cert: { type: "string" },
      key: { type: "string" },
      out: { type: "string" },
      ...extraOptions,
    },
  });
  const sitekey = process.env.TURNSTILE_SITE_KEY;
  const secret = process.env.TURNSTILE_SECRET_KEY;
  if (!sitekey || !secret) throw new Error("TURNSTILE_SITE_KEY と TURNSTILE_SECRET_KEY を環境変数で渡してください");
  for (const name of ["widget-host", "cert", "key", "out"] as const) {
    if (!values[name]) throw new Error(`--${name} が必要です`);
  }
  const config: Config = {
    sitekey, secret,
    widgetHost: values["widget-host"]!, widgetPort: Number(values["widget-port"]),
    embedHost: values["embed-host"]!, embedPort: Number(values["embed-port"]),
    certPath: values.cert!, keyPath: values.key!, outPath: values.out!,
  };
  return { config, values };
}
