import pygame
import sys
import jeu  # Import du fichier jeu.py
from pathlib import Path

pygame.init()
pygame.mixer.init()

# Configuration des chemins relatifs
ASSETS_DIR = Path(__file__).parent / "assets"

LARGEUR = 1024
HAUTEUR = 768
FPS = 60

BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
VIOLET = (138, 43, 226)
ORANGE = (255, 140, 0)
JAUNE = (255, 215, 0)
VERT = (34, 139, 34)
BLEU_CLAIR = (135, 206, 235)
ROSE_ARCADE = (255, 20, 147)
CYAN_ARCADE = (0, 255, 255)
LIME = (50, 205, 50)

class Bouton:
    def __init__(self, x, y, largeur, hauteur, texte, couleur_fond, couleur_bordure):
        self.rect = pygame.Rect(x, y, largeur, hauteur)
        self.texte = texte
        self.couleur_fond = couleur_fond
        self.couleur_bordure = couleur_bordure
        self.survole = False
        self.scale = 1.0
    
    def dessiner(self, ecran, police):
        if self.survole:
            self.scale = min(self.scale + 0.05, 1.15)
        else:
            self.scale = max(self.scale - 0.05, 1.0)
        
        rect_dessine = self.rect.copy()
        if self.scale > 1.0:
            inflation = int((self.scale - 1.0) * 60)
            rect_dessine.inflate_ip(inflation, inflation)
        
        # Bordure extérieure noire - style arcade
        pygame.draw.rect(ecran, NOIR, rect_dessine, border_radius=15, width=8)
        
        # Ombre intérieure pour effet 3D
        ombre_rect = rect_dessine.inflate(-16, -16)
        pygame.draw.rect(ecran, (0, 0, 0), ombre_rect, border_radius=8, width=4)
        
        # Remplissage principal
        rect_interieur = rect_dessine.inflate(-20, -20)
        pygame.draw.rect(ecran, self.couleur_fond, rect_interieur, border_radius=10)
        
        # Highlight supérieur pour effet 3D arcade
        rect_highlight = rect_interieur.copy()
        rect_highlight.height = rect_highlight.height // 3
        highlight_color = tuple(min(c + 80, 255) for c in self.couleur_fond)
        pygame.draw.rect(ecran, highlight_color, rect_highlight, border_radius=8)
        
        # Texte avec ombre portée
        texte_ombre = police.render(self.texte, True, NOIR)
        texte_rect_ombre = texte_ombre.get_rect(center=(rect_dessine.centerx + 4, rect_dessine.centery + 4))
        ecran.blit(texte_ombre, texte_rect_ombre)
        
        # Texte principal en blanc avec effet de glow
        texte_surface = police.render(self.texte, True, BLANC)
        texte_rect = texte_surface.get_rect(center=rect_dessine.center)
        ecran.blit(texte_surface, texte_rect)
    
    def verifier_survol(self, pos_souris):
        self.survole = self.rect.collidepoint(pos_souris)
        return self.survole
    
    def est_clique(self, pos_souris):
        return self.rect.collidepoint(pos_souris)

class MenuPrincipal:
    def __init__(self):
        self.ecran = pygame.display.set_mode((LARGEUR, HAUTEUR))
        pygame.display.set_caption("Zoo Escape")
        self.horloge = pygame.time.Clock()
        
        self.charger_image_fond()
        self.charger_musique()
        
        self.police_titre = pygame.font.Font(None, 120)
        self.police_bouton = pygame.font.Font(None, 55)
        self.police_credits = pygame.font.Font(None, 35)
        
        largeur_bouton = 280
        hauteur_bouton = 80
        y_centre = 580
        espacement = 30
        largeur_totale = largeur_bouton * 3 + espacement * 2
        x_debut = (LARGEUR - largeur_totale) // 2
        
        self.bouton_jouer = Bouton(
            x_debut, y_centre, largeur_bouton, hauteur_bouton,
            "JOUER", LIME, CYAN_ARCADE
        )
        self.bouton_options = Bouton(
            x_debut + largeur_bouton + espacement, y_centre, largeur_bouton, hauteur_bouton,
            "OPTIONS", JAUNE, ROSE_ARCADE
        )
        self.bouton_quitter = Bouton(
            x_debut + (largeur_bouton + espacement) * 2, y_centre, largeur_bouton, hauteur_bouton,
            "QUITTER", ORANGE, (255, 0, 127)
        )
        
        self.boutons = [self.bouton_jouer, self.bouton_options, self.bouton_quitter]
    
    def charger_image_fond(self):
        nom_fichier = ASSETS_DIR / "zoo_escape_bg.png"

        try:
            print(f"Tentative de chargement de l'image : {nom_fichier}")
            self.image_fond = pygame.image.load(str(nom_fichier))
            self.image_fond = pygame.transform.scale(self.image_fond, (LARGEUR, HAUTEUR))
            self.a_image_fond = True
            print("✓ Image de fond chargée avec succès !")
        except FileNotFoundError:
            print(f"✗ Image '{nom_fichier}' non trouvée dans le dossier.")
            print("  Création d'un fond par défaut...")
            self.a_image_fond = False
            self.creer_fond_default()
        except Exception as e:
            print(f"✗ Erreur lors du chargement de l'image : {e}")
            print("  Création d'un fond par défaut...")
            self.a_image_fond = False
            self.creer_fond_default()
    
    def charger_musique(self):
        nom_fichier = ASSETS_DIR / "milktruck 110bpm.mp3"
        
        try:
            print(f"Tentative de chargement de la musique : {nom_fichier}")
            pygame.mixer.music.load(str(nom_fichier))
            pygame.mixer.music.play(-1)  
            print("✓ Musique chargée et lancée avec succès !")
        except FileNotFoundError:
            print(f"✗ Fichier audio '{nom_fichier}' non trouvé dans le dossier.")
        except Exception as e:
            print(f"✗ Erreur lors du chargement de la musique : {e}")
    
    def creer_fond_default(self):
        self.image_fond = pygame.Surface((LARGEUR, HAUTEUR))

        for y in range(HAUTEUR // 2):
            ratio = y / (HAUTEUR // 2)
            r = int(135 + (100 - 135) * ratio)
            g = int(206 + (180 - 206) * ratio)
            b = int(235 + (200 - 235) * ratio)
            pygame.draw.line(self.image_fond, (r, g, b), (0, y), (LARGEUR, y))

        pygame.draw.rect(self.image_fond, (34, 139, 34), (0, HAUTEUR // 2, LARGEUR, HAUTEUR // 2))

        pygame.draw.ellipse(self.image_fond, (210, 180, 140), 
                          (LARGEUR // 4, HAUTEUR // 2, LARGEUR // 2, HAUTEUR // 3))

        for i in range(6):
            x = i * 200 + 50
            y = HAUTEUR // 2 - 80
            pygame.draw.rect(self.image_fond, (139, 69, 19), (x, y, 30, 80))
            pygame.draw.circle(self.image_fond, (0, 128, 0), (x + 15, y), 50)
            pygame.draw.circle(self.image_fond, (34, 139, 34), (x - 20, y + 20), 40)
            pygame.draw.circle(self.image_fond, (50, 205, 50), (x + 40, y + 20), 40)
    
    def dessiner_titre_pixel_art(self):
        titre_ombre = self.police_titre.render("ZOO ESCAPE", True, NOIR)
        rect_ombre = titre_ombre.get_rect(center=(LARGEUR // 2 + 6, 106))
        self.ecran.blit(titre_ombre, rect_ombre)

        titre_bordure = self.police_titre.render("ZOO ESCAPE", True, VIOLET)
        rect_bordure = titre_bordure.get_rect(center=(LARGEUR // 2 + 3, 103))
        self.ecran.blit(titre_bordure, rect_bordure)

        titre_orange = self.police_titre.render("ZOO ESCAPE", True, ORANGE)
        rect_orange = titre_orange.get_rect(center=(LARGEUR // 2, 100))
        self.ecran.blit(titre_orange, rect_orange)

        titre_jaune = self.police_titre.render("ZOO ESCAPE", True, JAUNE)
        titre_jaune.set_alpha(150)
        rect_jaune = titre_jaune.get_rect(center=(LARGEUR // 2 - 2, 98))
        self.ecran.blit(titre_jaune, rect_jaune)
    
    def gerer_evenements(self):
        for evenement in pygame.event.get():
            if evenement.type == pygame.QUIT:
                return "quitter"
            
            if evenement.type == pygame.MOUSEBUTTONDOWN:
                pos_souris = pygame.mouse.get_pos()
                
                if self.bouton_jouer.est_clique(pos_souris):
                    return "jouer"
                elif self.bouton_options.est_clique(pos_souris):
                    return "options"
                elif self.bouton_quitter.est_clique(pos_souris):
                    return "quitter"
        
        return None
    
    def executer(self):
        print("Démarrage du menu Zoo Escape...")
        en_cours = True

        while en_cours:
            self.horloge.tick(FPS)

            action = self.gerer_evenements()

            if action == "quitter":
                print("Fermeture du menu...")
                en_cours = False
            elif action == "jouer":
                print("==> Lancement du jeu...")
                # Lancer le jeu
                jeu.lancer_jeu(self.ecran)
                # Une fois le jeu terminé, on revient au menu
            elif action == "options":
                print("==> Ouverture des options...")

            pos_souris = pygame.mouse.get_pos()
            for bouton in self.boutons:
                bouton.verifier_survol(pos_souris)

            self.ecran.blit(self.image_fond, (0, 0))

            overlay = pygame.Surface((LARGEUR, HAUTEUR))
            overlay.set_alpha(60)
            overlay.fill(NOIR)
            self.ecran.blit(overlay, (0, 0))

            self.dessiner_titre_pixel_art()

            for bouton in self.boutons:
                bouton.dessiner(self.ecran, self.police_bouton)

            credits = self.police_credits.render("Protocol Coop - 2025", True, BLANC)
            credits_ombre = self.police_credits.render("Protocol Coop - 2025", True, NOIR)
            self.ecran.blit(credits_ombre, (LARGEUR // 2 - 138, HAUTEUR - 28))
            self.ecran.blit(credits, (LARGEUR // 2 - 140, HAUTEUR - 30))

            pygame.display.flip()

        pygame.quit()
        sys.exit()

# Lancement du menu
if __name__ == "__main__":
    try:
        menu = MenuPrincipal()
        menu.executer()
    except Exception as e:
        print(f"ERREUR CRITIQUE: {e}")
        import traceback
        traceback.print_exc()
        input("Appuyez sur Entree pour fermer...")