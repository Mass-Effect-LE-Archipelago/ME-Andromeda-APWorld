# RE tooling environment for this project.
#
# Ghidra 12.1.4 (Java 21) and the REA CLI, with every writable location kept inside
# the workspace so the sandbox does not block them.
#
#   Set-ExecutionPolicy -Scope Process Bypass -Force
#   . .\rea-env.ps1
#   rea doctor --json
#   ghidra-headless <projdir> <projname> -import <binary>
#
# Notes:
#   * Ghidra needs a full JDK. The machine has one at Program Files\Java\jdk-21.0.12.1;
#     it is not on PATH and Ghidra does not find it without JAVA_HOME.
#   * Ghidra writes settings to %APPDATA%\ghidra, which the sandbox denies, so APPDATA
#     and LOCALAPPDATA are redirected into tools\ghidra-user.
#   * npm's default cache is outside the workspace and blocked; npm_config_cache fixes it.

$root = Split-Path -Parent $PSScriptRoot

$env:GHIDRA_INSTALL_DIR = Join-Path $root "tools\ghidra\ghidra_12.1.4_PUBLIC"
$env:JAVA_HOME = "C:\Program Files\Java\jdk-21.0.12.1"
$env:APPDATA = Join-Path $root "tools\ghidra-user\AppData\Roaming"
$env:LOCALAPPDATA = Join-Path $root "tools\ghidra-user\AppData\Local"
$env:MAXMEM = "8G"
$env:npm_config_cache = Join-Path $root "tools\npm-cache"
$env:npm_config_update_notifier = "false"
$env:REA_GHIDRA_SCRIPTS = Join-Path $root "tools\ghidra-scripts"

foreach ($p in @($env:APPDATA, $env:LOCALAPPDATA, (Join-Path $root "tools\ghidra-projects"))) {
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
}

function rea {
    param([Parameter(ValueFromRemainingArguments = $true)] $Args)
    & npx -y rea-agents@6.5.0 @Args
}

function ghidra-headless {
    param([Parameter(ValueFromRemainingArguments = $true)] $Args)
    & (Join-Path $env:GHIDRA_INSTALL_DIR "support\analyzeHeadless.bat") @Args
}

Write-Host "GHIDRA_INSTALL_DIR = $env:GHIDRA_INSTALL_DIR"
Write-Host "JAVA_HOME          = $env:JAVA_HOME"
Write-Host "APPDATA (ghidra)   = $env:APPDATA"
Write-Host "npm cache          = $env:npm_config_cache"
