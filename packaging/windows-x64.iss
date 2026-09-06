#define MyAppName "YT Downloader by 學人新創"
#define MyAppVersion "0.1.5-dev"
#define MyAppPublisher "學人新創"
#define MyAppExeName "YT Downloader by 學人新創.exe"

[Setup]
AppId={{4A0A7D57-0F9C-4F57-A166-BDCB3E26475D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\學人新創\YT Downloader
DefaultGroupName={#MyAppPublisher}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist\installer
OutputBaseFilename=YT-Downloader-0.1.5-dev-Windows-x64-Setup
SetupIconFile=..\build\windows\app-icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=0.1.5.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Windows x64 installer
VersionInfoProductName={#MyAppName}

[Languages]
Name: "chinesetraditional"; MessagesFile: "..\build\windows\ChineseTraditional.isl"

[Tasks]
Name: "desktopicon"; Description: "建立桌面捷徑"; GroupDescription: "其他捷徑："; Flags: checkedonce

[Files]
Source: "..\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "啟動 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--remove-autostart"; Flags: runhidden waituntilterminated skipifdoesntexist
