# Téléchargement du jeu

## Pour les joueurs (PC portable, etc.)

Il faut le fichier **`ZooEscape_Setup.exe`** (~120 Mo), pas un petit fichier de quelques Ko.

- **Clic droit** → **Exécuter en tant qu'administrateur**
- Pas besoin d'installer Python ni Inno Setup sur le PC de jeu
- Si Windows affiche un avertissement bleu : **Informations complémentaires** → **Exécuter quand même**

## Pour l'équipe (générer l'installateur)

```bat
cd installer
build.cmd
```

Fichier produit : `installer\output\ZooEscape_Setup.exe` (copié aussi ici).

## GitHub Releases

Release publiée : https://github.com/mr-aldente/J3D_Zoo-Escape/releases/tag/v1.0.0

Lien direct du installateur :
https://github.com/mr-aldente/J3D_Zoo-Escape/releases/latest/download/ZooEscape_Setup.exe

Pour republier après un nouveau build :

```bat
cd installer
build.cmd
powershell -ExecutionPolicy Bypass -File publish-release.ps1
```
