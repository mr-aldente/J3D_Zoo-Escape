"""
Configuration du serveur multijoueur (Internet / LAN).

Pour jouer sur deux PC distants (pas le même Wi-Fi), hébergez zoo_escape_server.py
sur une machine avec IP publique ou tunnel (port 5555 ouvert) puis renseignez :
  public_host : adresse IP ou nom de domaine
  public_port : 5555 par défaut
"""
import json
import os

_DEFAULT = {
    "public_host": "",
    "public_port": 5555,
}

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "reseau_config.json")


def charger_config_reseau() -> dict:
    cfg = dict(_DEFAULT)
    if os.path.isfile(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    host = os.environ.get("ZOO_ESCAPE_SERVER_HOST", "").strip()
    if host:
        cfg["public_host"] = host
    port = os.environ.get("ZOO_ESCAPE_SERVER_PORT", "").strip()
    if port.isdigit():
        cfg["public_port"] = int(port)
    return cfg
