"""
Chemins d'installation — développement et exécutable PyInstaller.
"""
import os
import sys


def is_frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def resource_dir() -> str:
    """Ressources en lecture seule (assets embarqués dans l'exe)."""
    if is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def install_dir() -> str:
    """Dossier d'installation (config.json et fichiers optionnels)."""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def project_root() -> str:
    if is_frozen():
        return install_dir()
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def config_path() -> str:
    return os.path.join(install_dir(), "config.json")


def server_script() -> str:
    return os.path.join(project_root(), "server", "zoo_escape_server.py")


def docs_dir() -> str:
    return os.path.join(project_root(), "docs")


def map_overall_path() -> str:
    bundled = os.path.join(resource_dir(), "Map-overall.png")
    if os.path.isfile(bundled):
        return bundled
    return os.path.join(docs_dir(), "Map-overall.png")
