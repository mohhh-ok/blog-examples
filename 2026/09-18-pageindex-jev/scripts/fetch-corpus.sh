#!/bin/sh
# 各 docs サイトが公開している llms-full.txt を corpus/raw/<site>.md に落とす（試作で使った 4 サイト）。
set -e
cd "$(dirname "$0")/.."
mkdir -p corpus/raw
for u in zod.dev hono.dev elysiajs.com vite.dev; do
  curl -sL --max-time 120 "https://$u/llms-full.txt" -o "corpus/raw/$u.md"
  echo "$u: $(wc -c < "corpus/raw/$u.md") bytes"
done
