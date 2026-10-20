import { readFileSync } from "node:fs";
import { dirname, isAbsolute, join } from "node:path";

// 計測の対象の一覧。tsv の列: id・text (正解の文)・terms (固有名詞。; 区切り、無ければ空)・audio (任意。無ければ <audioDir>/<id>.wav)。
export type ManifestItem = {
  id: string;
  text: string;
  terms: string[];
  audioPath: string;
};

export function readManifest(options: { path: string; audioDir: string | undefined }): ManifestItem[] {
  const lines = readFileSync(options.path, "utf8").split("\n").filter((line) => line.trim() !== "");
  const header = lines[0]?.split("\t") ?? [];
  const column = (name: string) => header.indexOf(name);
  const [idColumn, textColumn, termsColumn, audioColumn] = [column("id"), column("text"), column("terms"), column("audio")];
  if (idColumn < 0 || textColumn < 0 || termsColumn < 0) throw new Error(`${options.path}: header must have id, text, terms`);
  return lines.slice(1).map((line) => {
    const cells = line.split("\t");
    const id = cells[idColumn] ?? "";
    const audio = audioColumn >= 0 ? cells[audioColumn] : undefined;
    return {
      id,
      text: cells[textColumn] ?? "",
      terms: (cells[termsColumn] ?? "").split(";").map((term) => term.trim()).filter((term) => term !== ""),
      audioPath: resolveAudioPath({ manifestPath: options.path, audioDir: options.audioDir, id, audio }),
    };
  });
}

function resolveAudioPath(options: { manifestPath: string; audioDir: string | undefined; id: string; audio: string | undefined }): string {
  if (options.audio !== undefined && options.audio !== "") {
    return isAbsolute(options.audio) ? options.audio : join(dirname(options.manifestPath), options.audio);
  }
  if (options.audioDir === undefined) throw new Error(`no audio column and no --audio-dir for ${options.id}`);
  return join(options.audioDir, `${options.id}.wav`);
}
