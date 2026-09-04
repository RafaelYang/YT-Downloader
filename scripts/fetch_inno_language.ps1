[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$Destination = Join-Path $ProjectRoot "build\windows\ChineseTraditional.isl"
$LanguageUrl = "https://raw.githubusercontent.com/jrsoftware/issrc/6ef32198ef1f7b7b375cd4b6b90896c2a58eb4c2/Files/Languages/ChineseTraditional.isl"
$LanguageSha256 = "031684fc769259291fd563338b5abe20b7753c88ab5a2976b83a80788deb8455"

New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
Invoke-WebRequest -Uri $LanguageUrl -OutFile $Destination -UseBasicParsing

$Actual = (Get-FileHash -Path $Destination -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Actual -ne $LanguageSha256) {
    throw "SHA-256 verification failed for the Inno Setup Traditional Chinese language file: $Actual"
}

Write-Host "Prepared verified Inno Setup Traditional Chinese messages: $Destination"
