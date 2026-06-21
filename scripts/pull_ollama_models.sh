#!/usr/bin/env bash
set -euo pipefail

models=(
  "qwen3:14b"
  "bge-m3"
  "deepseek-r1:14b"
  "llama3.1:8b"
)

for model in "${models[@]}"; do
  echo "Pulling ${model}..."
  ollama pull "${model}"
done

cat <<'EOF'
Optional heavier models for powerful machines:
# ollama pull qwen3:30b
# ollama pull llama3.3:70b
EOF
