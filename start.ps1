# 一鍵啟動：載入建置環境 + 啟動常駐 GPU 推論服務
# 用法：在 PowerShell 執行 .\start.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "=== 載入 ARM64 編譯環境變數 ===" -ForegroundColor Cyan
$vcvars = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsarm64.bat"
if (Test-Path $vcvars) {
    cmd /c "`"$vcvars`" && set" | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') { Set-Item -Path "env:$($matches[1])" -Value $matches[2] }
    }
}
$env:PATH = "C:\Program Files\LLVM\bin;" + $env:PATH

Write-Host "=== 檢查 llama-server 是否已在跑 ===" -ForegroundColor Cyan
$healthy = $false
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8811/health" -TimeoutSec 2 -UseBasicParsing
    if ($resp.StatusCode -eq 200) { $healthy = $true }
} catch {}

if ($healthy) {
    Write-Host "llama-server 已經在跑，略過啟動" -ForegroundColor Green
} else {
    Write-Host "=== 啟動 llama-server（GPU，Qwen2.5-7B）===" -ForegroundColor Cyan
    $llamaDir = Join-Path $root "progress\p0\build\llama.cpp"
    $model = Join-Path $llamaDir "models-test\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"
    $exe = Join-Path $llamaDir "build\bin\llama-server.exe"
    if (-not (Test-Path $exe)) { throw "找不到 llama-server.exe，P0 build 可能沒做完：$exe" }
    if (-not (Test-Path $model)) { throw "找不到模型檔：$model" }

    $startArgs = @{
        FilePath = $exe
        ArgumentList = @("-m", $model, "-ngl", "99", "--port", "8811")
        WorkingDirectory = $llamaDir
        RedirectStandardOutput = (Join-Path $root "progress\p2_tool_calling\server_stdout.log")
        RedirectStandardError = (Join-Path $root "progress\p2_tool_calling\server_stderr.log")
        WindowStyle = "Hidden"
    }
    Start-Process @startArgs

    Write-Host "等待模型載入 GPU..." -ForegroundColor Yellow
    $ready = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 3
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8811/health" -TimeoutSec 2 -UseBasicParsing
            if ($resp.StatusCode -eq 200) { $ready = $true; break }
        } catch {}
    }
    if ($ready) { Write-Host "llama-server 已就緒" -ForegroundColor Green } else { Write-Host "等待逾時，請檢查 progress\p2_tool_calling\server_stderr.log" -ForegroundColor Red }
}

Write-Host "=== 啟動本機主控台網頁伺服器 (port 8899) ===" -ForegroundColor Cyan
$consoleHealthy = $false
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8899/" -TimeoutSec 2 -UseBasicParsing
    if ($resp.StatusCode -eq 200) { $consoleHealthy = $true }
} catch {}

if ($consoleHealthy) {
    Write-Host "主控台已經在跑，略過啟動" -ForegroundColor Green
} else {
    $venvPython = Join-Path $root "progress\p0\venv-arm64\Scripts\python.exe"
    $consoleDir = Join-Path $root "console"
    $consoleArgs = @{
        FilePath = $venvPython
        ArgumentList = @("serve.py", "8899")
        WorkingDirectory = $consoleDir
        WindowStyle = "Hidden"
    }
    Start-Process @consoleArgs
    Write-Host "主控台已啟動：http://127.0.0.1:8899/" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== 全部就緒 ===" -ForegroundColor Green
Write-Host "主控台：http://127.0.0.1:8899/"
Write-Host "推論服務健康檢查：http://127.0.0.1:8811/health"
Start-Process "http://127.0.0.1:8899/"
