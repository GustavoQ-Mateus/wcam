#Requires -RunAsAdministrator
param(
    [string]$DllPath,
    [string]$User = (Get-CimInstance Win32_ComputerSystem).UserName
)

$ErrorActionPreference = 'Stop'
$DllName = 'Wcam.VirtualCamera.dll'
$LocalServiceSid = '*S-1-5-19'
$MinimumBuild = 22000
$InstallDirectory = Join-Path $env:ProgramFiles 'WCam'
$DataDirectory = Join-Path $env:ProgramData 'WCam'
$InstalledDll = Join-Path $InstallDirectory $DllName

function Find-PublishedDll {
    $searchRoot = Join-Path $PSScriptRoot '..\vcam\src\Wcam.VirtualCamera\bin'
    $published = Get-ChildItem -Path $searchRoot -Recurse -Filter $DllName -ErrorAction SilentlyContinue |
        Where-Object { $_.Directory.Name -eq 'publish' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $published) {
        throw "No published $DllName found. Run 'dotnet publish -r win-x64 -c Release' in vcam\src\Wcam.VirtualCamera or pass -DllPath."
    }
    return $published.FullName
}

function Copy-Dll([string]$source) {
    New-Item -ItemType Directory -Force -Path $InstallDirectory | Out-Null
    try {
        Copy-Item -Path $source -Destination $InstalledDll -Force
    }
    catch [System.IO.IOException] {
        Write-Host 'The previous DLL is loaded by the Windows camera service; restarting FrameServer.'
        Restart-Service -Name FrameServer -Force
        Copy-Item -Path $source -Destination $InstalledDll -Force
    }
}

function Grant-DataAccess {
    New-Item -ItemType Directory -Force -Path (Join-Path $DataDirectory 'logs') | Out-Null
    & icacls.exe $DataDirectory /grant "${LocalServiceSid}:(OI)(CI)M" /grant "${User}:(OI)(CI)M" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "icacls failed on $DataDirectory" }
    & icacls.exe $InstallDirectory /grant "${LocalServiceSid}:(OI)(CI)RX" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "icacls failed on $InstallDirectory" }
}

function Register-Dll {
    $process = Start-Process -FilePath regsvr32.exe -ArgumentList '/s', "`"$InstalledDll`"" -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "regsvr32 failed with exit code $($process.ExitCode)" }
}

$build = [System.Environment]::OSVersion.Version.Build
if ($build -lt $MinimumBuild) { throw "Windows build $build is older than $MinimumBuild." }
if (-not $DllPath) { $DllPath = Find-PublishedDll }
Write-Host "Source: $DllPath"
Copy-Dll (Resolve-Path $DllPath).Path
Grant-DataAccess
Register-Dll
Write-Host "Registered $InstalledDll"
Write-Host "Data and logs: $DataDirectory (access for LOCAL SERVICE and $User)"
