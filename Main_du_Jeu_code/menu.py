import pygame
import sys
import os
import cv2 
import jeu

pygame.init()

LARGEUR = 1024
HAUTEUR = 768
FPS = 60

BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
ACCENT = (56, 189, 248)      

ecran = pygame.display.set_mode((LARGEUR, HAUTEUR))
pygame.display.set_caption("Zoo Escape - Menu Principal")

class BoutonTransparent:
    def __init__(self, x, y, largeur, hauteur, texte, action=None):
        self.rect = pygame.Rect(x, y, largeur, hauteur)
        self.texte = texte
        self.action = action
        self.est_survole = False
        self.police = pygame.font.Font(None, 40)

    def dessiner(self, surface):
        surface_bouton = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        txt_rect = pygame.Rect(0, 0, self.rect.width, self.rect.height)

        if self.est_survole:
            pygame.draw.rect(surface_bouton, (255, 255, 255, 60), surface_bouton.get_rect(), border_radius=30)
            pygame.draw.rect(surface_bouton, ACCENT, surface_bouton.get_rect(), width=2, border_radius=30)
            txt_surface = self.police.render(self.texte, True, ACCENT)
            glow = self.police.render(self.texte, True, ACCENT)
            glow.set_alpha(100)
            txt_surf_rect = txt_surface.get_rect(center=txt_rect.center)
            surface_bouton.blit(glow, (txt_surf_rect.x, txt_surf_rect.y + 2))
            surface_bouton.blit(txt_surface, txt_surf_rect)
        else:
            pygame.draw.rect(surface_bouton, (0, 0, 0, 150), surface_bouton.get_rect(), border_radius=30)
            pygame.draw.rect(surface_bouton, (255, 255, 255, 100), surface_bouton.get_rect(), width=1, border_radius=30)
            txt_surface = self.police.render(self.texte, True, BLANC)
            txt_surf_rect = txt_surface.get_rect(center=txt_rect.center)
            surface_bouton.blit(txt_surface, txt_surf_rect)

        surface.blit(surface_bouton, self.rect.topleft)

    def verifier_survol(self, position_souris):
        self.est_survole = self.rect.collidepoint(position_souris)

    def gerer_clic(self, position_souris):
        if self.rect.collidepoint(position_souris) and self.action:
            self.action()

def lancer_partie():
    jeu.lancer_jeu(ecran) 
    pygame.display.set_mode((LARGEUR, HAUTEUR))

def quitter_jeu():
    pygame.quit()
    sys.exit()

def afficher_menu():
    horloge = pygame.time.Clock()
    
    dossier_courant = os.path.dirname(__file__)
    chemin_video = os.path.join(dossier_courant, "assets", "background.mp4")
    
    cap = cv2.VideoCapture(chemin_video)
    video_marche = cap.isOpened()
    
    if not video_marche:
        print(f"ATTENTION : Impossible de lire la vidéo au chemin : {chemin_video}")
        print("Vérifie que le fichier s'appelle bien background.mp4 et qu'il n'y a pas de double extension (.mp4.mp4)")

    image_logo = None
    try:
        chemin_logo = os.path.join(dossier_courant, "assets", "logo.png")
        image_logo = pygame.image.load(chemin_logo).convert_alpha()
    except Exception as e:
        print(f"✗ Erreur logo image : {e}")
        image_logo = None

    largeur_btn = 320
    hauteur_btn = 65
    centre_x = LARGEUR // 2 - largeur_btn // 2
    
    boutons = [
        BoutonTransparent(centre_x, 470, largeur_btn, hauteur_btn, "JOUER", lancer_partie),
        BoutonTransparent(centre_x, 580, largeur_btn, hauteur_btn, "QUITTER", quitter_jeu)
    ]
    
    police_titre = pygame.font.Font(None, 110)
    police_sous_titre = pygame.font.Font(None, 36)

    en_cours = True
    # Juste avant le while en_cours:
    compteur_video = 0
    ralentissement = 2  # Mets 2 pour diviser la vitesse par 2, 3 pour la diviser par 3, etc.
    derniere_surface_video = None
    
    while en_cours:
        position_souris = pygame.mouse.get_pos()
        
        for evenement in pygame.event.get():
            if evenement.type == pygame.QUIT:
                quitter_jeu()
            
            if evenement.type == pygame.MOUSEMOTION:
                for bouton in boutons:
                    bouton.verifier_survol(position_souris)
                    
            if evenement.type == pygame.MOUSEBUTTONDOWN and evenement.button == 1:
                for bouton in boutons:
                    bouton.gerer_clic(position_souris)

        # --- LECTURE ET AFFICHAGE DE LA VIDÉO ---
        if video_marche:
            # On ne met à jour l'image que tous les X tours de boucle
            if compteur_video % ralentissement == 0:
                ret, frame = cap.read()
                if not ret: 
                    # Si la vidéo est terminée, on la remet au début
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                
                if ret:
                    # Convertir les couleurs et la taille
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = cv2.resize(frame, (LARGEUR, HAUTEUR))
                    # Sauvegarder la nouvelle image
                    derniere_surface_video = pygame.image.frombuffer(frame.tobytes(), frame.shape[1::-1], "RGB")
            
            # On affiche la dernière image sauvegardée à CHAQUE tour pour éviter que ça clignote
            if derniere_surface_video:
                ecran.blit(derniere_surface_video, (0, 0))
                
            compteur_video += 1
        else:
            ecran.fill((15, 20, 30))

        voile = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
        voile.fill((0, 0, 0, 110)) 
        ecran.blit(voile, (0, 0))

        if image_logo:
            rect_logo = image_logo.get_rect(center=(LARGEUR // 2, 300))
            ecran.blit(image_logo, rect_logo)
        else:
            titre = police_titre.render("ZOO ESCAPE", True, BLANC)
            ombre = police_titre.render("ZOO ESCAPE", True, NOIR)
            rect_titre = titre.get_rect(center=(LARGEUR // 2, 220))
            ecran.blit(ombre, rect_titre.move(4, 6))
            ecran.blit(titre, rect_titre)

        sous_titre = police_sous_titre.render("L'évasion ultime en coopération.", True, (220, 220, 220))
        rect_sous_titre = sous_titre.get_rect(center=(LARGEUR // 2, 400))
        ecran.blit(sous_titre, rect_sous_titre)

        for bouton in boutons:
            bouton.dessiner(ecran)

        pygame.display.flip()
        horloge.tick(FPS)

if __name__ == "__main__":
    afficher_menu()
