# Start RAG Server with Groq (FAST - ~1s responses)
# Requires: GROQ_API_KEY environment variable

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RAG SERVER - GROQ MODE (FAST)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for API key
if (-not $env:GROQ_API_KEY) {
    Write-Host "[ERROR] GROQ_API_KEY not set!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Set it with:" -ForegroundColor Yellow
    Write-Host '  $env:GROQ_API_KEY = "your_api_key_here"' -ForegroundColor White
    Write-Host ""
    Write-Host "Get a free key at: https://console.groq.com" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "[OK] GROQ_API_KEY found" -ForegroundColor Green

# Set provider
$env:LLM_PROVIDER = "groq"

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Provider: Groq (llama-3.1-8b-instant)" -ForegroundColor White
Write-Host "  Expected latency: 0.8-1.5s" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start server
python server.py
