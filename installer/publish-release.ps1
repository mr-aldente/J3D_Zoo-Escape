# Publie ZooEscape_Setup.exe sur GitHub Releases
# Prerequis : gh auth login

$ErrorActionPreference = "Stop"
$Version = "v1.0.8"
$Repo = "mr-aldente/J3D_Zoo-Escape"
$Setup = Join-Path $PSScriptRoot "output\ZooEscape_Setup.exe"

if (-not (Test-Path $Setup)) {
    Write-Error "Fichier introuvable : $Setup — lancez build.cmd d'abord."
}

gh auth status | Out-Null

$exists = $false
try {
    gh release view $Version --repo $Repo 2>$null | Out-Null
    $exists = $LASTEXITCODE -eq 0
} catch {}

if ($exists) {
    Write-Host "Mise a jour de la release $Version..."
    gh release upload $Version $Setup --repo $Repo --clobber
} else {
    Write-Host "Creation de la release $Version..."
    gh release create $Version --repo $Repo --title "Zoo Escape 1.0.8" `
        --notes "Fix release packaging: installer version synced to 1.0.8 and server __pycache__/.pyc excluded. Includes the network restart on R at end screen." `
        $Setup
}

Write-Host "OK : https://github.com/$Repo/releases/tag/$Version"
