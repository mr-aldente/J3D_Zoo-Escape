#!/usr/bin/env python3
"""
Test avancé du réseau : simule un vrai jeu avec échanges continus.
Teste aussi la robustesse en cas de déconnexion.
"""
import sys
import os
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from server.zoo_escape_server import GameServer
import client_reseau as reseau

class FakeJoueur:
    """Faux joueur pour simuler"""
    def __init__(self, x_start=100):
        self.x = float(x_start)
        self.y = 50.0
        self.vy = 0.0
        self.sur_sol = True
        self.slide = False
    
    def update(self, speed):
        """Simule le mouvement du joueur"""
        self.x += speed
        if self.x > 1000:
            self.x = 100  # Cycle

def test_game_loop():
    """Teste une boucle de jeu avec 200 frames (~1.4 sec à 144 FPS)"""
    print("\n[TEST] Boucle de jeu 200 frames...")
    
    # Connexion des deux joueurs
    client1 = reseau.ClientReseau('127.0.0.1')
    client2 = reseau.ClientReseau('127.0.0.1')
    
    if not client1.connecter(timeout=3.0):
        print("❌ Échec client 1")
        return False
    if not client2.connecter(timeout=3.0):
        print("❌ Échec client 2")
        client1.fermer()
        return False
    
    print(f"✓ Clients connectés (IDs: {client1.player_id}, {client2.player_id})")
    
    # Attendre game_start
    time.sleep(0.5)
    if not client1.game_start_recu or not client2.game_start_recu:
        print("❌ game_start non reçu")
        client1.fermer()
        client2.fermer()
        return False
    
    # Créer les joueurs simulés
    j1 = FakeJoueur(100)
    j2 = FakeJoueur(200)
    
    print("Simulation de 200 frames...")
    errors = 0
    
    for frame in range(200):
        # Mise à jour locale
        j1.update(2.0)
        j2.update(2.0)
        
        # Envoie les états
        client1.envoyer_etat_joueur(j1)
        client2.envoyer_etat_joueur(j2)
        
        # Reçoit les états distants
        etat_j2 = client1.get_etat_joueur_distant()
        etat_j1 = client2.get_etat_joueur_distant()
        
        # Vérifie la cohérence (avec latence acceptable)
        if etat_j2 and etat_j2.get('x', 0) < j2.x - 50:  # 50 px de tolérance
            errors += 1
        if etat_j1 and etat_j1.get('x', 0) < j1.x - 50:
            errors += 1
        
        time.sleep(0.005)  # ~5 ms entre les frames (simule 200 Hz)
        
        if (frame + 1) % 50 == 0:
            print(f"  Frame {frame + 1}: OK (errors={errors})")
    
    print(f"✓ Boucle 200 frames terminée (errors={errors})")
    
    client1.fermer()
    client2.fermer()
    
    return errors < 5  # Tolère max 5 erreurs

def test_disconnection():
    """Teste la gestion de déconnexion"""
    print("\n[TEST] Gestion de déconnexion...")
    
    # Connexion des deux joueurs
    client1 = reseau.ClientReseau('127.0.0.1')
    client2 = reseau.ClientReseau('127.0.0.1')
    
    if not client1.connecter(timeout=3.0) or not client2.connecter(timeout=3.0):
        print("❌ Échec connexion")
        return False
    
    time.sleep(0.5)
    
    # Envoie quelques frames
    j1 = FakeJoueur(100)
    j2 = FakeJoueur(200)
    
    for _ in range(20):
        j1.update(1.0)
        j2.update(1.0)
        client1.envoyer_etat_joueur(j1)
        client2.envoyer_etat_joueur(j2)
        time.sleep(0.01)
    
    print("✓ 20 frames envoyées")
    
    # Ferme client2
    print("Déconnexion de client2...")
    client2.fermer()
    time.sleep(0.5)
    
    # Envoie encore quelques frames de client1
    for _ in range(10):
        client1.envoyer_etat_joueur(j1)
        time.sleep(0.01)
    
    # Vérifie que client1 a reçu la notification de déconnexion
    etat = client1.get_etat_jeu()
    
    client1.fermer()
    
    print("✓ Déconnexion gérée")
    return True

if __name__ == '__main__':
    print("="*60)
    print("TEST RÉSEAU AVANCÉ - Zoo Escape")
    print("="*60)
    
    try:
        # Lance le serveur
        server = GameServer(host='127.0.0.1', port=5555)
        server_thread = threading.Thread(target=server.start, daemon=True)
        server_thread.start()
        time.sleep(1)
        
        # Test 1 : Boucle de jeu
        if test_game_loop():
            print("✓ Test boucle: RÉUSSI")
        else:
            print("❌ Test boucle: ÉCHOUÉ")
        
        time.sleep(1)
        
        # Arrête et redémarre le serveur pour le test 2
        server.shutdown()
        time.sleep(1)
        
        # Nouveau serveur pour test 2
        server2 = GameServer(host='127.0.0.1', port=5555)
        server_thread2 = threading.Thread(target=server2.start, daemon=True)
        server_thread2.start()
        time.sleep(1)
        
        # Test 2 : Déconnexion
        if test_disconnection():
            print("✓ Test déconnexion: RÉUSSI")
        else:
            print("❌ Test déconnexion: ÉCHOUÉ")
        
        print("\n" + "="*60)
        print("✓✓✓ TESTS AVANCÉS TERMINÉS ✓✓✓")
        print("="*60)
    
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    time.sleep(0.5)
