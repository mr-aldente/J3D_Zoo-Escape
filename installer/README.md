# Installateur Zoo Escape (SAE J3D)

Conforme au cahier des charges §6.1.7 :

- Installateur avec choix des composants (jeu, site web, sources, serveur LAN)
- Désinstallation depuis le dossier d'installation (`Desinstaller.bat` / `unins000.exe`)
- Désinstallation via **Paramètres Windows → Applications**

## Prérequis de build

1. [Python 3.10+](https://www.python.org/downloads/)
2. [Inno Setup 6](https://jrsoftware.org/isinfo.php)

## Compiler

Double-cliquez **`build.cmd`** ou, dans un terminal :

```bat
cd installer
build.cmd
```

Si vous utilisez PowerShell directement et que les scripts sont bloques :

```powershell
cd installer
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

*(Erreur « l'exécution de scripts est désactivée » → utilisez `build.cmd` ci-dessus.)*

Sorties :

| Fichier | Usage |
|---------|--------|
| `dist/ZooEscape.exe` | Jeu autonome |
| `output/ZooEscape_Setup.exe` | Installateur à distribuer |
| `../docs/downloads/ZooEscape_Setup.exe` | Lien du site web |

## Installation manuelle (test)

Double-cliquez `output\ZooEscape_Setup.exe` après le build.
