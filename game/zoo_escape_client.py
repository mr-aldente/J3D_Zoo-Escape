import socket
import pickle
import threading
from typing import Optional, Callable

class NetworkClient:
    """Client réseau pour Zoo Escape"""
    
    def __init__(self, server_ip: str, server_port: int = 5555):
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = None
        self.connected = False
        self.player_id = None
        
        # État du jeu reçu du serveur
        self.game_state = None
        self.lock = threading.Lock()
        
        # Callback quand on reçoit des données
        self.on_game_state_received: Optional[Callable] = None
        self.on_game_start: Optional[Callable] = None
        self.on_game_over: Optional[Callable] = None
        
    def connect(self) -> bool:
        """Se connecte au serveur"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_ip, self.server_port))
            self.connected = True
            
            print(f"[CLIENT] Connecté à {self.server_ip}:{self.server_port}")
            
            # Reçoit l'ID du joueur
            data = self.receive_data()
            if data and data['type'] == 'player_id':
                self.player_id = data['id']
                print(f"[CLIENT] Vous êtes le joueur {self.player_id}")
            
            # Lance le thread de réception
            receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
            receive_thread.start()
            
            return True
            
        except Exception as e:
            print(f"[CLIENT] Erreur de connexion: {e}")
            self.connected = False
            return False
    
    def send_player_state(self, x: float, y: float, velocity_y: float, 
                          is_jumping: bool, is_sliding: bool, has_item: bool,
                          animation_state: str):
        """Envoie l'état du joueur au serveur"""
        if not self.connected:
            return
        
        data = {
            'type': 'player_state',
            'state': {
                'x': x,
                'y': y,
                'velocity_y': velocity_y,
                'is_jumping': is_jumping,
                'is_sliding': is_sliding,
                'has_item': has_item,
                'animation_state': animation_state
            }
        }
        self.send_data(data)
    
    def send_damage(self, amount: int):
        """Envoie un événement de dégâts"""
        if not self.connected:
            return
        
        self.send_data({
            'type': 'damage',
            'amount': amount
        })
    
    def get_other_player_state(self) -> Optional[dict]:
        """Récupère l'état de l'autre joueur"""
        with self.lock:
            if not self.game_state:
                return None
            
            # Retourne l'état de l'autre joueur
            if self.player_id == 0:
                return self.game_state.get('player2')
            else:
                return self.game_state.get('player1')
    
    def get_shared_health(self) -> int:
        """Récupère la vie partagée"""
        with self.lock:
            if self.game_state:
                return self.game_state.get('shared_health', 100)
            return 100
    
    def receive_loop(self):
        """Boucle de réception des messages du serveur"""
        while self.connected:
            try:
                data = self.receive_data()
                
                if not data:
                    break
                
                # Traite selon le type de message
                if data['type'] == 'game_state':
                    with self.lock:
                        self.game_state = data['state']
                    
                    if self.on_game_state_received:
                        self.on_game_state_received(self.game_state)
                
                elif data['type'] == 'game_start':
                    print("[CLIENT] La partie commence !")
                    if self.on_game_start:
                        self.on_game_start()
                
                elif data['type'] == 'game_over':
                    print("[CLIENT] Game Over !")
                    if self.on_game_over:
                        self.on_game_over()
                
                elif data['type'] == 'player_disconnected':
                    print(f"[CLIENT] Joueur {data['player_id']} déconnecté")
                    self.disconnect()
                
                elif data['type'] == 'server_shutdown':
                    print("[CLIENT] Serveur arrêté")
                    self.disconnect()
                    
            except Exception as e:
                print(f"[CLIENT] Erreur réception: {e}")
                break
        
        self.disconnect()
    
    def send_data(self, data: dict):
        """Envoie des données au serveur"""
        if not self.connected or not self.socket:
            return
        
        try:
            serialized = pickle.dumps(data)
            size = len(serialized)
            self.socket.sendall(size.to_bytes(4, 'big'))
            self.socket.sendall(serialized)
        except Exception as e:
            print(f"[CLIENT] Erreur d'envoi: {e}")
            self.disconnect()
    
    def receive_data(self) -> Optional[dict]:
        """Reçoit des données du serveur"""
        try:
            # Reçoit la taille
            size_bytes = self.socket.recv(4)
            if not size_bytes:
                return None
            
            size = int.from_bytes(size_bytes, 'big')
            
            # Reçoit les données
            data = b''
            while len(data) < size:
                packet = self.socket.recv(min(size - len(data), 4096))
                if not packet:
                    return None
                data += packet
            
            return pickle.loads(data)
        except Exception as e:
            print(f"[CLIENT] Erreur de réception: {e}")
            return None
    
    def disconnect(self):
        """Se déconnecte du serveur"""
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        print("[CLIENT] Déconnecté du serveur")

# ============================================
# EXEMPLE D'UTILISATION DANS TON JEU PYGAME
# ============================================

"""
Dans ton main.py ou game.py :

# Initialisation
network = NetworkClient(server_ip="TON_IP_SERVEUR", server_port=5555)

# Connexion
if network.connect():
    print("Connecté au serveur !")
    
    # Attendre que l'autre joueur se connecte
    while network.player_id is None:
        time.sleep(0.1)
    
    # Dans ta boucle de jeu (à chaque frame)
    while running:
        # ... ton code de jeu ...
        
        # Envoie ton état
        network.send_player_state(
            x=player.x,
            y=player.y,
            velocity_y=player.velocity_y,
            is_jumping=player.is_jumping,
            is_sliding=player.is_sliding,
            has_item=player.has_item,
            animation_state=player.current_animation
        )
        
        # Récupère l'autre joueur
        other_player = network.get_other_player_state()
        if other_player:
            # Dessine l'autre joueur à sa position
            draw_player(screen, other_player['x'], other_player['y'])
        
        # Affiche la vie partagée
        shared_health = network.get_shared_health()
        draw_health_bar(screen, shared_health)
        
        # Si collision avec ennemi
        if collision_with_enemy:
            network.send_damage(10)
"""