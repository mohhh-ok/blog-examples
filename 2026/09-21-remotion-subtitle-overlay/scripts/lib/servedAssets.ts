import fs from "node:fs/promises";
import path from "node:path";

// 実機検証で判明した事実: OffthreadVideo (および @remotion/media の <Video>) の src は
// レンダー用ローカルサーバー (bundleLocation を静的ルートにして renderMedia が立てる) 経由で
// 取得される。file:// をそのまま渡すと、内部の /proxy?src=... エンドポイントが
// "Can only download URLs starting with http:// or https://" で落ちる (確認済み)。
// そのため、参照したいファイルは bundle 出力ディレクトリ配下にコピーし、
// サーバーのルートから見える相対パス (例: /served/background.mp4) を src として渡す。
export async function copyIntoServedDir(args: {
  bundleLocation: string;
  sourcePath: string;
}): Promise<string> {
  const { bundleLocation, sourcePath } = args;
  const fileName = path.basename(sourcePath);
  const destPath = path.join(bundleLocation, "served", fileName);
  await fs.mkdir(path.dirname(destPath), { recursive: true });
  await fs.copyFile(sourcePath, destPath);
  return `/served/${encodeURIComponent(fileName)}`;
}
