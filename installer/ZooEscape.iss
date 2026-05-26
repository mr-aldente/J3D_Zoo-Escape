; Inno Setup — Zoo Escape (SAE J3D)
; Compiler avec Inno Setup 6+ : iscc installer\ZooEscape.iss

#define MyAppName "Zoo Escape"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Zoo Escape — Projet J3D EPITA"
#define MyAppURL "https://j3d-zoo-escape.onrender.com"
#define MyAppExeName "ZooEscape.exe"
#define DistDir "..\installer\dist"
#define RepoRoot ".."

[Setup]
AppId={{A7F3C2E1-9B4D-4F8A-B1C2-3D4E5F607189}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
LicenseFile=
OutputDir=output
OutputBaseFilename=ZooEscape_Setup
SetupIconFile=
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Installation complète"
Name: "compact"; Description: "Jeu uniquement"
Name: "custom"; Description: "Personnalisée"; Flags: iscustom

[Components]
Name: "game"; Description: "Jeu Zoo Escape (obligatoire)"; Types: full compact custom; Flags: fixed
Name: "website"; Description: "Site web local (pages HTML, médias)"; Types: full custom
Name: "sources"; Description: "Code source Python du projet"; Types: full custom
Name: "server"; Description: "Serveur multijoueur local (nécessite Python 3)"; Types: full custom

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked
Name: "launchgame"; Description: "Lancer le jeu à la fin de l'installation"; GroupDescription: "Options :"; Components: game

[Files]
; Exécutable PyInstaller
Source: "{#DistDir}\{#MyAppExeName}"; DestDir: "{app}"; Components: game; Flags: ignoreversion
; Site web
Source: "{#RepoRoot}\docs\*"; DestDir: "{app}\website"; Components: website; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "downloads\ZooEscape_Setup.exe,downloads\ZooEscape_Setup_*.exe"
; Sources
Source: "{#RepoRoot}\src\*"; DestDir: "{app}\sources\src"; Components: sources; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc,config.json"
Source: "{#RepoRoot}\server\*"; DestDir: "{app}\sources\server"; Components: sources; Flags: ignoreversion recursesubdirs
Source: "{#RepoRoot}\requirements.txt"; DestDir: "{app}\sources"; Components: sources; Flags: ignoreversion
Source: "{#RepoRoot}\tools\*"; DestDir: "{app}\sources\tools"; Components: sources; Flags: ignoreversion recursesubdirs skipifsourcedoesntexist
; Serveur LAN (optionnel)
Source: "{#RepoRoot}\server\*"; DestDir: "{app}\server"; Components: server; Flags: ignoreversion recursesubdirs
Source: "{#RepoRoot}\requirements.txt"; DestDir: "{app}\server"; Components: server; Flags: ignoreversion
Source: "server\LancerServeur.bat"; DestDir: "{app}\server"; Components: server; Flags: ignoreversion
; Manuels
Source: "MANUEL_INSTALLATION.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "Desinstaller.bat"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\website\downloads"; Components: website

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Components: game
Name: "{group}\Site web Zoo Escape"; Filename: "{app}\website\index.html"; Components: website
Name: "{group}\Manuel d'installation"; Filename: "{app}\MANUEL_INSTALLATION.md"; Components: game
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Components: game
Name: "{group}\Serveur multijoueur (LAN)"; Filename: "{app}\server\LancerServeur.bat"; Components: server

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent; Tasks: launchgame; Components: game
Filename: "{app}\website\index.html"; Description: "Ouvrir le site web local"; Flags: postinstall skipifsilent unchecked; Components: website

[UninstallDelete]
Type: filesandordirs; Name: "{app}\config.json"
Type: filesandordirs; Name: "{app}\website"
Type: filesandordirs; Name: "{app}\sources"
Type: filesandordirs; Name: "{app}\server"

; Pas de [Code] InitializeSetup : ne pas tester dist\ sur le PC de l'utilisateur.
; ISCC echoue deja a la compilation si ZooEscape.exe manque dans installer\dist\.
