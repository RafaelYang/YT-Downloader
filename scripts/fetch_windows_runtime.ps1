[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$WindowsVendor = Join-Path $ProjectRoot "vendor\windows-x64"
$ProviderDestination = Join-Path $ProjectRoot "vendor\bgutil-ytdlp-pot-provider"
$TemporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("yt-downloader-windows-" + [guid]::NewGuid().ToString("N"))

$FfmpegArchiveName = "ffmpeg-n8.1.2-50-g1a748fe2cd-win64-gpl-8.1.zip"
$FfmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-09-03-13-17/$FfmpegArchiveName"
$FfmpegSha256 = "b0b50337bdd4e7797caa874fbd000435864361b71ceb6aa26525d8df0c9c86a6"

$NodeVersion = "24.20.0"
$NodeArchiveName = "node-v$NodeVersion-win-x64.zip"
$NodeUrl = "https://nodejs.org/dist/v$NodeVersion/$NodeArchiveName"
$NodeSha256 = "6cac9ffbca8f6a47091e4b5c772e0606049c3871cb67d900c0cedde630e545ba"

$ProviderVersion = "1.3.2"
$ProviderArchiveName = "bgutil-ytdlp-pot-provider-$ProviderVersion.tar.gz"
$ProviderUrl = "https://codeload.github.com/Brainicism/bgutil-ytdlp-pot-provider/tar.gz/refs/tags/$ProviderVersion"
$ProviderSha256 = "3545ac7ffc0869498755cb3b4760a72fa2f176689d0890a6f5b898d163012ba2"

function Get-VerifiedFile {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$ExpectedSha256,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
    $Actual = (Get-FileHash -Path $Destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Actual -ne $ExpectedSha256) {
        throw "SHA-256 verification failed for $(Split-Path -Leaf $Destination): $Actual"
    }
}

if (-not $IsWindows -or [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture -ne "X64") {
    throw "Windows x64 runtime must be prepared on Windows x64."
}

New-Item -ItemType Directory -Path $TemporaryRoot -Force | Out-Null
New-Item -ItemType Directory -Path $WindowsVendor -Force | Out-Null

try {
    $FfmpegArchive = Join-Path $TemporaryRoot $FfmpegArchiveName
    $FfmpegExtracted = Join-Path $TemporaryRoot "ffmpeg"
    Get-VerifiedFile $FfmpegUrl $FfmpegSha256 $FfmpegArchive
    Expand-Archive -Path $FfmpegArchive -DestinationPath $FfmpegExtracted

    $Ffmpeg = Get-ChildItem -Path $FfmpegExtracted -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
    $Ffprobe = Get-ChildItem -Path $FfmpegExtracted -Recurse -Filter "ffprobe.exe" | Select-Object -First 1
    $FfmpegLicense = Get-ChildItem -Path $FfmpegExtracted -Recurse -Filter "LICENSE.txt" | Select-Object -First 1
    if (-not $Ffmpeg -or -not $Ffprobe -or -not $FfmpegLicense) {
        throw "FFmpeg archive is missing ffmpeg.exe, ffprobe.exe, or LICENSE.txt."
    }
    Copy-Item $Ffmpeg.FullName (Join-Path $WindowsVendor "ffmpeg.exe") -Force
    Copy-Item $Ffprobe.FullName (Join-Path $WindowsVendor "ffprobe.exe") -Force
    Copy-Item $FfmpegLicense.FullName (Join-Path $WindowsVendor "ffmpeg-LICENSE.txt") -Force

    $NodeArchive = Join-Path $TemporaryRoot $NodeArchiveName
    Get-VerifiedFile $NodeUrl $NodeSha256 $NodeArchive
    Expand-Archive -Path $NodeArchive -DestinationPath $TemporaryRoot
    $NodeRoot = Join-Path $TemporaryRoot "node-v$NodeVersion-win-x64"
    Copy-Item (Join-Path $NodeRoot "node.exe") (Join-Path $WindowsVendor "node.exe") -Force
    Copy-Item (Join-Path $NodeRoot "LICENSE") (Join-Path $WindowsVendor "node-LICENSE") -Force

    $ProviderArchive = Join-Path $TemporaryRoot $ProviderArchiveName
    $ProviderTemporary = Join-Path $TemporaryRoot "provider"
    Get-VerifiedFile $ProviderUrl $ProviderSha256 $ProviderArchive
    New-Item -ItemType Directory -Path $ProviderTemporary -Force | Out-Null
    & tar.exe -xzf $ProviderArchive -C $ProviderTemporary --strip-components=1
    if ($LASTEXITCODE -ne 0) {
        throw "Could not extract the PO-token provider source."
    }

    Push-Location $ProviderTemporary
    try {
        & git apply --whitespace=nowarn (Join-Path $ScriptDir "patches\bgutil-localhost.patch")
        if ($LASTEXITCODE -ne 0) {
            throw "Could not apply the loopback-only provider patch."
        }
    }
    finally {
        Pop-Location
    }

    $OriginalPath = $env:Path
    $env:Path = "$NodeRoot;$OriginalPath"
    Push-Location (Join-Path $ProviderTemporary "server")
    try {
        & npm.cmd ci --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw "npm ci failed." }
        & npx.cmd tsc
        if ($LASTEXITCODE -ne 0) { throw "Provider TypeScript build failed." }
        & npm.cmd prune --omit=dev --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw "npm prune failed." }
    }
    finally {
        Pop-Location
        $env:Path = $OriginalPath
    }

    $ProviderMain = Join-Path $ProviderTemporary "server\build\main.js"
    if (-not (Select-String -Path $ProviderMain -SimpleMatch 'host: "127.0.0.1"' -Quiet)) {
        throw "PO-token provider was not restricted to 127.0.0.1."
    }
    $CanvasModule = Get-ChildItem -Path (Join-Path $ProviderTemporary "server\node_modules\canvas") -Recurse -Filter "*.node" | Select-Object -First 1
    if (-not $CanvasModule) {
        throw "The Windows Canvas native module was not installed."
    }

    if (Test-Path $ProviderDestination) {
        Remove-Item -Path $ProviderDestination -Recurse -Force
    }
    Copy-Item -Path $ProviderTemporary -Destination $ProviderDestination -Recurse

    & (Join-Path $WindowsVendor "ffmpeg.exe") -version | Select-Object -First 1
    & (Join-Path $WindowsVendor "ffprobe.exe") -version | Select-Object -First 1
    & (Join-Path $WindowsVendor "node.exe") --version
    Write-Host "Prepared pinned Windows x64 media and quality runtimes."
}
finally {
    if (Test-Path $TemporaryRoot) {
        Remove-Item -Path $TemporaryRoot -Recurse -Force
    }
}
