param(
    [string]$Compiler = (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$BuildDirectory = Join-Path $PSScriptRoot 'build'
$Keys = @{ 'installer.launch' = 'LaunchApp'; 'installer.remove_user_data' = 'RemoveUserData' }

function Write-Messages([string]$Language) {
    $catalog = Get-Content (Join-Path $Root "locales\$Language.json") -Raw -Encoding utf8 | ConvertFrom-Json
    $lines = @('[CustomMessages]')
    foreach ($key in $Keys.Keys) {
        $text = $catalog.$key
        if (-not $text) { throw "Missing $key in locales\$Language.json" }
        $lines += "$($Keys[$key])=$($text -replace '\r?\n', '%n')"
    }
    [System.IO.File]::WriteAllLines((Join-Path $BuildDirectory "$Language.isl"), $lines, (New-Object System.Text.UTF8Encoding $true))
}

New-Item -ItemType Directory -Force -Path $BuildDirectory | Out-Null
Write-Messages 'en'
Write-Messages 'pt-BR'
& $Compiler (Join-Path $PSScriptRoot 'wcam.iss')
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }
