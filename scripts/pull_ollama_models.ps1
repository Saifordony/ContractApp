$ErrorActionPreference = "Stop"

$models = @(
  "llama3.1:8b"
)

foreach ($model in $models) {
  Write-Host "Pulling $model..."
  ollama pull $model
}

Write-Host "Stable MVP uses one optional wording model: llama3.1:8b."
Write-Host "Future heavier experiments (disabled in active runtime):"
Write-Host "# ollama pull qwen3:14b"
Write-Host "# ollama pull qwen3:30b"
