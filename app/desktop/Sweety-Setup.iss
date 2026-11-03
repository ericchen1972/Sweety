; Build through build_windows_installer.py using a verified release directory.
#ifndef PackageDir
  #error PackageDir must point to the release Sweety directory
#endif
#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef BuildDir
  #error BuildDir is required
#endif

[Setup]
AppId={{A7E7F70A-DC1B-4C3F-9753-B5F094B326D2}
AppName=Sweety
AppVersion={#AppVersion}
AppPublisher=Eric Chen
AppPublisherURL=https://sweety.tw/
DefaultDirName={localappdata}\Programs\Sweety
DefaultGroupName=Sweety
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#BuildDir}
OutputBaseFilename=Sweety-Windows-Setup-{#AppVersion}
SetupIconFile={#BuildDir}\Sweety.ico
UninstallDisplayIcon={app}\Sweety.exe
LicenseFile=..\..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
AppMutex=Local\Sweety.Portable
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousTasks=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesetraditional"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#PackageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Sweety"; Filename: "{app}\Sweety.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Sweety"; Filename: "{app}\Sweety.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Sweety.exe"; Description: "{cm:LaunchProgram,Sweety}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent unchecked

; No UninstallDelete: user settings, credentials and sessions are kept outside {app}.
