import socket
import pickle
import threading
import random
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PlayerState:
    """État d'un joueur à synchroniser"""
    x: float
    y: float
    velocity_y: float
    is_jumping: bool
    is_sliding: bool
    has_item: bool
    animation_state: str
    
@dataclass
class GameState:
    """État global du jeu partagé"""
    player1: Optional[PlayerState] = None
    player2: Optional[PlayerState] = None
    shared_health: int = 100
    current_level: int = 1
    game_time: float = 0.0

DISCOVERY_PORT = 5556  # UDP port used for LAN broadcast discovery


def get_local_ip() -> str:
    """IP LAN réelle (évite 127.0.0.1 sous Windows)."""
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


class GameServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.clients: Dict[int, socket.socket] = {}  # {player_id: socket}
        self.game_state = GameState()
        self.lobby_chars: Dict[int, str] = {}
        self.lobby_level: Optional[dict] = None
        self._send_lock = threading.Lock()
        self.running = True
        self._beacon_running = False
        self._game_started = False

        print(f"[SERVEUR] Initialisation sur {host}:{port}")

    def _beacon_thread(self):
        """Broadcasts server presence via UDP so clients can discover it without entering an IP."""
        import json as _json
        ip_locale = get_local_ip()
        nom = socket.gethostname()
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = _json.dumps({
            'type': 'zoo_escape_server',
            'ip': ip_locale,
            'nom': nom,
            'port': self.port,
        }).encode()
        print(f"[SERVEUR] Beacon UDP démarré (port {DISCOVERY_PORT})")
        while self._beacon_running:
            try:
                udp.sendto(msg, ('<broadcast>', DISCOVERY_PORT))
            except Exception:
                pass
            import time; time.sleep(1.0)
        udp.close()
        print("[SERVEUR] Beacon UDP arrêté")

    def _demarrer_partie_si_pret(self):
        if len(self.clients) == 2 and not self._game_started:
            self._beacon_running = False
            self._game_started = True
            self.lobby_chars = {}
            self.lobby_level = None
            seed = random.randint(0, 2**31)
            print(f"[SERVEUR] 2 joueurs connectés ! Partie lancée. Seed={seed}")
            self.broadcast({'type': 'game_start', 'seed': seed})

    def start(self):
        """Démarre le serveur et reste actif pendant toute la partie."""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(2)
        print(f"[SERVEUR] En attente de connexions (max 2)...")
        print(f"[SERVEUR] IP à donner à l'autre joueur : {get_local_ip()}:{self.port}")

        self._beacon_running = True
        t_beacon = threading.Thread(target=self._beacon_thread, daemon=True)
        t_beacon.start()

        self.server_socket.settimeout(1.0)

        try:
            while self.running:
                if len(self.clients) < 2:
                    try:
                        client_socket, address = self.server_socket.accept()
                    except socket.timeout:
                        continue
                    except OSError:
                        break

                    player_id = len(self.clients)
                    self.clients[player_id] = client_socket
                    print(f"[SERVEUR] Joueur {player_id} connecté depuis {address}")

                    self.send_data(client_socket, {'type': 'player_id', 'id': player_id})

                    thread = threading.Thread(
                        target=self.handle_client,
                        args=(player_id, client_socket),
                        daemon=True,
                    )
                    thread.start()
                    self._demarrer_partie_si_pret()
                else:
                    import time
                    time.sleep(0.2)
                    if len(self.clients) < 2:
                        self._game_started = False
                        if not self._beacon_running:
                            self._beacon_running = True
                            t_beacon = threading.Thread(target=self._beacon_thread, daemon=True)
                            t_beacon.start()

        except KeyboardInterrupt:
            print("\n[SERVEUR] Arrêt du serveur...")
        finally:
            self._beacon_running = False
            self.shutdown()
    
    def handle_client(self, player_id: int, client_socket: socket.socket):
        """Gère la communication avec un client"""
        client_socket.settimeout(15.0)
        try:
            while self.running:
                try:
                    data = self.receive_data(client_socket)
                except socket.timeout:
                    continue

                if data is None:
                    print(f"[SERVEUR] Joueur {player_id} déconnecté (socket fermée)")
                    break

                msg_type = data.get('type')
                
                # Traite selon le type de message
                if msg_type == 'player_state':
                    self.update_player_state(player_id, data.get('state', {}))
                    self.broadcast({
                        'type': 'game_state',
                        'state': self.serialize_game_state(),
                    })
                elif msg_type == 'lobby_char':
                    perso = data.get('personnage')
                    if isinstance(perso, str) and perso:
                        self.lobby_chars[player_id] = perso
                        self.broadcast({
                            'type': 'lobby_state',
                            'chars': dict(self.lobby_chars),
                            'both_ready': 0 in self.lobby_chars and 1 in self.lobby_chars,
                        })

                elif msg_type == 'lobby_level':
                    # Seul J1 (host logique) choisit la difficulté / niveau.
                    if player_id == 0:
                        cfg = data.get('config')
                        if isinstance(cfg, dict):
                            self.lobby_level = cfg
                            self.broadcast({'type': 'lobby_level', 'config': cfg})

                elif msg_type == 'damage':
                    amount = data.get('amount', 1)
                    self.game_state.shared_health -= amount
                    self.broadcast({
                        'type': 'health_update',
                        'health': self.game_state.shared_health
                    })
                    
                    if self.game_state.shared_health <= 0:
                        self.broadcast({'type': 'game_over'})
                        break
                
                elif msg_type == 'heartbeat':
                    self.send_data(client_socket, {'type': 'heartbeat_ack'})
                    continue

        except Exception as e:
            print(f"[SERVEUR] Erreur avec joueur {player_id}: {e}")
        finally:
            self.disconnect_client(player_id, client_socket)
    
    def update_player_state(self, player_id: int, state_data: dict):
        """Met à jour l'état d'un joueur"""
        player_state = PlayerState(**state_data)
        
        if player_id == 0:
            self.game_state.player1 = player_state
        else:
            self.game_state.player2 = player_state
    
    def serialize_game_state(self) -> dict:
        """Sérialise l'état du jeu pour envoi"""
        return {
            'player1': self.game_state.player1.__dict__ if self.game_state.player1 else None,
            'player2': self.game_state.player2.__dict__ if self.game_state.player2 else None,
            'shared_health': self.game_state.shared_health,
            'current_level': self.game_state.current_level,
            'game_time': self.game_state.game_time
        }
    
    def broadcast(self, data: dict):
        """Envoie un message à tous les clients connectés.
        Ignore les erreurs d'envoi individuelles pour que un client en erreur
        n'affecte pas les autres."""
        dead_clients = []
        for player_id, client_socket in list(self.clients.items()):
            try:
                self.send_data(client_socket, data)
            except Exception as e:
                print(f"[SERVEUR] Erreur broadcast vers joueur {player_id}: {e}")
                dead_clients.append(player_id)
        
        # Nettoie les clients morts
        for player_id in dead_clients:
            if player_id in self.clients:
                try:
                    self.clients[player_id].close()
                except:
                    pass
                del self.clients[player_id]
    
    def _recv_exact(self, client_socket: socket.socket, n: int) -> Optional[bytes]:
        """Lit exactement N octets depuis le socket (robuste)."""
        data = b''
        while len(data) < n:
            try:
                chunk = client_socket.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except socket.timeout:
                if len(data) == 0:
                    raise
                continue
            except Exception:
                return None
        return data
    
    def send_data(self, client_socket: socket.socket, data: dict):
        """Envoie des données via socket"""
        try:
            serialized = pickle.dumps(data)
            size = len(serialized)
            if size > 1_000_000:
                print(f"[SERVEUR] Payload trop gros: {size} bytes")
                return
            # Plusieurs threads serveur envoient potentiellement en parallèle :
            # on sérialise les écritures pour éviter la corruption de trames TCP.
            with self._send_lock:
                client_socket.sendall(size.to_bytes(4, 'big'))
                client_socket.sendall(serialized)
        except OSError as e:
            # Connexion déjà fermée (déconnexion normale) : pas de log bruyant
            if self.running and getattr(e, "errno", None) not in (9, 32, 54, 104):
                print(f"[SERVEUR] Erreur d'envoi: {e}")
    
    def receive_data(self, client_socket: socket.socket) -> Optional[dict]:
        """Reçoit des données via socket (protocole: [4 bytes taille][payload pickle])"""
        try:
            size_bytes = self._recv_exact(client_socket, 4)
            if not size_bytes:
                return None

            size = int.from_bytes(size_bytes, 'big')
            if size <= 0 or size > 1_000_000:
                print(f"[SERVEUR] Taille invalide reçue: {size}")
                return None

            payload = self._recv_exact(client_socket, size)
            if not payload:
                return None

            return pickle.loads(payload)
        except socket.timeout:
            raise
        except Exception as e:
            print(f"[SERVEUR] Erreur de réception: {e}")
            return None
    
    def disconnect_client(self, player_id: int, client_socket: socket.socket):
        """Gère la déconnexion d'un client proprement"""
        print(f"[SERVEUR] Joueur {player_id} déconnecté")
        try:
            client_socket.close()
        except:
            pass
        
        if player_id in self.clients:
            del self.clients[player_id]

        if len(self.clients) < 2:
            self._game_started = False
            self.lobby_level = None
            self.lobby_chars = {}

        # Notifie l'autre joueur si la partie est en cours
        if len(self.clients) > 0:
            self.broadcast({'type': 'player_disconnected', 'player_id': player_id})
    
    def shutdown(self):
        """Arrête proprement le serveur"""
        self.running = False
        self._beacon_running = False
        if self.clients:
            self.broadcast({'type': 'server_shutdown'})
        
        for client_socket in self.clients.values():
            try:
                client_socket.close()
            except:
                pass
        
        try:
            self.server_socket.close()
        except:
            pass
        print("[SERVEUR] Serveur arrêté.")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "5555"))
    ip_locale = get_local_ip()
    print("=" * 45)
    print("   ZOO ESCAPE — Serveur de jeu")
    print("=" * 45)
    print(f"   IP locale    : {ip_locale}")
    print(f"   Port         : {port}")
    print("   Donne cette IP à l'autre joueur (même Wi-Fi ou IP publique).")
    print("=" * 45)
    server = GameServer(host='0.0.0.0', port=port)
    server.start()