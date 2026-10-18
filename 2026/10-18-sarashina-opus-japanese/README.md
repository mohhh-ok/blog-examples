# Sarashina3 mini と Claude Opus 5.5 の日本語比較

SB Intuitions の Sarashina3 mini（API）と Anthropic の Claude Opus 5.5 に、同じ日本語の問題 40 問を出して出力を並べ、
GPT に一対比較で判定させる。これとは別に、筆者本人が読みやすさを盲検で判定するための書き直しを 10 問作り（H01〜H10）、同じ条件で両モデルに出した。

記事: [Sarashina3 miniとClaude Opus 5.5に同じ日本語の問題40問を出して比べた](https://mohhh-ok.github.io/blog/posts/2026/10-18-aisarashina3-miniとclaude-opus-55に同じ日本語の問題40問を出して比べた/)

Sarashina は API で使えるのが mini だけなので、Anthropic の最上位に近いモデルと Sarashina の小さいモデルの比較になる。

## 問題（`data/problems.jsonl`、40 問）

| カテゴリ | 問題数 | 素材 |
|---|---|---|
| 書き直し | 10 | 法令 3（e-Gov 法令検索）・最高裁判決 2（裁判所の裁判例検索）・自作の悪文 5 |
| 敬語 | 4 | 自作（社名・人名は架空） |
| 自由作文 | 4 | 自作 |
| 要約 | 4 | 青空文庫（蜘蛛の糸・手袋を買いに・夢十夜 第一夜・よだかの星。著者はいずれも没後 70 年以上） |
| ニュアンス | 4 | 自作 |
| 漢字の読み | 14 | 自作。難読語 8 と、文脈で読みが決まる同形異音語 6。正誤は機械で採点 |

- 入力には第三者の著作物と個人情報を入れていない。法令と判決は著作権法 13 条で権利の目的とならない。各問の出典 URL と根拠は `source` に書いてある
- 判決は理由のうち人名を含まない部分を使った
- 漢字の読みに SB Intuitions 製のベンチマーク（JKYB）は使っていない
- 自作の問題（31 問: 書き直しの悪文 5・敬語 4・自由作文 4・ニュアンス 4・漢字の読み 14）は Claude Opus 5.5 が書いた。Opus に合う問題になっている可能性がある
- 要約の 4 作品は有名なので、両モデルとも本文を覚えている可能性がある

## 人が読む用の書き直し（`data/problems_h.jsonl`、10 問）

本人の盲検判定をやり直すために作った書き直しの問題。40 問の集計には入れていない。

- 内訳は R01〜R10 と同じで、法令 3（民法 95 条・労働基準法 20 条・特定商取引法 9 条 1 項）・最高裁判決 2・自作の悪文 5。R01〜R10 と同じ条文・判決の箇所・題材は使っていない
- 指示文は R01〜R10 と同じ
- 自作の 5 問も Claude Opus 5.5 が書いた
- `scripts/build_problems_h.py` で作る。判決 PDF の改ページ記号は本文から除いた。古い法令は本文に項番号が無いので、第 2 項以降の行頭に全角の項番号を付けた

## 条件

| | Sarashina3 mini | Claude Opus 5.5 |
|---|---|---|
| モデル名 | `sarashina3-mini` | `claude-opus-5-5` |
| エンドポイント | `POST https://api.sarashina.ai/v1/chat/completions` | `POST https://api.anthropic.com/v1/messages` |
| システムプロンプト | なし | なし |
| サンプリング | 既定（temperature 0.7・top_p 0.9・repetition_penalty 1.05） | 既定（指定できない） |
| thinking | なし | adaptive（切れない）。`output_config.effort = "low"` で最小にした |
| 出力上限 | `max_completion_tokens = 8000` | `max_tokens = 8000`（thinking の分を含む） |

「temperature を揃える」と「Opus の thinking を切る」は、Opus 5.5 の API が受け付けないためできなかった。
2026-10-18 に送ったときの返答は次のとおり。

- `temperature: 0.7` を送ると 400: `` `temperature` is deprecated for this model. ``
- `thinking: {"type": "disabled"}` を送ると 400: `"thinking.type.disabled" is not supported for this model. Use "thinking.type.adaptive" and "output_config.effort" to control thinking behavior.`

そこで両モデルとも各社の既定のサンプリングで揃え、Opus の thinking は effort を最も低い `low` にした。
Opus が thinking に使ったトークン数は、レスポンスの `usage.output_tokens_details.thinking_tokens` として問題ごとに保存してある。
Opus には別モデルへのフォールバック（`fallbacks`）を付けていない。比較対象のモデルが入れ替わらないようにするため。

Sarashina3 mini は 6 RPM・バースト不可なので、リクエストは逐次で、開始間隔を 12 秒空けた。429 が返ったら `Retry-After` 秒待つ。

## 判定

- GPT（`gpt-6.1-sol`。2026-10-18 に OpenAI の `/v1/models` で一番新しい主力モデル）にモデル名を伏せて一対比較させた
- 回答 1・回答 2 の左右を入れ替えて 2 回判定し、2 回で勝者が同じならその勝ち、食い違えば引き分け
- 判定プロンプトの全文: `prompts/judge_rewrite.txt`（書き直し）、`prompts/judge_general.txt`（それ以外。観点は `scripts/judge.py` の `CRITERIA`）
- 書き直しは、回答ごとに「元の文章の意味が保たれているか・情報が落ちていないか」を先に判定させ、そのうえで読みやすさを比べさせた。
  勝敗は `scripts/aggregate.py` で決める。意味が保たれた回答が片方だけならそちらの勝ち、両方保たれていれば読みやすいほうの勝ち、両方とも意味が変わっていれば引き分け。
  読みやすくても意味を変えた書き直し（二重否定の読み違えなど）を勝ちにしないため
- 漢字の読みは GPT 判定もするが、主な指標は機械採点の正答率。回答から空白と句読点・括弧を除き、正解（複数の読みを許す問題は全部）と一致すれば正解
- 判定役に Claude は使っていない（自己採点の偏りを避けるため）
- 書き直しは筆者本人も盲検で読みやすさを判定した。本人の判定は読みやすさだけで、意味の正しさは判定していない（本人がそう明言した）。意味は GPT の判定だけを使う
  - 盲検シートは `scripts/blind_sheet.py` で作る。A/B の割り当ては問題ごとにランダムで、対応表は別ファイルに保存する。各モデルの応答は API の出力を一切加工せずに全文そのまま載せ、シート側の区切りは応答の見出しとぶつからないよう「━━」の行で書く
  - `--keep-assignment` を付けると、今の対応表の A/B の割り当てのままシートだけを作り直す（`--force` は割り当てから引き直す）
  - H01〜H10 のシートは `PROBLEMS_FILE=data/problems_h.jsonl BLIND_KEY=output/blind_key_h.json` で作った。対応表は `output/blind_key_h.json`
  - H01〜H10 で本人が判定したのは 7 問（H01〜H05・H07・H09。判定する問題は本人が選んだ）。シートの「判定:」の行を逐語で `output/human_judgement_h.json` に書いた。各行から読み取った「読みやすいとした回答（A / B）」は Claude が文面から読み取ったもの（H07 の「用途による。文章としてはAで十分だと思うが、チラシなどの場合はBとして構成されていた方がいいかな。」は差なしとした）
  - 本人は、応答の癖でどちらのモデルか見当はついたが、なるべく流されないように読んだと述べている。Opus が書き直しの後に「補足」の節を付けることも本人は知っていた
- R01〜R10 の本人の判定（`output/human_judgement.json`、対応表 `output/blind_key.json`）は無効にした。このときのシートは、書き方の癖でモデルが分からないよう両モデルの出力を同じ規則で整えていた（`scripts/blind_format.py`。見出しの `#` と太字の `**` を外すなど）。その結果、Opus の「補足」の節が本文と地続きの 1 行になり、本文が補足とセットで書かれていることが読み取れないまま本人が判定した。判定の記録はそのまま残してある
- `output/results.md` に、本人の判定を GPT の読みやすさの判定（2 回ぶん）・意味の判定と並べた表がある（R01〜R10 は無効と書いたうえで載せている）

集計の結果は `output/results.md`。

## 限界

- GPT 判定には出力をそのまま見せている。Sarashina は「もちろんです。」などの前置きを付け、Opus は Markdown の見出しや太字を使うことが多いため、書き方の癖でモデルの見当がつく場合がある
- 本人の盲検シートも応答を無加工で載せたので、同じく書き方の癖でモデルの見当がつく。H01〜H10 の判定はこの前提で読む

## 再現手順

依存は [uv](https://docs.astral.sh/uv/) がスクリプト先頭の inline metadata から入れる。PDF の本文抽出に `pdftotext`（poppler）を使う。

```bash
set -a; source ../../.env; set +a      # SARASHINA_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY
python3 scripts/fetch_sources.py       # 法令・判決・青空文庫を /tmp/sarashina-blog/src に取得（SRC_DIR で変更可）
python3 scripts/build_problems.py      # data/problems.jsonl を作る
uv run scripts/run_models.py           # output/raw/{sarashina,opus}/<id>.json と output/request_log.jsonl
uv run scripts/judge.py                # output/judge/<id>_{sarashina,opus}-first.json
python3 scripts/blind_sheet.py         # 盲検シート（/tmp/sarashina-blog/blind-sheet.md）と output/blind_key.json
python3 scripts/import_human.py        # 盲検シートの「判定:」の行を output/human_judgement.json に取り込む（R01〜R10）

# 人が読む用の書き直し H01〜H10
python3 scripts/build_problems_h.py    # data/problems_h.jsonl を作る
PROBLEMS_FILE=data/problems_h.jsonl REQUEST_LOG=output/request_log_h.jsonl uv run scripts/run_models.py
PROBLEMS_FILE=data/problems_h.jsonl uv run scripts/judge.py
PROBLEMS_FILE=data/problems_h.jsonl BLIND_SHEET=/tmp/sarashina-blog/blind-sheet-h.md BLIND_KEY=output/blind_key_h.json python3 scripts/blind_sheet.py

python3 scripts/aggregate.py           # output/results.json と output/results.md（H01〜H10 も別の節に入る。API キー不要）
python3 scripts/render_outputs.py      # outputs.md と outputs/<カテゴリ>.md（全問の問題文・出力・判定。API キー不要）
```

`run_models.py` と `judge.py` は保存済みの問題を飛ばすので、途中で止まっても同じコマンドで続きから回る。問題 ID を引数に渡すとその問題だけを回す。

## 出力

- [`outputs.md`](outputs.md): 全問（40 問と H01〜H10）の問題文、両モデルの出力の全文、GPT の判定 2 回の結果と理由、本人の判定、漢字の正誤を、カテゴリごとの `outputs/<カテゴリ>.md` に読める形で載せた目次。出力は `output/raw` から加工せずに、引用の中に転記している（出力に Markdown の見出しや区切り線が入っているため）
  - 公開の前に、Sarashina の利用規約 第12条に沿って、40 問と H01〜H10 の両モデルの出力に暴力的・わいせつ・差別的な表現、第三者の著作物、実在の個人を特定できる情報が含まれていないことを確認した（2026-10-18）。要約の出力にある作品の引用は青空文庫の著作権切れ作品だけ。K01 の署名例にあるメールアドレスは、問題で与えた架空の社名から作られたドメインと伏せ字（〇〇・xxxx）で、加工せずに載せている
- `output/raw/<model>/<id>.json`: 送ったリクエスト（モデル名・パラメータ）、送信日時、API のレスポンス JSON をそのまま
- `output/request_log.jsonl`: 40 問の全リクエストの開始・終了時刻と HTTP ステータス（429 なら `retry_after`）。H01〜H10 は `output/request_log_h.jsonl`
- `output/judge/<id>_<回答1に置いたモデル>-first.json`: 判定プロンプト全文、GPT の判定（理由つき）、レスポンス JSON
- `output/results.json` / `output/results.md`: 集計
- `output/blind_key.json` / `output/human_judgement.json`: R01〜R10 の盲検シートの対応表と本人の判定（無効にしたもの）
- `output/blind_key_h.json` / `output/human_judgement_h.json`: H01〜H10 の盲検シートの対応表と本人の判定（シートの「判定:」の行を逐語で）
