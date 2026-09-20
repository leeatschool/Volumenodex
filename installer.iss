; Script generated for Inno Setup 6
#define MyAppName "Volumenodex"
#define MyAppVersion "1.3.0"
#define MyAppPublisher "Volumenodex"
#define MyAppExeName "Volumenodex.exe"

[Setup]
AppId={{D37E8C94-2A4B-4E7B-9C0F-6A48D6C31B8A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=C:\Users\Aaron\Downloads\Volumenodex-v1.0.0-Windows-x64
OutputBaseFilename=Volumenodex-v1.3.0-Setup
SetupIconFile=C:\Users\Aaron\Downloads\Volumenodex-v1.0.0-Windows-x64\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "C:\Users\Aaron\Downloads\Volumenodex-v1.0.0-Windows-x64\Volumenodex\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
