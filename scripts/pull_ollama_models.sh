#!/usr/bin/env bash
set -euo pipefail

models=(
  "llama3.1:8b"
)

for model in "${models[@]}"; do
  echo "Pulling ${model}..."
  ollama pull "${model}"
done

cat <<'MSG'
Stable MVP uses one optional wording model: llama3.1:8b.
Future heavier experiments (disabled in active runtime):
# ollama pull qwen3:14b
# ollama pull qwen3:30b
MSG
