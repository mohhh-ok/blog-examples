# Claude Code 用 dev container (macOS + devcontainer CLI)

Claude Code を egress firewall 付きの dev container に隔離して
`--dangerously-skip-permissions` を回すための構成。公式リファレンス
(https://github.com/anthropics/claude-code/tree/main/.devcontainer) を
ベースに、そのままでは動かない箇所へのパッチと pnpm / macOS 向けの
volume 構成を足したもの。詳細はブログ記事を参照。

## 使い方

1. 3ファイルをプロジェクトの `.devcontainer/` に置く
2. `myapp` を自分のプロジェクトのディレクトリ名に置換する
   (volume 名 3 箇所と `npm_config_store_dir` のパス。
   `/workspaces/<ディレクトリ名>` に合わせる)
3. `package.json` に `"packageManager": "pnpm@<ホストと同じ版>"` を追加する
4. 起動:

```sh
pnpm dlx @devcontainers/cli up --workspace-folder .
pnpm dlx @devcontainers/cli exec --workspace-folder . claude
```

前提: Docker (Docker Desktop / colima)、ホストに pnpm。VS Code は不要。
