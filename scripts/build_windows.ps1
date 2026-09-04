[CmdletBinding()]
param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$WindowsVendor = Join-Path $ProjectRoot "vendor\windows-x64"
$ProviderMain = Join-Path $ProjectRoot "vendor\bgutil-ytdlp-pot-provider\server\build\main.js"
$AppPath = Join-Path $ProjectRoot "dist\YT Downloader by 學人新創\YT Downloader by 學人新創.exe"

if (-not $IsWindows -or [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture -ne "X64") {
    throw "Windows x64 application must be built on Windows x64."
}

if (
    -not (Test-Path (Join-Path $WindowsVendor "ffmpeg.exe")) -or
    -not (Test-Path (Join-Path $WindowsVendor "ffprobe.exe")) -or
    -not (Test-Path (Join-Path $WindowsVendor "node.exe")) -or
    -not (Test-Path $ProviderMain)
) {
    & (Join-Path $ScriptDir "fetch_windows_runtime.ps1")
}

Push-Location $ProjectRoot
try {
    & $Python (Join-Path $ScriptDir "create_windows_icon.py")
    if ($LASTEXITCODE -ne 0) { throw "Windows icon generation failed." }

    & $Python -m PyInstaller --noconfirm --clean "packaging\windows-x64.spec"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller Windows build failed." }
}
finally {
    Pop-Location
}

if (-not (Test-Path $AppPath)) {
    throw "Packaged Windows executable was not created: $AppPath"
}

Write-Host "Created Windows x64 application: $AppPath"
