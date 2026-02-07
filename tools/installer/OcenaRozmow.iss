[Setup]
AppId={{D6C4F2D5-2D2E-4C43-8C3F-1B83A9A5F51A}}
AppName=Ocena rozmow
AppVersion=0.1.0
AppPublisher=Ocena Rozmow
DefaultDirName={pf}\OcenaRozmow
DefaultGroupName=OcenaRozmow
OutputDir=..\..\dist\installer
OutputBaseFilename=OcenaRozmow-Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\..\dist\OcenaRozmow\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Ocena rozmow"; Filename: "{app}\OcenaRozmow.exe"
Name: "{commondesktop}\Ocena rozmow"; Filename: "{app}\OcenaRozmow.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Utworz ikonę na pulpicie"; GroupDescription: "Ikony:"; Flags: unchecked

[Run]
Filename: "{app}\OcenaRozmow.exe"; Description: "Uruchom program"; Flags: nowait postinstall skipifsilent
