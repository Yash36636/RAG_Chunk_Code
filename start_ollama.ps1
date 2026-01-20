# Start RAG Server with Ollama (LOCAL - no API needed)
# Requires: Ollama running locally

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RAG SERVER - OLLAMA MODE (LOCAL)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Ollama is running
Write-Host "Checking Ollama status..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "[OK] Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Ollama is not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Start Ollama first:" -ForegroundColor Yellow
    Write-Host "  1. Open a new terminal" -ForegroundColor White
    Write-Host "  2. Run: ollama serve" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Set provider
$env:LLM_PROVIDER = "ollama"
$env:OLLAMA_MODEL = "qwen2.5:3b-instruct"

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Provider: Ollama (local)" -ForegroundColor White
Write-Host "  Model: qwen2.5:3b-instruct" -ForegroundColor White
Write-Host "  Expected latency: 2-5s" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start server
python server.py
