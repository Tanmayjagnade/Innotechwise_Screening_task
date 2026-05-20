# Demo script for Windows PowerShell: exercises all three endpoints in sequence.
$BASE = "http://localhost:8000"
$Headers = @{ "Content-Type" = "application/json" }

function Show-Json($obj) { $obj | ConvertTo-Json -Depth 10 }

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  GreenPack EPR Service - Demo" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "`n--- 1. POST /submit ---" -ForegroundColor Yellow
$submitBody = @{
    producer_id = "GREENPACK-001"
    month = "2026-04"
    declared_quantities_kg = @{
        rigid_plastic = 12000
        flexible_plastic = 8500
        multilayer_plastic = 3200
    }
} | ConvertTo-Json -Depth 3
$r1 = Invoke-RestMethod -Uri "$BASE/submit" -Method POST -Body $submitBody -Headers $Headers
Show-Json $r1

Write-Host "`n--- 2. GET /summary/GREENPACK-001/2026-04 ---" -ForegroundColor Yellow
$r2 = Invoke-RestMethod -Uri "$BASE/summary/GREENPACK-001/2026-04" -Method GET
Show-Json $r2

Write-Host "`n--- 3a. POST /ask (answerable question) ---" -ForegroundColor Yellow
$askBody1 = @{ question = "What are the EPR registration requirements for plastic producers?" } | ConvertTo-Json
$r3a = Invoke-RestMethod -Uri "$BASE/ask" -Method POST -Body $askBody1 -Headers $Headers
Show-Json $r3a

Write-Host "`n--- 3b. POST /ask (out-of-scope — expect I do not know) ---" -ForegroundColor Yellow
$askBody2 = @{ question = "What is the capital of France?" } | ConvertTo-Json
$r3b = Invoke-RestMethod -Uri "$BASE/ask" -Method POST -Body $askBody2 -Headers $Headers
Show-Json $r3b

Write-Host "`n--- 4. POST /submit (validation error — negative quantity) ---" -ForegroundColor Yellow
try {
    $badBody = @{
        producer_id = "GREENPACK-001"
        month = "2026-05"
        declared_quantities_kg = @{ rigid_plastic = -500 }
    } | ConvertTo-Json -Depth 3
    Invoke-RestMethod -Uri "$BASE/submit" -Method POST -Body $badBody -Headers $Headers
} catch {
    $_.Exception.Response | Select-Object StatusCode | Format-List
    Write-Host $_.ErrorDetails.Message
}

Write-Host "`nDemo complete." -ForegroundColor Green
