import random
import pygame
import os

LARGEUR = 1024
HAUTEUR = 768
FPS = 144

BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
ROUGE = (255, 80, 80)
VERT = (80, 240, 130)
GRIS = (60, 60, 60)
BLEU_BORD = (48, 97, 228)

def creer_fond():
    fond = pygame.Surface((LARGEUR, HAUTEUR))
    for y in range(HAUTEUR):
        r = int(125 + 20 * (y / HAUTEUR))
        g = int(180 + 30 * (y / HAUTEUR))
        b = int(230 + 20 * (y / HAUTEUR))
        pygame.draw.line(fond, (r, g, b), (0, y), (LARGEUR, y))

    pygame.draw.circle(fond, (255, 220, 110), (LARGEUR - 140, 110), 62)
    pygame.draw.circle(fond, (255, 238, 170), (LARGEUR - 140, 110), 46)

    pygame.draw.ellipse(fond, (46, 130, 70), (-120, HAUTEUR // 2 + 70, LARGEUR // 2, 210))
    pygame.draw.ellipse(fond, (52, 150, 78), (250, HAUTEUR // 2 + 30, LARGEUR // 2, 250))
    pygame.draw.ellipse(fond, (38, 115, 64), (640, HAUTEUR // 2 + 50, LARGEUR // 2, 230))
    return fond

def dessiner_bords(ecran):
    pygame.draw.rect(ecran, BLEU_BORD, (0, 0, LARGEUR, 80))
    pygame.draw.rect(ecran, BLEU_BORD, (0, HAUTEUR - 80, LARGEUR, 80))

    for x in range(0, LARGEUR, 36):
        pygame.draw.rect(ecran, (80, 132, 255), (x, 63, 20, 17), border_radius=3)
        pygame.draw.rect(ecran, (80, 132, 255), (x, HAUTEUR - 80, 20, 17), border_radius=3)

def dessiner_piste(ecran, y_sol, label, couleur):
    pygame.draw.rect(ecran, (46, 130, 78), (0, y_sol + 2, LARGEUR, 55))
    pygame.draw.line(ecran, (35, 60, 35), (0, y_sol + 2), (LARGEUR, y_sol + 2), 5)
    pygame.draw.line(ecran, (210, 230, 180), (0, y_sol), (LARGEUR, y_sol), 2)
    txt = pygame.font.Font(None, 34).render(label, True, couleur)
    ecran.blit(txt, (22, y_sol - 32))

class Joueur:
    def __init__(self, x, y_sol, controles, nom, couleurs):
        self.x = x
        self.y_sol = y_sol
        self.nom = nom
        self.couleurs = couleurs
        self.controles = controles

        self.largeur = 50
        self.hauteur = 80
        self.hauteur_slide = 40

        self.y = float(y_sol - self.hauteur)
        self.vy = 0.0
        self.gravite = 0.9
        self.force_saut = -14.5

        self.sur_sol = True
        self.slide = False
        self.slide_buffer = False
        self.etat_montee = False
        self.etat_descente = False
        self.atterrissage_timer = 0
        self.anim = 0

        self.utilise_sprite = False
        self.spritesheet = None
        self.frames = []      
        self.index_frame = 0  
        self.animation_timer = 0
        self.vitesse_animation = 4 
        self.running_frames = []
        self.jumping_frames = []
        self.current_animation = []

        try:
            dossier_courant = os.path.dirname(__file__)
            chemin_image = os.path.join(dossier_courant, "assets", "animation.png")
            
            if not os.path.exists(chemin_image):
                 chemin_image = os.path.join(dossier_courant, "assets", "animation.jpg")
                 
            self.spritesheet = pygame.image.load(chemin_image).convert_alpha()
            self.echelle = 0.8  
            
            pas_x = 184            
            pas_y = 293            
            largeur_decoupe = 180  
            hauteur_decoupe = 180  
            offset_x = 50          
            offset_y = 60          
            frames_par_ligne = [6, 5, 4, 3]
            
            for j in range(len(frames_par_ligne)):
                for i in range(frames_par_ligne[j]):
                    x_img = offset_x + (i * pas_x)
                    y_img = offset_y + (j * pas_y)
                    
                    frame_brute = pygame.Surface((largeur_decoupe, hauteur_decoupe), pygame.SRCALPHA)
                    frame_brute.blit(self.spritesheet, (0, 0), pygame.Rect(x_img, y_img, largeur_decoupe, hauteur_decoupe))
                    
                    nv_largeur = int(largeur_decoupe * self.echelle)
                    nv_hauteur = int(hauteur_decoupe * self.echelle)
                    frame_agrandie = pygame.transform.scale(frame_brute, (nv_largeur, nv_hauteur))
                    self.frames.append(frame_agrandie)
                    
                    self.frame_largeur_finale = nv_largeur
                    self.frame_hauteur_finale = nv_hauteur
                    
            self.running_frames = list(range(0, 6))       
            self.jumping_frames = list(range(6, 11))      
            
            self.current_animation = self.running_frames
            self.utilise_sprite = True 
            
        except Exception as e:
            print(f"✗ Erreur animation : {e}")
            self.utilise_sprite = False

    def update(self, touches):
        jump_key, slide_key = self.controles
        sur_sol_avant = self.sur_sol

        if touches[slide_key] and not self.sur_sol:
            self.slide_buffer = True

        if touches[jump_key] and self.sur_sol and not self.slide:
            self.vy = self.force_saut
            self.sur_sol = False

        vouloir_slide = touches[slide_key] or self.slide_buffer
        self.slide = vouloir_slide and self.sur_sol

        self.vy += self.gravite
        self.y += self.vy

        hauteur_actuelle = self.hauteur_slide if self.slide else self.hauteur
        y_cible_sol = self.y_sol - hauteur_actuelle

        if self.y >= y_cible_sol:
            self.y = y_cible_sol
            self.vy = 0
            self.sur_sol = True
            if not sur_sol_avant:
                self.atterrissage_timer = 8
                self.slide_buffer = False
        else:
            self.sur_sol = False

        if self.atterrissage_timer > 0:
            self.atterrissage_timer -= 1

        self.etat_montee = self.vy < -1 and not self.sur_sol
        self.etat_descente = self.vy > 1 and not self.sur_sol

        self.anim = (self.anim + 1) % 60

        if self.utilise_sprite and len(self.current_animation) > 0:
            if self.sur_sol:
                if self.current_animation != self.running_frames:
                    self.current_animation = self.running_frames
                    self.index_frame = 0 
                    self.animation_timer = 0
            else:
                if self.current_animation != self.jumping_frames:
                    self.current_animation = self.jumping_frames
                    self.index_frame = 0
                    self.animation_timer = 0
                    
            self.animation_timer += 1
            if self.animation_timer >= self.vitesse_animation:
                self.animation_timer = 0
                self.index_frame += 1
                if self.index_frame >= len(self.current_animation):
                    self.index_frame = 0

    def get_rect(self):
        h = self.hauteur_slide if self.slide else self.hauteur
        return pygame.Rect(int(self.x), int(self.y), self.largeur, h)

    def dessiner(self, ecran):
        rect = self.get_rect()
        
        if self.utilise_sprite and len(self.frames) > 0:
            frame_a_dessiner = self.frames[self.current_animation[self.index_frame]]
            
            if self.slide:
                frame_a_dessiner = pygame.transform.scale(frame_a_dessiner, (self.frame_largeur_finale, self.frame_hauteur_finale // 2))
                y_dessin = self.y - (self.frame_hauteur_finale // 2 - self.hauteur_slide) // 2
            else:
                y_dessin = self.y - (self.frame_hauteur_finale - self.hauteur) // 2
                
            x_dessin = self.x - (self.frame_largeur_finale - self.largeur) // 2
            
            ecran.blit(frame_a_dessiner, (int(x_dessin), int(y_dessin)))
            
            txt = pygame.font.Font(None, 28).render(self.nom, True, BLANC)
            ecran.blit(txt, (rect.x, rect.y - 30))
            
        else:
            c1, c2 = self.couleurs
            ecrasement = 2 if self.atterrissage_timer > 0 else 0
            pygame.draw.ellipse(ecran, (0, 0, 0), (rect.x + 4, self.y_sol + 4, rect.width - 8, 10))
            corps_rect = rect.inflate(0, ecrasement)
            pygame.draw.rect(ecran, c1, corps_rect, border_radius=10)
            pygame.draw.rect(ecran, (25, 25, 25), rect, width=2, border_radius=10)
            if self.slide:
                tete_offset = 2
            elif self.etat_descente:
                tete_offset = -2
            elif self.etat_montee:
                tete_offset = -14
            else:
                tete_offset = -10
            tete_y = rect.y + tete_offset
            pygame.draw.circle(ecran, c2, (rect.centerx, tete_y + 12), 12)
            pygame.draw.circle(ecran, (25, 25, 25), (rect.centerx, tete_y + 12), 12, 2)
            pygame.draw.circle(ecran, BLANC, (rect.centerx - 4, tete_y + 10), 3)
            pygame.draw.circle(ecran, BLANC, (rect.centerx + 4, tete_y + 10), 3)
            pygame.draw.circle(ecran, NOIR, (rect.centerx - 4, tete_y + 10), 1)
            pygame.draw.circle(ecran, NOIR, (rect.centerx + 4, tete_y + 10), 1)
            if self.etat_descente:
                offset = 5
            elif self.etat_montee:
                offset = -5
            else:
                offset = 2 if (self.anim // 10) % 2 == 0 else -2
            pygame.draw.rect(ecran, c2, (rect.x - 5, rect.y + 14 + offset, 8, 14), border_radius=3)
            pygame.draw.rect(ecran, c2, (rect.right - 3, rect.y + 14 - offset, 8, 14), border_radius=3)
            if self.etat_descente:
                pygame.draw.line(ecran, BLANC, (rect.centerx - 12, rect.y - 10), (rect.centerx - 12, rect.y + 4), 2)
                pygame.draw.line(ecran, BLANC, (rect.centerx + 12, rect.y - 10), (rect.centerx + 12, rect.y + 4), 2)
            txt = pygame.font.Font(None, 28).render(self.nom, True, BLANC)
            ecran.blit(txt, (rect.x - 4, rect.y - 34))

class Obstacle:
    def __init__(self, x, y_sol, obstacle_type, largeur=70):
        self.x = float(x)
        self.y_sol = y_sol
        self.type = obstacle_type  
        self.largeur = largeur

        if self.type == "low":
            self.hauteur = random.randint(58, 84)
            self.y = y_sol - self.hauteur
        else:
            self.hauteur = random.randint(24, 34)
            self.y = y_sol - random.randint(86, 106)

    def deplacer(self, vitesse):
        self.x -= vitesse

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.largeur, self.hauteur)

    def dessiner(self, ecran, pulse=0):
        rect = self.get_rect()

        if self.type == "low":
            pygame.draw.rect(ecran, (128, 85, 48), rect, border_radius=6)
            pygame.draw.rect(ecran, (79, 51, 28), rect, width=2, border_radius=6)
            for i in range(rect.y + 8, rect.bottom, 10):
                pygame.draw.line(ecran, (153, 105, 62), (rect.x + 6, i), (rect.right - 6, i), 1)
        else:
            pygame.draw.rect(ecran, (88, 106, 68), rect, border_radius=6)
            pygame.draw.rect(ecran, (52, 66, 42), rect, width=2, border_radius=6)
            leaf_color = (70, 150 + pulse // 3, 75)
            pygame.draw.circle(ecran, leaf_color, (rect.x + 10, rect.centery), 8)
            pygame.draw.circle(ecran, leaf_color, (rect.right - 10, rect.centery), 8)

class Circuit:
    def __init__(self, y_sol, longueur_niveau):
        self.y_sol = y_sol
        self.longueur_niveau = longueur_niveau
        self.obstacles = []
        self._generer()

    def _generer(self):
        x = 920
        last_type = "low"
        while x < self.longueur_niveau + 1400:
            if random.random() < 0.72:
                obstacle_type = "high" if last_type == "low" else "low"
            else:
                obstacle_type = last_type

            largeur = random.randint(58, 82)
            self.obstacles.append(Obstacle(x, self.y_sol, obstacle_type, largeur))
            last_type = obstacle_type
            x += random.randint(300, 420)

    def update(self, vitesse):
        for obs in self.obstacles:
            obs.deplacer(vitesse)

    def dessiner(self, ecran, pulse):
        for obs in self.obstacles:
            if -120 < obs.x < LARGEUR + 120:
                obs.dessiner(ecran, pulse)

class JeuDeuxJoueurs:
    def __init__(self):
        self.fond = creer_fond()
        self.longueur_niveau = 9800
        self.distance = 0.0
        self.vitesse = 4.1
        self.vitesse_max = 6.8
        self.acceleration = 0.0009

        self.y_sol_j1 = int(HAUTEUR * 0.48)
        self.y_sol_j2 = int(HAUTEUR * 0.82)

        self.joueur1 = Joueur(
            x=220,
            y_sol=self.y_sol_j1,
            controles=(pygame.K_z, pygame.K_s),
            nom="J1",
            couleurs=((225, 120, 90), (255, 170, 140)),
        )
        self.joueur2 = Joueur(
            x=220,
            y_sol=self.y_sol_j2,
            controles=(pygame.K_UP, pygame.K_DOWN),
            nom="J2",
            couleurs=((90, 145, 230), (140, 195, 255)),
        )

        self.circuit_j1 = Circuit(self.y_sol_j1, self.longueur_niveau)
        self.circuit_j2 = Circuit(self.y_sol_j2, self.longueur_niveau)

        self.game_over = False
        self.victoire = False
        self.frame = 0

    def update(self, touches):
        if self.game_over or self.victoire:
            return

        self.joueur1.update(touches)
        self.joueur2.update(touches)

        if self.vitesse < self.vitesse_max:
            self.vitesse += self.acceleration

        self.circuit_j1.update(self.vitesse)
        self.circuit_j2.update(self.vitesse)
        self.distance += self.vitesse

        rect1 = self.joueur1.get_rect()
        rect2 = self.joueur2.get_rect()

        for obs in self.circuit_j1.obstacles:
            if rect1.colliderect(obs.get_rect()):
                self.game_over = True
                return

        for obs in self.circuit_j2.obstacles:
            if rect2.colliderect(obs.get_rect()):
                self.game_over = True
                return

        if self.distance >= self.longueur_niveau:
            self.victoire = True

    def dessiner(self, ecran):
        ecran.blit(self.fond, (0, 0))
        dessiner_bords(ecran)

        dessiner_piste(ecran, self.y_sol_j1, "Piste J1 (Z sauter / S glisser)", (255, 190, 170))
        dessiner_piste(ecran, self.y_sol_j2, "Piste J2 (HAUT sauter / BAS glisser)", (170, 210, 255))

        pulse = int(60 * abs(((self.frame % 40) / 20) - 1))
        self.circuit_j1.dessiner(ecran, pulse)
        self.circuit_j2.dessiner(ecran, pulse)

        self.joueur1.dessiner(ecran)
        self.joueur2.dessiner(ecran)

        progression = min(100, int((self.distance / self.longueur_niveau) * 100))
        panneau = pygame.Rect(12, 10, 390, 84)
        pygame.draw.rect(ecran, (18, 24, 36), panneau, border_radius=10)
        pygame.draw.rect(ecran, (64, 75, 100), panneau, width=2, border_radius=10)

        p_small = pygame.font.Font(None, 33)
        txt_vie = p_small.render("VIE PARTAGÉE: 1", True, BLANC)
        txt_prog = p_small.render(f"Progression: {progression}%", True, BLANC)
        ecran.blit(txt_vie, (24, 20))
        ecran.blit(txt_prog, (24, 48))

        pygame.draw.rect(ecran, GRIS, (230, 56, 160, 16), border_radius=8)
        pygame.draw.rect(ecran, VERT, (230, 56, int(160 * progression / 100), 16), border_radius=8)

        if self.game_over or self.victoire:
            overlay = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 185))
            ecran.blit(overlay, (0, 0))

            p_title = pygame.font.Font(None, 68)
            p_text = pygame.font.Font(None, 36)

            if self.game_over:
                titre = p_title.render("GAME OVER", True, ROUGE)
                txt = p_text.render("Vie partagée perdue : un des deux joueurs a touché un obstacle.", True, BLANC)
            else:
                titre = p_title.render("VICTOIRE COOP !", True, VERT)
                txt = p_text.render("Les deux joueurs ont réussi à survivre.", True, BLANC)

            aide = p_text.render("R = rejouer   |   ESC = menu", True, BLANC)
            ecran.blit(titre, (LARGEUR // 2 - 180, HAUTEUR // 2 - 90))
            ecran.blit(txt, (LARGEUR // 2 - 360, HAUTEUR // 2 - 28))
            ecran.blit(aide, (LARGEUR // 2 - 180, HAUTEUR // 2 + 26))

def lancer_jeu(ecran):
    horloge = pygame.time.Clock()
    jeu = JeuDeuxJoueurs()

    while True:
        horloge.tick(FPS)
        jeu.frame += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if (jeu.game_over or jeu.victoire) and event.key == pygame.K_r:
                    return lancer_jeu(ecran)

        touches = pygame.key.get_pressed()
        jeu.update(touches)
        jeu.dessiner(ecran)
        pygame.display.flip()
