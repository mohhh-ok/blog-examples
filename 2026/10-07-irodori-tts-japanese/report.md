# Irodori-TTS v4.1-Small と Fish Audio s2.1-pro の日本語読み・声クローン計測

計測日 2026-10-07。記事本文の下書きではなく、手法と結果の記録。数値の表は `report-numbers.md` (`make_report.py` が JSON から生成) にあり、この文書の数値はそこから引いている。

## 結果の要点

- 読み (R: JKYB-Parakeet から無作為に 100 文): 対象漢字の読みの正解は Irodori 98/100、Fish 92/100。両方とも参照音声は R10 (10.2 秒)
  - Irodori の不正解 2 件のうち 1 件 (r087「天地」をテンチ) は marginal (辞書上は許容) の読みで、もう 1 件 (r032「蛇の目傘」をヘビノメガサ) は Fish も同じ誤り
  - Fish の不正解 8 件: 保留→ホリュ、芝生→シタフ、数寄屋→カズヨヤ、趣→オモモキ、蛇の目→ヘビノメ、汚染→オウセン (2 回目の書き起こしでは正解)、石碑→セキ (碑が抜ける)、天地→テンチ (marginal)
- 数字・英字 (N: 10 文): Irodori 9/10、Fish 7/10
  - Irodori の誤り: 14時30分 → チュウヨウジ (2 回の書き起こしで同じ。要聴取)
  - Fish の誤り: API → エーティーアイ、1,000万円 → センバンエン (2 回目はセンマンエン)、10分 → ジュウブン
- 誤読しやすい漢字 (C: 08-27 の 5 文): Irodori は東雲をシノノメ、「人気のない道」をヒトケと読んだ。Fish は東雲をヒガシクモ、人気をニンキと読んだ
- 声の似方 (B: 同じ文 5 回、resemblyzer で生成に使った参照音声との類似度)
  - R10: Irodori 0.9079 ± 0.0045、Fish 0.9131 ± 0.0028
  - R26: Irodori 0.8956 ± 0.0140、Fish 0.9263 ± 0.0103
  - Irodori は推奨に近い R26 (25.7 秒) にしても似方は上がらなかった (後述の注意を参照)
  - 試行間 (5 本の 10 ペア): Irodori R10 0.9575 / R26 0.9705、Fish R10 0.9363 / R26 0.9505
  - 08-27 の IndexTTS-2.5 (同じ R10・同じ文) は ref 比 0.8477 だった
- seed: Irodori は `SamplingRequest(seed=42)` で 2 回生成した wav の MD5 が R10・R26 とも一致した。API に seed 引数がある (IndexTTS-2.5 は外から torch の乱数を固定していた)
- 速度 (RTX 4090、fp32、40 RF steps): RTF 0.109〜0.403 (mean 0.2399、129 本)。8〜11 秒の長い文で 0.11 前後、2〜5 秒の短い文で 0.15〜0.40。モデル読み込みは 13.6 秒 (キャッシュ済み)、初回はダウンロード 10.1 秒 + 読み込み 20.1 秒

## 条件

### モデルと呼び方

- Irodori-TTS v4.1-Small (`Aratako/Irodori-TTS-v4.1-Small`、コード commit `89f9d8fbd4d51ea019867ee1197725ede1df13c5`)。Python API の `InferenceRuntime` + `SamplingRequest` で呼んだ。設定はモデルカードのベンチと同じ既定 (fp32、40 RF steps、text CFG 3.0、speaker CFG 5.0)。参照音声は `ref_wav` に 1 本渡し、書き起こしは渡さない (Irodori は参照の書き起こしを使わない)
- seed 実験以外は seed を指定せず、ランタイムが選んだ seed を `used_seed` として記録した
- Irodori の出力には SilentCipher の透かしが自動で入る (今回は有効)
- テキストの正規化は記号の置換程度で、数字の読み下しは無い。N の文は数字・英字をそのまま入れた (かな指定の手段が無い)
- Fish Audio s2.1-pro。09-24 記事と同じ MessagePack で `/v1/tts` を直接叩く inline zero-shot clone。参照音声と書き起こしを毎回送る。temperature 0.7、top_p 0.7
- 実行環境: Irodori は RunPod Secure Cloud の RTX 4090 ($0.74/hr)。Fish はクラウド API

### 参照音声

- R10: 08-26 Fish 記事の `reference/ref.wav` (10.16 秒、24kHz mono、本人の声)
- R26: 09-24 Gemini 記事の `audio/ref-source.mp3` (25.69 秒) を 24kHz mono wav に変換したもの。元の wav は残っておらず、mp3 128kbps の劣化を含む
- R (100 文) と N (10 文) は両モデルとも R10 で生成した
- Irodori のモデルカードは参照音声を約 30 秒以上にするよう推奨している。R10 は 10 秒なので、R・N・C・B(R10) は Irodori に不利な条件になりうる
- R26 は 1 本の続けて話した録音。Irodori の README は長い参照について「同じ話者の短いクリップを複数つなぐ形で学習・評価しており、1 本の長い録音は評価していない」と書いている。R26 で似方が上がらなかったのはこの形の違いと mp3 の劣化の両方が考えられ、今回の計測では切り分けていない

### 実験と本数

| 実験 | 内容 | Irodori | Fish |
|---|---|---|---|
| B | 「本日は晴天なり。マイクのテスト中です。この音声は、ゼロショット音声合成のサンプルです。」を 5 回 | R10×5、R26×5 | R10×5、R26×5 |
| seed | B の文を seed=42 で 2 回、MD5 比較 | R10×2、R26×2 | なし (API に seed が無い) |
| C | 08-27 の c1〜c5 (読み指定なし) | R10×5 | R10×5 |
| R | JKYB-Parakeet 13,536 行から `random.Random(20261007).sample` で 100 行 | R10×100 | R10×100 |
| N | 数字・時刻・金額・割合・英字略語の自作 10 文 | R10×10 | R10×10 |

合計 Irodori 129 本、Fish 125 本。選んだ 100 行は `data/r100.jsonl`、N の 10 文は `data/n10.jsonl` (JKYB と同じ形式で、正解の読みと許容する読みを持つ)。R の 100 行の内訳は訓読み 49、音読み 46、付表の語 5。

### 読みの判定

1. 生成音声を 16kHz mono mp3 に変換し、gpt-4o-transcribe に「聞こえたとおりの音をすべてカタカナで。数字・英字も読まれた音のとおりに。助詞の は・へ は ワ・エ と書く。不自然に聞こえても直さない」というプロンプトで書き起こさせた (`transcribe.py`)
2. JKYB-Parakeet 公式の評価ツールキット (`Parakeet-Inc/Joyo-Kanji-Yomi-Benchmark-Parakeet-Edition`、commit `9606471bc15f052bdda7c18eba6396cd31020528`) の `score_row` で採点した (`score.py`)。読みの正規化 (長音・オ段+ウなどの吸収) と、対象漢字の範囲を前後の文脈でアライメントする処理は公式実装のまま
3. 「正解」は対象の読みが `readings.natural` のどれかと完全一致した場合。marginal (辞書上は許容だがその文脈では一般的でない読み) も含めた値も併記した
4. 不正解の行と疑いのある行 (計 15 本) は、同じ設定でもう一度書き起こした。表の値は 1 回目の書き起こしによる

公式の手順は ASR に kana-whisper を使うので、この数値はモデルカードの Kana-CER と互換ではない。N の行は常用漢字の区分に当てはまらないので、採点時だけ `reading_category` を `on_yomi` に置いている (集計に区分は使っていない)。

### 書き起こし誤りの疑いの扱い

次のどれかに当たる行を「書き起こし誤りの疑い」として一覧に残した (`report-numbers.md` の不正解の表)。

- 書き起こしにカタカナ以外の文字が混じる (Irodori r087)
- 対象の前後の文脈が正解の読みと 20% 以上ずれている (Irodori r087、Fish n03)
- 2 回目の書き起こしで判定が変わる (Fish r043 汚染、Fish n08 1,000万円)

疑いの行を除いても順位は変わらない (R: Irodori 98/99、Fish 92/99。N: Irodori 9/10、Fish 6/8)。

書き起こしの揺れの実例として、seed=42 の 2 本 (MD5 が一致した同じ音声) でも「ホンジツハ / ホンジツワ」「コノ / この」のように書き起こしが変わった。また Fish の B では「本日は」が「コンニチワ」「コンジツ」と書き起こされた試行が 10 本中 6 本あった。Irodori でも 2 本ある。生成側が実際にそう読んだのか書き起こしの誤りかは、耳で確かめる必要がある (B は判定の対象外)。

## 聴き比べ用のファイル

`~/Downloads/irodori-eval/` に、同じ文の Irodori と Fish のペアを置いた (B の run1、C、R、N の計 117 文 × 2 本、参照音声 2 本)。`README.md` に文の一覧があり、どちらかが不正解と判定された文に ★ を付けている。イントネーションは数値で測っていない。

耳で確かめたい行:

- Irodori n01「14時30分」(チュウヨウジと書き起こされた)
- Irodori c4「一日中」(イチネンチジュウと書き起こされた)、c2「早急」(ソッキュウと書き起こされた)
- Fish r059「石碑」(碑が抜けて書き起こされた)、r009「芝生」(シタフ)
- 両モデルの B で「本日は」がコンニチハと書き起こされた試行

## 費用

| 項目 | 量 | 費用 |
|---|---|---|
| RunPod RTX 4090 Secure | 09:45:59 作成〜09:52:06 削除、約 6.1 分 | 約 $0.075 |
| gpt-4o-transcribe | 音声 1,037 秒 (17.3 分、2 回目と参照を含む) × $0.006/分 | 約 $0.10 |
| Fish s2.1-pro | 125 本、2,568 文字 (UTF-8 で 7,636 バイト) | 単価は未確認 |

Pod は GraphQL の `podFindAndDeployOnDemand` に `supportPublicIp: true` と `allowedCudaVersions: ["12.8","12.9","13.0"]` を付けて作り、作成から約 30 秒で SSH がつながった。`podTerminate` で削除し、GraphQL の `myself.pods` と `runpodctl pod list --all` (全状態) が空であることを確認した。

## 再現の手順

1. `python select_rows.py <common_kanji_source.jsonl>` で `data/r100.jsonl` を作る
2. `FISH_API_KEY=... python gen_fish.py` で Fish の 125 本
3. Pod で `eval_irodori.py` の docstring どおりにセットアップし、Fish の出力も `/eval/out/fish/` に置いて実行 (Irodori 129 本と、両モデルの resemblyzer 類似度)
4. `OPENAI_API_KEY=... python transcribe.py`、不正解行は `ONLY=... OUT_NAME=transcripts-pass2.jsonl` でもう一度
5. `PYTHONPATH=<jkyb-toolkit>/src python score.py`、`python make_report.py`

Pod 上のセットアップで、resemblyzer が依存する webrtcvad のソースビルドが Python.h が無くて失敗した。ビルド済みの `webrtcvad-wheels` を入れ、resemblyzer は `--no-deps` で入れて回避した。

## 指標の限界

- 読みの判定は gpt-4o-transcribe のカタカナ書き起こしに依存する。同じ音声でも書き起こしが変わる例が出ている
- 各文 1 回の生成で、生成側の揺れ (同じ文で読みが変わるか) は測っていない
- R は 100 文なので、98 と 92 の差は 1 文あたり 1 ポイントの粒度で見る必要がある
- resemblyzer の類似度は単一の指標で、聴感の似方とは別。R10 と R26 は別の録音なので、参照をまたいだ数値の比較はできない
- 08-27 (IndexTTS-2.5) の B は今回と同じ R10・同じ文・同じ resemblyzer で測っており、ref 比 0.8477 ± 0.0134、試行間 0.9570 ± 0.0072 だった。今回の Irodori (R10) は ref 比 0.9079 ± 0.0045、試行間 0.9575 ± 0.0074。ただし生成は別の日・別の Pod で、IndexTTS-2.5 は bf16 だった。08-26 の Fish の数値は別の文での値
