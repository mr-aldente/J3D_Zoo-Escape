import pygame
import random

# Constantes
LARGEUR = 1024
HAUTEUR = 768
FPS = 60

# Couleurs
BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
BLEU = (0, 0, 255)
ROUGE = (255, 60, 60)
GRIS = (50, 50, 50)

class Joueur:
    def __init__(self):
        self.rayon = 40
        self.x = 150
        self.y = HAUTEUR // 2
        self.vitesse_y = 0
        self.vitesse_max = 6
        self.acceleration = 3
        self.gravite = 6.0
        self.force_saut = -12
        self.sur_sol = False
        self.marge_bord = 80
        self.en_montee = False
        self.en_descente = False
        self.compteur_animation = 0
        self.position_actuelle = "libre"  # "haut", "bas" ou "libre"
    
    def deplacer(self, touches):
        # Montrer vers le mur du haut - reste collé jusqu'à appui sur BAS
        if touches[pygame.K_UP] or touches[pygame.K_z]:
            self.position_actuelle = "haut"
            self.en_montee = True
            self.en_descente = False
            self.y = self.marge_bord + self.rayon
            self.vitesse_y = 0
        # Descendre vers le mur du bas - reste collé jusqu'à appui sur HAUT
        elif touches[pygame.K_DOWN] or touches[pygame.K_s]:
            self.position_actuelle = "bas"
            self.en_montee = False
            self.en_descente = True
            self.y = HAUTEUR - self.marge_bord - self.rayon
            self.vitesse_y = 0
        else:
            # Pas de touche : le personnage tombe avec gravité
            if self.position_actuelle != "haut" and self.position_actuelle != "bas":
                self.en_montee = False
                self.en_descente = False
                # Appliquer la gravité si aucune touche n'est pressée
                self.vitesse_y += self.gravite
                
                # Appliquer le déplacement vertical
                self.y += self.vitesse_y
                
                # Vérifier les limites verticales
                self.sur_sol = False
                
                if self.y - self.rayon < self.marge_bord:
                    self.y = self.marge_bord + self.rayon
                    self.vitesse_y = 0
                    self.sur_sol = True
                elif self.y + self.rayon > HAUTEUR - self.marge_bord:
                    self.y = HAUTEUR - self.marge_bord - self.rayon
                    self.vitesse_y = 0
                    self.sur_sol = True
        
        # Mettre à jour l'animation
        self.compteur_animation = (self.compteur_animation + 1) % 20
    
    def dessiner(self, ecran):
        # Changer la couleur selon l'état (animation)
        if self.en_montee:
            # Vert pulsant en montée
            couleur_pulse = (0, 255 - (self.compteur_animation * 20 % 100), 100)
            couleur = couleur_pulse
        elif self.en_descente:
            # Bleu pulsant en descente
            couleur_pulse = (100, 100 + (self.compteur_animation * 20 % 100), 255)
            couleur = couleur_pulse
        else:
            # Rouge normal en chute libre
            couleur = ROUGE
        
        # Dessiner le personnage (cercle)
        pygame.draw.circle(ecran, couleur, (int(self.x), int(self.y)), self.rayon)
        # Contour noir
        pygame.draw.circle(ecran, NOIR, (int(self.x), int(self.y)), self.rayon, 3)
        
        # Yeux pour donner vie au personnage
        pygame.draw.circle(ecran, NOIR, (int(self.x - 12), int(self.y - 8)), 5)
        pygame.draw.circle(ecran, NOIR, (int(self.x + 12), int(self.y - 8)), 5)
    
    def get_rect(self):
        return pygame.Rect(self.x - self.rayon, self.y - self.rayon, 
                          self.rayon * 2, self.rayon * 2)

class Obstacle:
    def __init__(self, x, position, largeur, hauteur):
        self.x = x
        self.position = position  # "haut" ou "bas"
        self.largeur = largeur
        self.hauteur = hauteur
        
        if position == "haut":
            self.y = 80
        else:
            self.y = HAUTEUR - 80 - hauteur
    
    def deplacer(self, vitesse_defilement):
        self.x -= vitesse_defilement
    
    def dessiner(self, ecran):
        # Dessiner l'obstacle blanc avec contour noir
        pygame.draw.rect(ecran, BLANC, (int(self.x), int(self.y), self.largeur, self.hauteur))
        pygame.draw.rect(ecran, NOIR, (int(self.x), int(self.y), self.largeur, self.hauteur), 3)
    
    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.largeur, self.hauteur)
    
    def est_hors_ecran(self):
        return self.x + self.largeur < 0

class MurMort:
    def __init__(self):
        self.x = -200
        self.largeur = 200
    
    def avancer(self, vitesse_defilement):
        self.x += vitesse_defilement * 0.08  # Le mur avance moins vite que le défilement
    
    def dessiner(self, ecran):
        # Effet de dégradé pour le mur de la mort
        for i in range(self.largeur):
            alpha = int(255 * (i / self.largeur))
            couleur = (alpha // 3, 0, 0)
            pygame.draw.line(ecran, couleur, 
                           (int(self.x + i), 0), 
                           (int(self.x + i), HAUTEUR))
    
    def touche_joueur(self, joueur):
        return joueur.x - joueur.rayon < self.x + self.largeur

def creer_niveau_1():
    """Crée le niveau 1 avec des obstacles prédéfinis (pas trop difficile)"""
    obstacles = []
    
    # Niveau 1 : Introduction douce
    # Format: (distance_x, position, largeur, hauteur)
    pattern = [
        (800, "bas", 120, 150),
        (1200, "haut", 100, 120),
        (1600, "bas", 150, 180),
        (2000, "haut", 120, 140),
        (2400, "bas", 100, 160),
        (2800, "haut", 140, 150),
        (3200, "bas", 120, 170),
        (3600, "haut", 100, 130),
        (4000, "bas", 160, 150),
        (4400, "haut", 120, 140),
        (4800, "bas", 100, 160),
        (5200, "haut", 140, 150),
        (5600, "bas", 120, 140),
        (6000, "haut", 100, 160),
        (6400, "bas", 150, 150),
        (6800, "haut", 120, 140),
        (7200, "bas", 100, 170),
    ]
    
    for x, pos, largeur, hauteur in pattern:
        obstacles.append(Obstacle(x, pos, largeur, hauteur))
    
    return obstacles, 7500  # Longueur totale du niveau

def lancer_jeu(ecran):
    """Fonction principale du jeu"""
    horloge = pygame.time.Clock()
    
    # Initialisation
    joueur = Joueur()
    obstacles, longueur_niveau = creer_niveau_1()
    mur_mort = MurMort()
    
    # Variables de jeu
    vitesse_defilement = 4.0
    vitesse_initiale = 4.0
    vitesse_max = 8.0
    acceleration_vitesse = 0.002
    
    distance_parcourue = 0
    
    # Polices
    police = pygame.font.Font(None, 48)
    police_petite = pygame.font.Font(None, 32)
    
    en_cours = True
    game_over = False
    victoire = False
    
    while en_cours:
        horloge.tick(FPS)
        
        # Gestion des événements
        for evenement in pygame.event.get():
            if evenement.type == pygame.QUIT:
                return False
            if evenement.type == pygame.KEYDOWN:
                if evenement.key == pygame.K_ESCAPE:
                    return True  # Retour au menu
                if (game_over or victoire) and evenement.key == pygame.K_r:
                    return lancer_jeu(ecran)  # Recommencer
        
        if not game_over and not victoire:
            # Mise à jour
            touches = pygame.key.get_pressed()
            joueur.deplacer(touches)
            
            # Augmenter progressivement la vitesse
            if vitesse_defilement < vitesse_max:
                vitesse_defilement += acceleration_vitesse
            
            # Déplacer les obstacles
            for obstacle in obstacles:
                obstacle.deplacer(vitesse_defilement)
            
            # Avancer le mur de la mort
            mur_mort.avancer(vitesse_defilement)
            
            # Augmenter la distance parcourue
            distance_parcourue += vitesse_defilement
            
            # Vérifier collision avec obstacles
            joueur_rect = joueur.get_rect()
            for obstacle in obstacles:
                if joueur_rect.colliderect(obstacle.get_rect()):
                    # Le joueur est bloqué par l'obstacle
                    if obstacle.position == "haut":
                        joueur.y = obstacle.y + obstacle.hauteur + joueur.rayon
                        joueur.vitesse_y = max(0, joueur.vitesse_y)
                    else:
                        joueur.y = obstacle.y - joueur.rayon
                        joueur.vitesse_y = min(0, joueur.vitesse_y)
            
            # Vérifier si touché par le mur de la mort
            if mur_mort.touche_joueur(joueur):
                game_over = True
            
            # Vérifier la victoire
            if distance_parcourue >= longueur_niveau:
                victoire = True
        
        # Dessin
        # Fond blanc
        ecran.fill(BLANC)
        
        # Bords bleus
        pygame.draw.rect(ecran, BLEU, (0, 0, LARGEUR, 80))  # Bord haut
        pygame.draw.rect(ecran, BLEU, (0, HAUTEUR - 80, LARGEUR, 80))  # Bord bas
        
        # Dessiner le mur de la mort
        mur_mort.dessiner(ecran)
        
        # Dessiner les obstacles
        for obstacle in obstacles:
            obstacle.dessiner(ecran)
        
        # Dessiner le joueur
        joueur.dessiner(ecran)
        
        # Afficher la progression
        progression = min(100, int((distance_parcourue / longueur_niveau) * 100))
        texte_progression = police_petite.render(f"Progression: {progression}%", True, NOIR)
        pygame.draw.rect(ecran, BLANC, (10, 10, 250, 40))
        ecran.blit(texte_progression, (20, 20))
        
        # Barre de progression
        pygame.draw.rect(ecran, GRIS, (10, 55, 300, 20))
        pygame.draw.rect(ecran, (0, 255, 0), (10, 55, int(300 * progression / 100), 20))
        pygame.draw.rect(ecran, NOIR, (10, 55, 300, 20), 2)
        
        # Instructions
        texte_instructions = police_petite.render("HAUT/BAS ou Z/S pour bouger - ESC pour menu", True, NOIR)
        ecran.blit(texte_instructions, (LARGEUR//2 - 300, HAUTEUR - 35))
        
        # Écrans de fin
        if game_over:
            overlay = pygame.Surface((LARGEUR, HAUTEUR))
            overlay.set_alpha(200)
            overlay.fill(NOIR)
            ecran.blit(overlay, (0, 0))
            
            texte_game_over = police.render("GAME OVER!", True, ROUGE)
            texte_raison = police_petite.render("Vous avez ete rattrape par le mur !", True, BLANC)
            texte_recommencer = police_petite.render("R pour recommencer - ESC pour menu", True, BLANC)
            ecran.blit(texte_game_over, (LARGEUR//2 - 150, HAUTEUR//2 - 80))
            ecran.blit(texte_raison, (LARGEUR//2 - 250, HAUTEUR//2 - 20))
            ecran.blit(texte_recommencer, (LARGEUR//2 - 250, HAUTEUR//2 + 30))
        
        if victoire:
            overlay = pygame.Surface((LARGEUR, HAUTEUR))
            overlay.set_alpha(200)
            overlay.fill(NOIR)
            ecran.blit(overlay, (0, 0))
            
            texte_victoire = police.render("NIVEAU TERMINE !", True, (0, 255, 0))
            texte_bravo = police_petite.render("Felicitations ! Vous avez termine le niveau 1 !", True, BLANC)
            texte_recommencer = police_petite.render("R pour rejouer - ESC pour menu", True, BLANC)
            ecran.blit(texte_victoire, (LARGEUR//2 - 180, HAUTEUR//2 - 80))
            ecran.blit(texte_bravo, (LARGEUR//2 - 300, HAUTEUR//2 - 20))
            ecran.blit(texte_recommencer, (LARGEUR//2 - 220, HAUTEUR//2 + 30))
        
        pygame.display.flip()
    
    return True