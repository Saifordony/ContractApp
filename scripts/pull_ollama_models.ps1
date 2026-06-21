$ErrorActionPreference = "Stop"

$models = @(
  "qwen3:14b",
  "bge-m3",
  "deepseek-r1:14b",
  "llama3.1:8b"
)

foreach ($model in $models) {
  Write-Host "Pulling $model..."
  ollama pull $model
}

Write-Host "Optional heavier models for powerful machines:"
Write-Host "# ollama pull qwen3:30b"
Write-Host "# ollama pull llama3.3:70b"
