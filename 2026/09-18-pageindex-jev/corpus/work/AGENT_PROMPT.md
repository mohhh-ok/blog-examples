# サブエージェント（Claude Code Agent tool, model=haiku）に渡したプロンプト

各 chunk（corpus/work/chunks.json の 1 要素）につき 1 体、並列に起動した。`<site>` と `<numbers>` を chunk ごとに差し替え。

---
Read /Users/masaaki/Dev/playground/pageindex-jev/corpus/work/INSTRUCTIONS.md first and follow it exactly.

Your assigned input files are in /Users/masaaki/Dev/playground/pageindex-jev/corpus/work/<site>/ with these basenames: <numbers>
For each one, read `<n>.md` and write `<n>.json` next to it. Write the JSON with the Write tool. Do not read or modify any other file. Do not run any command. When every assigned file has its .json, reply with one line: the count of files written.
---

目録の仕様本文は src/manifest.ts の MANIFEST_SPEC（INSTRUCTIONS.md に同じ文が入っている）。
