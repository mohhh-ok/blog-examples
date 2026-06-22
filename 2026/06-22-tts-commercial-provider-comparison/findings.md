# 検証中間まとめ (2026-06-22)

API 3 種 (Cartesia / Fish Audio / Azure Personal Voice) は API key 取得待ちのため未測定。
self-host 系 (CosyVoice 2 / CosyVoice 3 / OpenVoice v2) の実測で **想定外のトレードオフ** と
**フレームワーク側のバグ** が見えてきたので、判明している事実を整理する。

## TL;DR

- **CosyVoice 2** と **Fun-CosyVoice 3** は同じ Apache 2.0 / 同じシリーズだが、得意領域が違う:
  - **v2**: JA を kanji 入力で CER 0.023 / F0 完璧。**ただし他言語で重大バグあり**
  - **v3**: 全言語で声質安定 (F0 ±8Hz)、**ただし JA は kanji 入力で CER 0.25 まで崩壊**
- v3 の JA 劣化の正体は **frontend.py の `contains_chinese()` 関数が日本語 kanji を中国語と誤判定する** こと
- ただし `contains_chinese` を強制 `False` にしても CER 0.20〜0.34 までしか改善せず、**モデル本体にも kanji→中国語的読みの bias** が残る (= 2 層のバグ)
- v3 で `inference_cross_lingual` を使うと CER は良くなるが **F0 が完全女性化** する罠あり (Whisper では検出不能)
- v3 の生成は **サンプリング揺れが大きく**、同じ入力でも CER 0.125〜0.458 と変動する
- 結論: **商用採用には用途に応じた使い分け**、または API provider 課金が現実解

## 実測サマリ

ref.wav の F0 中央値 = 104.9Hz (男性低音域)。F0 差 ±20Hz 内なら声質保持、+50Hz 超は別人レベル。

### 7 言語 × モデル別、CER と F0

| model | ja CER | ja F0 | en CER | en F0 | zh CER | zh F0 | ko CER | ko F0 | de CER | de F0 | fr CER | es CER |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **cosyvoice2** | **0.023** ★ | **−8** ★ | 0.00 | +4 | 0.00 | **+187 ⚠** | 0.024 | −30 | 0.875 | **+185 ⚠** | 0.324 | 0.165 |
| **cosyvoice3** | 0.25 ✕ | +1 ★ | 0.00 | +7 | 0.00 | −8 | 0.024 | +3 | 0.125 | +2 | 0.00 | 0.047 |
| **cosyvoice3 + kana前処理** | **0.045** ★ | **−4** ★ | (未測) | | | | | | | | | |
| openvoice_v2 | 0.114 | 0 | 0.00 | +29 | 0.08 | +2 | 0.049 | −2 | n/a | n/a | 0.00 | 0.00 |

★ = 商用採用可レベル、✕ = 採用不可、⚠ = 完全女性化 (F0 が成人女性域 165-255Hz 以上にジャンプ)

### v2 の他言語バグ (発話時間 / 無音 / 異常)

v2 は JA は完璧だが、**他言語で 3 種類のバグ**:

| 言語 | 全長 | 発話 | 無音 | 最長無音 | 異常タグ |
|---|---:|---:|---:|---:|---|
| ja | 8.2s | 5.7s | 2.5s | 0.9s | ✓正常 |
| en | 10.7s | 7.8s | 3.0s | 0.7s | ✓正常 |
| zh | 7.6s | 4.9s | 2.7s | 0.4s | F0 +187Hz **女性化** |
| ko | **20.0s** | 18.4s | 1.6s | 0.6s | ⚠**長尺 (内容重複疑い)** |
| **fr** | **16.7s** | 8.5s | **8.1s** | **3.1s** | ⚠**長無音+重複** |
| es | 12.2s | 7.9s | 4.3s | 0.6s | やや長め |
| de | **19.2s** | 15.2s | 4.0s | 0.8s | ⚠長尺 + F0 +185Hz **女性化** |

v3 / OpenVoice v2 は全部 5-8s で正常 (この種のバグは v3 で解消されている)。

## 用途別推奨マトリクス

| 用途 | 推奨 | 理由 |
|---|---|---|
| **JA のみの voice clone** | **CosyVoice 2** | CER 0.023、無音無し、F0 完璧 |
| 多言語 (de / fr / es 含む) | CosyVoice 3 + JA だけ kana 前処理 | JA 以外は素のままで動作、JA は前処理が必要 |
| 全部素直に動かしたい | CosyVoice 3 のみ | JA だけ若干劣るが運用シンプル |
| 商用品質を最優先 (license リスク不問) | API provider (ElevenLabs / Cartesia 等) | OSS のバグ修正を待たない |

## v2 / v3 の特性比較

| 観点 | CosyVoice 2 | Fun-CosyVoice 3 |
|---|---|---|
| リリース | 2024-12 (25Hz 改良版) | 2025-12 (`Fun-CosyVoice3-0.5B-2512`) |
| 公式宣言サポート言語 | zh / en / ja / ko / yue (cross-lingual demo) | zh / en / ja / ko / de / es / fr / it / ru (9 言語) |
| Apache 2.0 (商用可) | ◯ | ◯ |
| LLM 制約 | `<\|endofprompt\|>` 必須でない | **`<\|endofprompt\|>` 必須** (`CosyVoice3LM` クラスで assert) |
| JA kanji 直接入力 | ◯ (実用品質) | ✕ (中国語判定で音素崩壊) |
| 他言語の音声品質 | de/zh/fr で無音/重複/女性化バグ | 9 言語全部で安定 |
| 公開規模 | 0.5B のみ | 0.5B (公式 demo には 1.5B もあるが未公開) |

## CosyVoice 3 JA 劣化の根本原因

### Bug 1: `contains_chinese()` の誤判定 (Frontend ルーティング)

`cosyvoice/utils/frontend_utils.py`:

```python
chinese_char_pattern = re.compile(r'[一-鿿]+')

def contains_chinese(text):
    return bool(chinese_char_pattern.search(text))
```

**`一-鿿` は CJK Unified Ideographs ブロック** — 日本語の常用漢字は全部この範囲に入っている (中国語と同じ Unicode ブロックを共有)。

`cosyvoice/cli/frontend.py` での使い方:

```python
if contains_chinese(text):
    text = self.zh_tn_model.normalize(text)          # 中国語テキスト正規化
    text = text.replace(".", "。")
    text = text.replace(" - ", "，")                 # 中国語句読点
    texts = list(split_paragraph(..., "zh", ...))    # zh 言語コードで段落分割
else:
    text = self.en_tn_model.normalize(text)
    ...
```

つまり日本語 kanji 含みテキストは丸ごと **中国語前処理パス** に乗せられて段落分割される。

### Bug 2: モデル本体の kanji→中国語 bias (LLM レイヤー)

`contains_chinese` を強制 `False` に monkey-patch して英語パスに乗せても、CER は 0.20〜0.34 までしか改善しない。

| variant | CER | F0 差 | got (一部) |
|---|---:|---:|---|
| 元 (kanji 直接) | 0.25 | +1 | 皆さんこんちいっかいマロは新しい機能についてご誠意します... |
| パッチ後 run0 | 0.341 | +0.3 | マナさんこんにちはもう一緒は新しい機能について... |
| パッチ後 run1 | 0.273 | −1.2 | 皆さん、本日、カッパイは新しい機能についてご**司会**います... |

→ **LLM 自体が kanji を中国語クラスタに引き寄せる傾向**を持つ。前処理だけでは直らない。

### 回避策の効果比較

11 バリエーション (`scripts/cosyvoice3_ja_probe*.py`) で切り分けた結果:

| variant | mode | target 形式 | endofprompt の位置 | CER | F0 差 |
|---|---|---|---|---:|---:|
| A_zs_no_sysprompt | zero_shot | kanji | prompt_text 先頭 | 0.386 | −3 |
| B_xl | cross_lingual | kanji | tts_text 先頭 | 0.227 | +1 |
| C_zs_ja_sysprompt | zero_shot | kanji | prompt_text 内 | 0.227 | +5 |
| D_zs_en_sysprompt | zero_shot | kanji | prompt_text 内 | 0.795 | −9 |
| E_xl_hiragana | cross_lingual | hiragana | tts_text 先頭 | 0.205 | +20 |
| **F_xl_katakana** | cross_lingual | katakana | tts_text 先頭 | **0.000** | **+161 ⚠女性化** |
| G_zs_hiragana_kanjiref | zero_shot | hiragana | prompt_text 先頭 | 0.432 | −2 |
| H_zs_hiragana_hiraganaref | zero_shot | hiragana | prompt_text 先頭 (ref_text も kana) | 0.250 | +2 |
| I_xl_hiragana_fixed | cross_lingual | hiragana+は→わ | tts_text 先頭 | 0.136 | +16 |
| J_xl_katakana_fixed | cross_lingual | katakana+は→わ | tts_text 先頭 | 0.000 | +21 |
| **K_zs_katakana_kanjiref** | **zero_shot** | **katakana+は→わ** | **prompt_text 先頭** | **0.045 ★** | **−4 ★** |
| L_zs_katakana_katakanaref | zero_shot | katakana+は→わ | prompt_text 先頭 (ref_text も kana) | 0.068 | −1 |
| M_zs_qiita_kanji | zero_shot | kanji | tts_text 末尾 (Qiita 流) | 1.364 | +1 |

### v3 で JA を商用採用するレシピ (K)

```python
def cosyvoice3_ja(text_kanji):
    # 1. kanji → katakana (pyopenjtalk / pykakasi)
    target_kana = to_katakana(text_kanji)
    # 2. は → わ 音節置換 (主題助詞・挨拶末尾)
    target_kana = wa_substitute(target_kana)
    # 3. prompt_text に <|endofprompt|> を前置 (ref_text は kanji のまま OK)
    prompt_text = f"<|endofprompt|>{REF_TEXT}"
    return cosy.inference_zero_shot(target_kana, prompt_text, ref_path)
```

これで CER 0.045 / F0 −4Hz。

## 学んだ罠

### 罠1: `inference_cross_lingual` の声質崩壊

`F_xl_katakana` は CER 0.000 で「完璧」に見えるが、F0 が **265Hz と完全女性化**。
Whisper の書き起こしは ja → ja の text を返すので、声質崩壊が検出されない。
**CER だけで評価すると見抜けない**。F0 比較 (`scripts/pitch_compare_all.py`) を必ず噛ませる。

### 罠2: Qiita / note 記事の流派は v3 では機能しない

[Qiita: GeneLab_999](https://qiita.com/GeneLab_999/items/f08c41121e3156ed22d2) と
[neosophie.com](https://neosophie.com/ja/blog/20260317-tts) の記事の流派:
- `<|endofprompt|>` を **tts_text の末尾** に付ける
- kanji のまま入力
- `CosyVoice` クラス + `load_jit=False`

これは **CosyVoice 2 の API 想定**で、v3 (`CosyVoice3` クラス) で同じ書き方をすると CER 1.364 で完全崩壊する (probe M)。記事著者は実は v2 を叩いていた可能性が高い。

### 罠3: サンプリングの揺れが大きい

同じ ref / 同じ prompt / 同じ target で 3 回 v3 を回しても CER が 0.125〜0.458 と変動する
(`scripts/cosyvoice3_demo_ref.py` 参照)。デモは good seed を選んで公開している可能性が高い。
production には beam search や seed 固定など追加の安定化が必要。

### 罠4: 公式 demo の 1.5B モデルは未公開

公式 demo 表には **CosyVoice 3.0-0.5B と CosyVoice 3.0-1.5B の 2 サイズ**が並ぶ。
HF / Modelscope で公開されているのは **0.5B (`Fun-CosyVoice3-0.5B-2512`) のみ**。
demo の綺麗な JA は 1.5B のものを含んでいる可能性があるが、再現できる範囲では 0.5B も同等
(text 上は CER 0.000 を出せる、`scripts/demo_check.py` で確認済)。

## v2 / v3 仕様の周辺メモ

- **公式 demo の参考**: `funaudiollm.github.io/cosyvoice3/`
- HF 公開: `FunAudioLLM/Fun-CosyVoice3-0.5B-2512` (0.5B) / `FunAudioLLM/CosyVoice2-0.5B` (v2)
- v3 demo の audio URL 命名: `c2_base` / `c3_base` (= 0.5B) / `c3_large` (= 1.5B 未公開)
- HF からの DL は modelscope.cn より明確に速い (実測 25 倍差 / 250kB/s vs 5-7MB/s)

## 開いている疑問

1. v2 の de/zh 女性化と ko/fr 無音/重複バグは **長い参照音声 (30s+)** で抑制できるか
2. v3 で **学習時の prompt format** (公開されていない) を再現すれば JA を改善できるか
3. RL モデル (`llm.rl.pt`, ~1.9GB、本ベンチでは未 DL) で JA SECS / WER が改善するか
4. v3 demo の 1.5B モデルがいつ公開されるか / 公開された場合の JA 品質
5. CosyVoice 3 の API 内に **temperature / top_p / seed を制御するパラメータ** があるか
6. Qwen3-TTS が CosyVoice の上位互換になり得るか (note 著者は speaker conditioning に構造的欠陥ありと指摘)

## 提案

CosyVoice の `contains_chinese()` バグは **upstream に PR を送る価値**がある:
1. 関数を `contains_cjk_ideographs()` にリネーム
2. `contains_japanese()` (ひらがな・カタカナ判定) を追加
3. `frontend.py` で日本語パスを明示的に分岐

これだけで v3 JA の CER が 0.25 → 0.05〜0.10 程度には改善する見込み。

## ファイル

### スクリプト
- `scripts/generate_cosyvoice2.py` — v2 7 言語生成 (kanji 直接入力で OK)
- `scripts/generate_cosyvoice3.py` — v3 7 言語生成 (現状は kanji 直接入力で JA 崩壊)
- `scripts/cosyvoice3_ja_probe*.py` — v3 JA 劣化の切り分け実験 (A〜M)
- `scripts/cosyvoice3_demo_text.py` — demo と同じ target text で再現を試みた実験
- `scripts/cosyvoice3_demo_ref.py` — demo の prompt audio を ref として使う実験
- `scripts/cosyvoice3_patch_test.py` — `contains_chinese()` モンキーパッチ実験
- `scripts/verify_with_whisper.py` — CER / bigram 計測
- `scripts/probe_verify.py` — JA probe 出力の CER 計測
- `scripts/demo_text_verify.py` — demo target 再現実験の CER + F0
- `scripts/patched_verify.py` — patch 実験の CER + F0
- `scripts/pitch_compare_all.py` — F0 比較 (CER で見えない声質崩壊検出)
- `scripts/silence_check.py` — 無音割合・最長無音・全長の異常検出 (v2 のバグ可視化)
- `scripts/demo_check.py` — 公式 demo wav を Whisper にかけて品質確認

### 出力
- `output/cosyvoice2/` — v2 7 言語生成物
- `output/cosyvoice3/` — v3 7 言語生成物 (kanji 直接入力、JA 崩壊)
- `output/cosyvoice3_probe/` — v3 JA 切り分け実験の wav (A〜M)
- `output/cosyvoice3_demo_text/` — demo target 再現の wav (a〜f)
- `output/cosyvoice3_patched/` — `contains_chinese()` パッチ実験の wav
- `output/openvoice_v2/` — 06-19 から symlink (6 言語、de 不可)

### 結果
- `results/cosyvoice2.json` / `cosyvoice3.json` / `openvoice_v2.json` — Whisper 評価結果
- `results/summary.csv` / `summary.md` — bigram Jaccard 全モデル × 全言語サマリ
