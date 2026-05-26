"""
client_reseau.py — Client réseau de Zoo Escape
================================================
Ce module gère la connexion TCP d'un joueur au serveur Zoo Escape.

Fonctionnement général :
  1. Le joueur "hôte" lance server/zoo_escape_server.py (automatiquement depuis le menu).
  2. Les deux joueurs lancent le jeu et se connectent au même serveur.
  3. Le serveur attribue un player_id (0 = J1, 1 = J2) à chaque client.
  4. Chaque client envoie son état à chaque frame et reçoit l'état global (incl. l'autre joueur).
  5. Le serveur envoie un signal 'game_start' avec un seed partagé quand les 2 joueurs sont là.

Format des messages (dictionnaires sérialisés par pickle) :
  → client envoie :  {'type': 'player_state', 'state': {...}}
  ← serveur envoie : {'type': 'player_id', 'id': 0|1}
                     {'type': 'game_start', 'seed': int}
                     {'type': 'game_state', 'state': {...}}
                     {'type': 'game_over'} / {'type': 'player_disconnected'}

La réception est faite dans un thread séparé pour ne pas bloquer la boucle de jeu.
"""

import socket
import pickle
import threading
import json as _json
from typing import Optional, List

DISCOVERY_PORT = 5556  # Must match zoo_escape_server.py
DEFAULT_PORT = 5555


def get_local_ip() -> str:
    """IP LAN de ce PC (pour affichage à l'hôte)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


def scanner_jeux_lan(timeout: float = 2.0) -> List[dict]:
    """
    Écoute les beacons UDP émis par le(s) serveur(s) Zoo Escape sur le LAN.
    Retourne une liste de dicts {'ip': str, 'nom': str, 'port': int} (dédupliqués par IP).
    """
    found: dict[str, dict] = {}  # ip → info
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        udp.bind(('', DISCOVERY_PORT))
        udp.settimeout(0.2)
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data, addr = udp.recvfrom(1024)
                msg = _json.loads(data.decode())
                if msg.get('type') == 'zoo_escape_server':
                    ip = msg.get('ip', addr[0])
                    found[ip] = {'ip': ip, 'nom': msg.get('nom', ip), 'port': msg.get('port', 5555)}
            except socket.timeout:
                pass
            except Exception:
                pass
    except Exception as e:
        print(f"[DISCOVERY] Erreur scanner : {e}")
    finally:
        udp.close()
    return list(found.values())


class ClientReseau:
    """
    Gère la connexion TCP avec le serveur de jeu.

    Utilisation typique :
        client = ClientReseau("192.168.1.10")
        if client.connecter():
            # attendre game_start dans l'écran d'attente du menu
            # puis passer client à JeuDeuxJoueurs
            jeu = JeuDeuxJoueurs(config_niveau, client_reseau=client, player_id=client.player_id)
    """

    def __init__(self, host: str, port: int = DEFAULT_PORT):
        self.host = host
        self.port = int(port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.player_id: Optional[int] = None   # attribué par le serveur (0=J1, 1=J2)
        self.seed: Optional[int] = None        # seed partagé pour la génération des obstacles
        self.connecte = False
        self.game_start_recu = False
        self._dernier_etat_jeu: Optional[dict] = None
        self._lock = threading.Lock()
        self._running = False
        self._heartbeat_tick = 0

    # ── Connexion ──────────────────────────────────────────────────────────────

    def connecter(self, timeout=5.0) -> bool:
        """
        Tente de se connecter au serveur.
        Retourne True si la connexion est établie et le player_id reçu.
        """
        try:
            self.sock.settimeout(timeout)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(5.0)  # Garde 5 sec timeout après connexion

            # Le serveur envoie immédiatement le player_id
            data = self._recevoir_bloquant()
            if data and data.get('type') == 'player_id':
                self.player_id = data['id']
                self.connecte = True
                self._running = True
                # Démarre le thread de réception en arrière-plan
                t = threading.Thread(target=self._boucle_reception, daemon=True)
                t.start()
                print(f"[CLIENT] Connecté ! Player ID = {self.player_id}")
                return True
        except Exception as e:
            print(f"[CLIENT] Erreur connexion à {self.host}:{self.port} → {e}")
        return False

    # ── Communication en jeu ───────────────────────────────────────────────────

    def envoyer_heartbeat(self) -> bool:
        """Maintient la connexion pendant les menus (difficulté, carte, etc.)."""
        if not self.connecte:
            return False
        self._heartbeat_tick += 1
        if self._heartbeat_tick % 15 != 0:
            return True
        try:
            self._envoyer({'type': 'heartbeat'})
            return True
        except Exception as e:
            print(f"[CLIENT] Erreur heartbeat: {e}")
            self.connecte = False
            return False

    def connexion_perdue(self) -> bool:
        """True si le serveur a signalé une déconnexion ou si le socket est mort."""
        if not self.connecte:
            return True
        with self._lock:
            etat = self._dernier_etat_jeu
        if etat and etat.get('type') in ('player_disconnected', 'server_shutdown'):
            self.connecte = False
            return True
        return False

    def preparer_debut_partie(self) -> None:
        """Efface les vieux messages d'erreur reçus pendant les menus."""
        with self._lock:
            if self._dernier_etat_jeu and self._dernier_etat_jeu.get('type') in (
                'player_disconnected', 'server_shutdown', 'game_over',
            ):
                self._dernier_etat_jeu = None

    def envoyer_etat_joueur(self, joueur) -> None:
        """
        Envoie l'état du joueur local au serveur.
        Appelé chaque frame pendant la partie.
        """
        if not self.connecte:
            return
        try:
            etat = {
                'x':              joueur.x,
                'y':              joueur.y,
                'velocity_y':     joueur.vy,
                'is_jumping':     not joueur.sur_sol,
                'is_sliding':     joueur.slide,
                'has_item':       False,
                'animation_state': (
                    'slide' if joueur.slide
                    else ('jump' if not joueur.sur_sol else 'run')
                ),
            }
            self._envoyer({'type': 'player_state', 'state': etat})
        except Exception as e:
            print(f"[CLIENT] Erreur envoi état joueur: {e}")
            self.connecte = False

    def get_etat_jeu(self) -> Optional[dict]:
        """
        Retourne le dernier état de jeu reçu du serveur (thread-safe).
        Contient les positions des deux joueurs, la santé partagée, etc.
        """
        with self._lock:
            return self._dernier_etat_jeu

    def get_etat_joueur_distant(self) -> Optional[dict]:
        """
        Raccourci pour extraire uniquement les données de l'autre joueur
        depuis le dernier état de jeu reçu.
        Retourne None si pas encore de données.
        """
        with self._lock:
            etat = self._dernier_etat_jeu
        if not etat or etat.get('type') != 'game_state':
            return None
        state = etat.get('state', {})
        # player_id 0 → on est J1 → on veut les données de J2, et inversement
        cle = 'player2' if self.player_id == 0 else 'player1'
        return state.get(cle)

    # ── Déconnexion ────────────────────────────────────────────────────────────

    def fermer(self) -> None:
        """Ferme proprement la connexion."""
        self._running = False
        self.connecte = False
        try:
            self.sock.close()
        except Exception:
            pass

    # ── Thread de réception ────────────────────────────────────────────────────

    def _boucle_reception(self) -> None:
        """
        Tourne en arrière-plan. Met à jour _dernier_etat_jeu à chaque message reçu.
        Gère également les messages spéciaux (game_start, game_over, déconnexion).
        Les messages heartbeat_ack sont ignorés silencieusement (confirmé connexion).
        """
        while self._running:
            data = self._recevoir_bloquant()
            if data is None:
                self.connecte = False
                print("[CLIENT] Connexion perdue.")
                break

            msg_type = data.get('type')

            if msg_type == 'heartbeat_ack':
                # Confirmation de vie du serveur - ignoré silencieusement
                continue

            elif msg_type == 'game_start':
                self.seed = data.get('seed')
                self.game_start_recu = True
                print(f"[CLIENT] Partie lancée ! Seed = {self.seed}")

            elif msg_type in ('game_state', 'health_update', 'game_over',
                              'player_disconnected', 'server_shutdown'):
                with self._lock:
                    self._dernier_etat_jeu = data

    # ── Sérialisation bas niveau ───────────────────────────────────────────────

    def _envoyer(self, data: dict) -> None:
        """Sérialise et envoie un message : [4 octets taille][payload pickle]."""
        try:
            payload = pickle.dumps(data)
            size = len(payload)
            if size > 1_000_000:
                print(f"[CLIENT] Payload trop gros: {size} bytes")
                self.connecte = False
                return
            self.sock.sendall(size.to_bytes(4, 'big'))
            self.sock.sendall(payload)
        except Exception as e:
            print(f"[CLIENT] Erreur envoi : {e}")
            self.connecte = False

    def _recv_exact(self, n: int) -> Optional[bytes]:
        """Lit exactement n octets depuis le socket (robuste TCP)."""
        data = b''
        while len(data) < n:
            try:
                chunk = self.sock.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except socket.timeout:
                if len(data) == 0:
                    return None
                continue
            except Exception:
                return None
        return data

    def _recevoir_bloquant(self) -> Optional[dict]:
        """
        Lit un message complet depuis le socket (bloquant).
        Protocole : [4 octets big-endian = taille][payload pickle]
        """
        try:
            size_bytes = self._recv_exact(4)
            if not size_bytes:
                return None
            size = int.from_bytes(size_bytes, 'big')
            if size <= 0 or size > 1_000_000:
                print(f"[CLIENT] Taille invalide: {size}")
                return None
            payload = self._recv_exact(size)
            if not payload:
                return None
            return pickle.loads(payload)
        except Exception as e:
            if self._running:
                print(f"[CLIENT] Erreur réception : {e}")
            return None