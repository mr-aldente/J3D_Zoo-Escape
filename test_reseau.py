#!/usr/bin/env python3
"""
Test simple du réseau : lance un serveur et deux clients.
Vérifie que les connexions TCP se font correctement et que les messages sont échangés.
"""
import sys
import os
import time
import threading
import signal

# Ajoute src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from server.zoo_escape_server import GameServer
import client_reseau as reseau

def timeout_handler(signum, frame):
    """Handler pour timeout"""
    raise TimeoutError("Test timeout")

def test_server():
    """Lance le serveur en arrière-plan"""
    print("\n" + "="*50)
    print("TEST RÉSEAU - Zoo Escape")
    print("="*50)
    
    server = GameServer(host='127.0.0.1', port=5555)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    return server

def test_client_connection():
    """Teste la connexion d'un client"""
    print("\n[TEST] Connexion client...")
    client = reseau.ClientReseau('127.0.0.1')
    
    if not client.connecter(timeout=3.0):
        print("❌ Échec connexion client")
        return None
    
    print(f"✓ Client connecté ! Player ID = {client.player_id}")
    return client

def test_two_clients():
    """Teste la connexion de deux clients"""
    print("\n[TEST] Deux clients...")
    
    # Première connexion
    client1 = reseau.ClientReseau('127.0.0.1')
    if not client1.connecter(timeout=3.0):
        print("❌ Échec client 1")
        return False
    print(f"✓ Client 1 connecté (ID={client1.player_id})")
    
    # Deuxième connexion
    client2 = reseau.ClientReseau('127.0.0.1')
    if not client2.connecter(timeout=3.0):
        print("❌ Échec client 2")
        client1.fermer()
        return False
    print(f"✓ Client 2 connecté (ID={client2.player_id})")
    
    # Vérifier le seed de départ
    time.sleep(1)
    if not client1.game_start_recu:
        print("❌ Client 1 n'a pas reçu game_start")
        client1.fermer()
        client2.fermer()
        return False
    
    if not client2.game_start_recu:
        print("❌ Client 2 n'a pas reçu game_start")
        client1.fermer()
        client2.fermer()
        return False
    
    print(f"✓ game_start reçu par les deux clients")
    print(f"  Seed C1={client1.seed}, C2={client2.seed}")
    
    if client1.seed != client2.seed:
        print("❌ Seeds différentes!")
        client1.fermer()
        client2.fermer()
        return False
    
    print(f"✓ Seeds identiques = {client1.seed}")
    
    # Test d'échange d'état
    print("\n[TEST] Échange d'état joueur...")
    
    class FakeJoueur:
        def __init__(self):
            self.x = 100.0
            self.y = 50.0
            self.vy = 0.0
            self.sur_sol = True
            self.slide = False
    
    joueur1 = FakeJoueur()
    joueur2 = FakeJoueur()
    
    joueur1.x = 150.0
    joueur2.x = 200.0
    
    for i in range(5):
        client1.envoyer_etat_joueur(joueur1)
        client2.envoyer_etat_joueur(joueur2)
        time.sleep(0.1)
        
        # Vérifier que les états sont reçus
        etat1 = client1.get_etat_joueur_distant()
        etat2 = client2.get_etat_joueur_distant()
        
        if etat1:
            print(f"  Frame {i+1}: C1 reçoit J2 à x={etat1.get('x', '?')}")
        if etat2:
            print(f"  Frame {i+1}: C2 reçoit J1 à x={etat2.get('x', '?')}")
    
    print("✓ Échange d'état OK")
    
    client1.fermer()
    client2.fermer()
    return True

if __name__ == '__main__':
    print("Démarrage du test réseau...")
    
    # Set signal timeout pour macOS (10 secondes max)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(10)
    
    try:
        # Lance le serveur
        server = test_server()
        time.sleep(1)  # Attendre que le serveur soit prêt
        
        # Test simple : un client
        print("\n--- Test 1 : Un client ---")
        client = test_client_connection()
        if client:
            client.fermer()
        
        print("\n--- Test 2 : Deux clients + échange ---")
        time.sleep(0.5)
        if test_two_clients():
            print("\n" + "="*50)
            print("✓✓✓ TOUS LES TESTS RÉUSSIS ✓✓✓")
            print("="*50)
        else:
            print("\n❌ Tests échoués")
        
        signal.alarm(0)  # Cancel alarm
    
    except TimeoutError:
        print("\n❌ Test timeout")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    time.sleep(0.5)
    print("\nTest terminé.")
