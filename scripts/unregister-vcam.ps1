#Requires -RunAsAdministrator
param(
    [switch]$RemoveData
)

$ErrorActionPreference = 'Stop'
$InstallDirectory = Join-Path $env:ProgramFiles 'WCam'
$DataDirectory = Join-Path $env:ProgramData 'WCam'
$InstalledDll = Join-Path $InstallDirectory 'Wcam.VirtualCamera.dll'

function Unregister-Dll {
    $process = Start-Process -FilePath regsvr32.exe -ArgumentList '/u', '/s', "`"$InstalledDll`"" -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "regsvr32 /u failed with exit code $($process.ExitCode)" }
}

function Remove-InstallDirectory {
    try {
        Remove-Item -Path $InstallDirectory -Recurse -Force
    }
    catch [System.IO.IOException], [System.UnauthorizedAccessException] {
        Write-Host 'The DLL is loaded by the Windows camera service; restarting FrameServer.'
        Restart-Service -Name FrameServer -Force
        Remove-Item -Path $InstallDirectory -Recurse -Force
    }
}

if (Test-Path $InstalledDll) {
    Unregister-Dll
    Remove-InstallDirectory
    Write-Host "Unregistered and removed $InstallDirectory"
}
else {
    Write-Host "Nothing registered at $InstalledDll"
}
if ($RemoveData -and (Test-Path $DataDirectory)) {
    Remove-Item -Path $DataDirectory -Recurse -Force
    Write-Host "Removed $DataDirectory"
}
