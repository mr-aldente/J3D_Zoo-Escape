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

class GameServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.clients: Dict[int, socket.socket] = {}  # {player_id: socket}
        self.game_state = GameState()
        self.running = True
        
        print(f"[SERVEUR] Initialisation sur {host}:{port}")
    
    def start(self):
        """Démarre le serveur"""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(2)  # Max 2 joueurs
        print(f"[SERVEUR] En attente de connexions...")
        
        try:
            while self.running and len(self.clients) < 2:
                client_socket, address = self.server_socket.accept()
                player_id = len(self.clients)
                self.clients[player_id] = client_socket
                
                print(f"[SERVEUR] Joueur {player_id} connecté depuis {address}")
                
                # Envoie l'ID au joueur
                self.send_data(client_socket, {'type': 'player_id', 'id': player_id})
                
                # Lance un thread pour gérer ce client
                thread = threading.Thread(target=self.handle_client, args=(player_id, client_socket))
                thread.daemon = True
                thread.start()
            
            if len(self.clients) == 2:
                # Génère un seed partagé pour que les deux clients aient
                # exactement les mêmes obstacles (même séquence random).
                seed = random.randint(0, 2**31)
                print(f"[SERVEUR] 2 joueurs connectés ! Partie lancée. Seed={seed}")
                self.broadcast({'type': 'game_start', 'seed': seed})
                
        except KeyboardInterrupt:
            print("\n[SERVEUR] Arrêt du serveur...")
            self.shutdown()
    
    def handle_client(self, player_id: int, client_socket: socket.socket):
        """Gère la communication avec un client"""
        try:
            while self.running:
                # Reçoit les données du client
                data = self.receive_data(client_socket)
                
                if not data:
                    break
                
                # Traite selon le type de message
                if data['type'] == 'player_state':
                    self.update_player_state(player_id, data['state'])
                    
                elif data['type'] == 'damage':
                    self.game_state.shared_health -= data['amount']
                    self.broadcast({
                        'type': 'health_update',
                        'health': self.game_state.shared_health
                    })
                    
                    if self.game_state.shared_health <= 0:
                        self.broadcast({'type': 'game_over'})
                
                # Renvoie l'état complet du jeu
                self.send_data(client_socket, {
                    'type': 'game_state',
                    'state': self.serialize_game_state()
                })
                
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
        """Envoie un message à tous les clients"""
        for client_socket in self.clients.values():
            try:
                self.send_data(client_socket, data)
            except:
                pass
    
    def send_data(self, client_socket: socket.socket, data: dict):
        """Envoie des données via socket"""
        try:
            serialized = pickle.dumps(data)
            # Envoie d'abord la taille, puis les données
            size = len(serialized)
            client_socket.sendall(size.to_bytes(4, 'big'))
            client_socket.sendall(serialized)
        except Exception as e:
            print(f"[SERVEUR] Erreur d'envoi: {e}")
    
    def receive_data(self, client_socket: socket.socket) -> Optional[dict]:
        """Reçoit des données via socket"""
        try:
            # Reçoit d'abord la taille
            size_bytes = client_socket.recv(4)
            if not size_bytes:
                return None
            
            size = int.from_bytes(size_bytes, 'big')
            
            # Reçoit les données
            data = b''
            while len(data) < size:
                packet = client_socket.recv(min(size - len(data), 4096))
                if not packet:
                    return None
                data += packet
            
            return pickle.loads(data)
        except Exception as e:
            print(f"[SERVEUR] Erreur de réception: {e}")
            return None
    
    def disconnect_client(self, player_id: int, client_socket: socket.socket):
        """Gère la déconnexion d'un client"""
        print(f"[SERVEUR] Joueur {player_id} déconnecté")
        client_socket.close()
        if player_id in self.clients:
            del self.clients[player_id]
        
        # Notifie l'autre joueur
        self.broadcast({'type': 'player_disconnected', 'player_id': player_id})
    
    def shutdown(self):
        """Arrête proprement le serveur"""
        self.running = False
        self.broadcast({'type': 'server_shutdown'})
        
        for client_socket in self.clients.values():
            client_socket.close()
        
        self.server_socket.close()
        print("[SERVEUR] Serveur arrêté.")

if __name__ == "__main__":
    # Affiche l'IP locale pour que l'autre joueur sache où se connecter
    try:
        ip_locale = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip_locale = "inconnue"
    print("=" * 45)
    print("   ZOO ESCAPE — Serveur de jeu")
    print("=" * 45)
    print(f"   IP locale    : {ip_locale}")
    print(f"   Port         : 5555")
    print(f"   Donne cette IP à l'autre joueur !")
    print("=" * 45)
    server = GameServer(host='0.0.0.0', port=5555)
    server.start()