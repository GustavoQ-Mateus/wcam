#define AppName "WCam"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef AppSource
  #define AppSource "..\app\src\Wcam.App\bin\Release\net10.0-windows10.0.22000.0\win-x64\publish"
#endif
#ifndef AgentSource
  #define AgentSource "..\agent\dist\wcam"
#endif
#ifndef CameraSource
  #define CameraSource "..\vcam\src\Wcam.VirtualCamera\bin\Release\net10.0-windows10.0.22000.0\win-x64\publish\Wcam.VirtualCamera.dll"
#endif
#define FirewallRule "WCam phone page"
#define PhonePort "8443"
#define LocalService "*S-1-5-19"

[Setup]
AppId={{7B1C5E1A-4F0E-4C55-9A57-5E2C3D8B9A10}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=WCam
DefaultDirName={autopf}\WCam
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=admin
UsedUserAreasWarning=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
AppMutex=WCam.App
CloseApplications=yes
OutputDir=Output
OutputBaseFilename=WCam-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\WCam.exe

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl,build\en.isl"
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl,build\pt-BR.isl"

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Excludes: "*.pdb"; Flags: ignoreversion recursesubdirs
Source: "{#AgentSource}\*"; DestDir: "{app}\agent"; Flags: ignoreversion recursesubdirs
Source: "{#CameraSource}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\locales\*.json"; DestDir: "{app}\locales"; Flags: ignoreversion

[Dirs]
Name: "{commonappdata}\WCam\logs"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\WCam.exe"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "WCam"; Flags: dontcreatekey uninsdeletevalue

[Run]
Filename: "{sys}\icacls.exe"; Parameters: """{app}"" /grant {#LocalService}:(OI)(CI)RX"; Flags: runhidden waituntilterminated
Filename: "{sys}\icacls.exe"; Parameters: """{commonappdata}\WCam\logs"" /grant {#LocalService}:(OI)(CI)M /grant ""{username}"":(OI)(CI)M"; Flags: runhidden waituntilterminated
Filename: "{sys}\regsvr32.exe"; Parameters: "/s ""{app}\Wcam.VirtualCamera.dll"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#FirewallRule}"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#FirewallRule}"" dir=in action=allow protocol=TCP localport={#PhonePort} profile=private remoteip=localsubnet program=""{app}\agent\wcam.exe"""; Flags: runhidden waituntilterminated
Filename: "{app}\WCam.exe"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
Filename: "{sys}\regsvr32.exe"; Parameters: "/u /s ""{app}\Wcam.VirtualCamera.dll"""; Flags: runhidden waituntilterminated; RunOnceId: "UnregisterCamera"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#FirewallRule}"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveFirewallRule"
Filename: "{sys}\net.exe"; Parameters: "stop FrameServer"; Flags: runhidden waituntilterminated; RunOnceId: "ReleaseCamera"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{commonappdata}\WCam"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserData: String;
begin
  if CurUninstallStep <> usPostUninstall then
    exit;
  UserData := ExpandConstant('{localappdata}\wcam');
  if not DirExists(UserData) then
    exit;
  if UninstallSilent then
    exit;
  if MsgBox(CustomMessage('RemoveUserData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    DelTree(UserData, True, True, True);
end;
