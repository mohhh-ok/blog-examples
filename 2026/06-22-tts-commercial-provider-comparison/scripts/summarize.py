"""results/<model>.json を集計して CSV + マークダウン表を吐く。"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

LANGS = ["ja", "en", "zh", "ko", "fr", "es", "de"]


def main() -> None:
    files = sorted(RESULTS.glob("*.json"))
    if not files:
        raise SystemExit("no result jsons")

    matrix: dict[str, dict[str, dict]] = {}
    for j in files:
        rows = json.loads(j.read_text())
        matrix[j.stem] = {r["lang"]: r for r in rows}

    csv_path = RESULTS / "summary.csv"
    with csv_path.open("w") as f:
        w = csv.writer(f)
        w.writerow(["model", "lang", "bigram_sim", "wer", "cer", "got"])
        for model, by_lang in matrix.items():
            for lang in LANGS:
                r = by_lang.get(lang)
                if r is None:
                    continue
                w.writerow([model, lang, r["bigram_sim"], r["wer"], r["cer"], r["got"]])
    print(f"wrote: {csv_path}")

    md = ["| model | " + " | ".join(LANGS) + " |", "|" + "---|" * (len(LANGS) + 1)]
    for model, by_lang in matrix.items():
        cells = [model]
        for lang in LANGS:
            r = by_lang.get(lang)
            cells.append(f"{r['bigram_sim']:.2f}" if r else "-")
        md.append("| " + " | ".join(cells) + " |")
    md_path = RESULTS / "summary.md"
    md_path.write_text("\n".join(md) + "\n")
    print(f"wrote: {md_path}")
    print()
    print("\n".join(md))


if __name__ == "__main__":
    main()
