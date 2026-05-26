# Manuel d'installation — Zoo Escape

Projet SAE J3D EPITA — Windows 10/11.

## Prérequis

- Windows 10 ou 11 (64 bits)
- Pour le **serveur multijoueur local** (composant optionnel) : Python 3.10+ et `pip install -r requirements.txt`

## Installation

1. Téléchargez `ZooEscape_Setup.exe` depuis le site du projet (section Téléchargement).
2. Double-cliquez sur l'installateur.
3. Choisissez le type d'installation :
   - **Complète** : jeu, site web local, sources et serveur LAN
   - **Jeu uniquement** : exécutable et raccourcis
   - **Personnalisée** : cochez les composants souhaités
4. Suivez l'assistant (dossier par défaut : `C:\Program Files\Zoo Escape`).
5. Optionnel : cochez « Créer un raccourci sur le Bureau » et « Lancer le jeu ».

### Composants optionnels

| Composant | Description |
|-----------|-------------|
| Jeu | Exécutable `ZooEscape.exe` (obligatoire) |
| Site web local | Copie du site dans `website\` (démonstration hors ligne) |
| Sources | Code Python (`sources\`) pour le jury / développement |
| Serveur LAN | Scripts serveur + `LancerServeur.bat` (Python requis) |

## Utilisation après installation

- **Jouer** : menu Démarrer → Zoo Escape, ou le raccourci Bureau.
- **Site web** : ouvrir `{installation}\website\index.html` dans un navigateur.
- **Héberger une partie en LAN** : lancer `server\LancerServeur.bat` (si installé), puis dans le jeu : Mode réseau → Héberger.

Le multijoueur en ligne utilise le serveur public : `j3d-zoo-escape.onrender.com` (connexion Internet requise).

## Désinstallation

Deux méthodes (exigence SAE) :

1. **Depuis le dossier d'installation** : exécuter `Desinstaller.bat` ou `unins000.exe`.
2. **Depuis Windows** : Paramètres → Applications → Applications installées → **Zoo Escape** → Désinstaller.

La configuration locale (`config.json`) est supprimée avec le jeu.

## Construction de l'installateur (équipe de développement)

```bat
cd installer
build.cmd
```

Fichiers produits :

- `installer\dist\ZooEscape.exe`
- `installer\output\ZooEscape_Setup.exe` → à copier dans `docs\downloads\` pour le lien du site

## Dépannage

| Problème | Solution |
|----------|----------|
| L'installateur refuse de démarrer | Exécuter `build.ps1` pour générer `ZooEscape.exe` avant `iscc` |
| Écran noir au menu | Vérifier que la carte graphique supporte OpenGL ; mettre à jour les pilotes |
| Serveur LAN ne démarre pas | Installer Python 3 et `pip install pygame` dans le dossier serveur |
| Antivirus bloque l'exe | Signer l'exécutable ou ajouter une exception (faux positif PyInstaller courant) |

## Aide dans le jeu

Une aide contextuelle est affichée dans les menus et écrans de jeu (texte en bas d'écran : touches, navigation).
