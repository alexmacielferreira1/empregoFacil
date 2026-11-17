# Gera dist\empregofacil-shard.zip pronto para subir na ShardCloud (Windows PowerShell).
# Uso: na pasta do projeto, rode:  powershell -ExecutionPolicy Bypass -File .\build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ">> Compilando o frontend para backend\static"
Push-Location frontend
npm install --no-audit --no-fund
npm run build
Pop-Location

Write-Host ">> Montando o pacote"
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
New-Item -ItemType Directory dist | Out-Null
$tmp = Join-Path $env:TEMP "empregofacil-shard"
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
New-Item -ItemType Directory $tmp | Out-Null

$ignorar = @("__pycache__", ".pytest_cache", "tests", "venv", ".venv")
Get-ChildItem backend -Force | Where-Object {
  $ignorar -notcontains $_.Name -and $_.Name -ne ".env" -and $_.Name -ne "Dockerfile" -and $_.Extension -ne ".db"
} | ForEach-Object { Copy-Item $_.FullName -Destination $tmp -Recurse -Force }
Get-ChildItem $tmp -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

Compress-Archive -Path (Join-Path $tmp "*") -DestinationPath "dist\empregofacil-shard.zip" -Force
Remove-Item $tmp -Recurse -Force
Write-Host ">> Pronto: dist\empregofacil-shard.zip"
