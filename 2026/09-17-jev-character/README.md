# jev-character

TypeSafe の System One モデル Jev に、自由入力の性格文と今の状況と来客を渡し、反応（近寄る／様子見／隠れる）の確率分布を受け取る。サイコロはコード側で振る。性格を数値に変換する段は置かず、文章のまま毎回渡す。

## 実行

```sh
bun install
TYPESAFE_API_KEY=... bun run src/run.ts
```

来客 1 回につき API 呼び出し 1 回。キャラ 3 体 × 状況 2 つ × 来客 5 種 = 30 回。
