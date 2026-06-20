$ErrorActionPreference = "Stop"

$script = Join-Path $PSScriptRoot "zap_scraping.py"
$output = Join-Path $PSScriptRoot "outputs\zap_venda_fortaleza.csv"
$statusLog = Join-Path $PSScriptRoot "outputs\zap_watchdog.status.log"
$runDir = Join-Path $PSScriptRoot "outputs\zap_runs"

New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$timeoutMinutes = 1.5
$pollSeconds = 10

while ($true) {
    $lineCount = 0
    if (Test-Path $output) {
        $lineCount = (Get-Content $output).Count
    }

    if ($lineCount -ge 10001) {
        Add-Content -Path $statusLog -Value "[watchdog] alvo atingido com $lineCount linhas. Encerrando."
        break
    }

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $stdoutLog = Join-Path $runDir "zap_scraper_$stamp.out.log"
    $stderrLog = Join-Path $runDir "zap_scraper_$stamp.err.log"

    Add-Content -Path $statusLog -Value "[watchdog] iniciando scraper com $lineCount linhas atuais. Logs: $stdoutLog / $stderrLog"

    $proc = Start-Process -WindowStyle Hidden -FilePath python -ArgumentList @(
        $script,
        "--output", $output,
        "--max-listings-per-type", "10000",
        "--headless"
    ) -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru

    $deadline = (Get-Date).AddMinutes($timeoutMinutes)
    while (-not $proc.HasExited -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds $pollSeconds
    }

    if (-not $proc.HasExited) {
        try {
            Stop-Process -Id $proc.Id -Force
            Add-Content -Path $statusLog -Value "[watchdog] timeout atingido. Processo $($proc.Id) finalizado e sera reiniciado."
        }
        catch {
            Add-Content -Path $statusLog -Value "[watchdog] falha ao encerrar processo $($proc.Id): $($_.Exception.Message)"
        }
    }
    else {
        Add-Content -Path $statusLog -Value "[watchdog] scraper terminou com codigo $($proc.ExitCode). Reiniciando."
    }

    Start-Sleep -Seconds 5
}
