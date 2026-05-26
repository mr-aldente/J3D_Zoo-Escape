# Build Zoo Escape - exe PyInstaller + installateur Inno Setup
# Prerequis : Python 3.10-3.12, pip, Inno Setup 6

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$InstallerDir = Join-Path $Root "installer"
$DistDir = Join-Path $InstallerDir "dist"
$OutputDir = Join-Path $InstallerDir "output"
$DownloadsDir = Join-Path $Root "docs\downloads"
$SpecFile = Join-Path $InstallerDir "zoo_escape.spec"

Set-Location $Root

Write-Host "=== Zoo Escape - build installateur ===" -ForegroundColor Cyan

function Invoke-Python {
    param([string[]]$PythonArgs)
    if ($script:PyLauncher -eq "python") {
        & python @PythonArgs
    } else {
        & py $script:PyVersion @PythonArgs
    }
}

$script:PyLauncher = "python"
$script:PyVersion = ""
foreach ($v in @("3.12", "3.11", "3.10", "3")) {
    & py "-$v" -c "import sys" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $script:PyLauncher = "py"
        $script:PyVersion = "-$v"
        break
    }
}

Write-Host "Python : $PyLauncher $PyVersion" -ForegroundColor Gray
Invoke-Python -PythonArgs @(
    "-c", "import sys; v=sys.version_info; assert v.major==3 and v.minor<=12, 'Python 3.10-3.12 requis'"
)

Write-Host "[1/4] Dependances Python..." -ForegroundColor Yellow
Invoke-Python -PythonArgs @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Python -PythonArgs @("-m", "pip", "install", "-r", "requirements.txt", "pyinstaller")

Write-Host "[2/4] PyInstaller (ZooEscape.exe)..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
Invoke-Python -PythonArgs @("-m", "PyInstaller", "--noconfirm", "--clean", $SpecFile)

$ExeDist = Join-Path $DistDir "ZooEscape.exe"
if (-not (Test-Path $ExeDist)) {
    $Built = Join-Path $Root "dist\ZooEscape.exe"
    if (Test-Path $Built) {
        Copy-Item $Built $ExeDist -Force
    } else {
        throw "ZooEscape.exe introuvable apres PyInstaller."
    }
}

Write-Host "[3/4] Inno Setup (ZooEscape_Setup.exe)..." -ForegroundColor Yellow
$Iscc = $null
if (Get-Command iscc -ErrorAction SilentlyContinue) {
    $Iscc = "iscc"
} elseif (Test-Path "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") {
    $Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
} elseif (Test-Path "$env:ProgramFiles\Inno Setup 6\ISCC.exe") {
    $Iscc = "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
}
if (-not $Iscc) {
    Write-Warning "Inno Setup non trouve : https://jrsoftware.org/isinfo.php"
    Write-Warning "ZooEscape.exe est dans installer\dist\"
    exit 0
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
& $Iscc (Join-Path $InstallerDir "ZooEscape.iss")

$SetupExe = Join-Path $OutputDir "ZooEscape_Setup.exe"
if (-not (Test-Path $SetupExe)) {
    throw "ZooEscape_Setup.exe non genere."
}

Write-Host "[4/4] Copie vers docs/downloads..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $DownloadsDir | Out-Null
Copy-Item $SetupExe (Join-Path $DownloadsDir "ZooEscape_Setup.exe") -Force

Write-Host ""
Write-Host "Termine." -ForegroundColor Green
Write-Host "  Jeu          : $ExeDist"
Write-Host "  Installateur : $SetupExe"
Write-Host "  Site web     : docs\downloads\ZooEscape_Setup.exe"
Write-Host "  Lien HTML    : downloads/ZooEscape_Setup.exe"
