import math
import random
import os
from array import array
from collections import deque

import pygame

# Constantes (peuvent être écrasées depuis menu.py)
LARGEUR = 1024
HAUTEUR = 768
FPS = 144

# Couleurs
BLANC      = (255, 255, 255)
NOIR       = (0,   0,   0)
ROUGE      = (255, 80,  80)
ROUGE_VIF  = (220, 40,  40)
VERT       = (80,  240, 130)
GRIS       = (60,  60,  60)
JAUNE      = (255, 215, 0)
ORANGE     = (255, 140, 0)
CYAN       = (0,   255, 255)
BLEU_BORD  = (48,  97,  228)
VIOLET     = (138, 43,  226)
ROSE       = (255, 20,  147)

# ──────────────────────────────────────────────
#  NIVEAUX
# ──────────────────────────────────────────────
NIVEAUX = {
    0: {  # Niveau 0: Test animations (sans obstacles)
        "nom": "ANIMATION TEST",
        "longueur": 6000,
        "vitesse": 3.5,
        "vitesse_max": 5.0,
        "acceleration": 0.0006,
        "gap_min": 300,
        "gap_max": 420,
        "generer_obstacles": False,
    },
    1: {  # Niveau 1: Facile
        "nom": "Level 1 - EASY",
        "longueur": 9800,
        "vitesse": 4.1,
        "vitesse_max": 6.8,
        "acceleration": 0.0009,
        "gap_min": 350,
        "gap_max": 480,
        "generer_obstacles": True,
    },
    2: {  # Niveau 2: Moyen
        "nom": "Level 2 - MEDIUM",
        "longueur": 11000,
        "vitesse": 4.5,
        "vitesse_max": 7.2,
        "acceleration": 0.0011,
        "gap_min": 280,
        "gap_max": 400,
        "generer_obstacles": True,
    },
    3: {  # Niveau 3: Difficile
        "nom": "Level 3 - HARD",
        "longueur": 12500,
        "vitesse": 5.0,
        "vitesse_max": 8.0,
        "acceleration": 0.0013,
        "gap_min": 220,
        "gap_max": 350,
        "generer_obstacles": True,
    },
}

# ──────────────────────────────────────────────
#  Polices pré-créées (évite de les recréer à chaque frame)
# ──────────────────────────────────────────────
_POLICES: dict = {}
_VOLUME_EFFETS = 0.7


class GestionnaireSons:
    def __init__(self):
        self.actif = pygame.mixer.get_init() is not None
        self.sons = {}
        if self.actif:
            self._creer_sons()
            self.set_volume(_VOLUME_EFFETS)

    def _generer_tonalite(self, frequence, duree=0.16, volume=0.35, forme="sine", glide=0.0):
        if not self.actif:
            return None
        sample_rate = 22050
        n_samples = max(1, int(sample_rate * duree))
        amplitude = int(32767 * max(0.0, min(1.0, volume)))
        buffer = array("h")
        for index in range(n_samples):
            t = index / sample_rate
            freq = frequence + glide * (index / n_samples)
            angle = 2 * math.pi * freq * t
            if forme == "square":
                valeur = 1.0 if math.sin(angle) >= 0 else -1.0
            elif forme == "triangle":
                valeur = 2 * abs(2 * ((t * freq) % 1) - 1) - 1
            else:
                valeur = math.sin(angle)
            enveloppe = min(1.0, index / max(1, n_samples * 0.08)) * max(0.0, 1 - index / n_samples)
            buffer.append(int(amplitude * valeur * enveloppe))
        return pygame.mixer.Sound(buffer=buffer.tobytes())

    def _creer_sons(self):
        self.sons = {
            "jump": self._generer_tonalite(620, 0.12, 0.28, "triangle", glide=120),
            "hit": self._generer_tonalite(180, 0.22, 0.32, "square", glide=-60),
            "win": self._generer_tonalite(760, 0.45, 0.25, "sine", glide=180),
            "lose": self._generer_tonalite(240, 0.5, 0.28, "triangle", glide=-120),
            "countdown": self._generer_tonalite(540, 0.09, 0.18, "sine", glide=40),
        }

    def play(self, nom):
        son = self.sons.get(nom)
        if self.actif and son is not None:
            son.play()

    def set_volume(self, volume):
        global _VOLUME_EFFETS
        _VOLUME_EFFETS = max(0.0, min(1.0, volume))
        for son in self.sons.values():
            if son is not None:
                son.set_volume(_VOLUME_EFFETS)


SONS = GestionnaireSons()

def police(taille: int) -> pygame.font.Font:
    if taille not in _POLICES:
        _POLICES[taille] = pygame.font.Font(None, taille)
    return _POLICES[taille]


def configurer_audio(volume_sons: float):
    SONS.set_volume(volume_sons)


# ──────────────────────────────────────────────
#  PARTICULES
# ──────────────────────────────────────────────
class Particule:
    __slots__ = ("x", "y", "vx", "vy", "vie", "vie_max", "couleur", "rayon")

    def __init__(self, x, y, couleur):
        self.x = float(x)
        self.y = float(y)
        angle = random.uniform(0, math.tau)
        vitesse = random.uniform(1.5, 5.5)
        self.vx = math.cos(angle) * vitesse
        self.vy = math.sin(angle) * vitesse - random.uniform(0, 2)
        self.vie = random.randint(18, 34)
        self.vie_max = self.vie
        self.couleur = couleur
        self.rayon = random.randint(3, 7)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.22
        self.vie -= 1

    def dessiner(self, ecran):
        alpha = max(0, int(255 * self.vie / self.vie_max))
        surf = pygame.Surface((self.rayon * 2, self.rayon * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.couleur, alpha), (self.rayon, self.rayon), self.rayon)
        ecran.blit(surf, (int(self.x) - self.rayon, int(self.y) - self.rayon))


# ──────────────────────────────────────────────
#  PISTE SOL
# ──────────────────────────────────────────────
class PisteSol:
    def __init__(self, y_sol):
        self.y_sol = y_sol
        self.offset_anim = 0.0

    def update(self, vitesse):
        self.offset_anim += vitesse * 0.25

    def dessiner(self, ecran):
        # Ligne de sol principale (légèrement épaisse)
        pygame.draw.line(ecran, (100, 200, 100), (0, self.y_sol), (LARGEUR, self.y_sol), 3)
        
        # Motif de carrés animé
        carreau = 48
        off = int(self.offset_anim) % carreau
        for x in range(-carreau + off, LARGEUR + carreau, carreau):
            pygame.draw.line(ecran, (60, 120, 60), (x, self.y_sol - 8), (x, self.y_sol + 8), 1)


# ──────────────────────────────────────────────
#  SKYBOX (deux images: skybox0 en bas, Skybox1 en haut)
# ──────────────────────────────────────────────
class Skybox:
    def __init__(self):
        self.skybox0 = None
        self.skybox1 = None
        self._charger_images()

    def _charger_images(self):
        try:
            chemin_base = os.path.join(os.path.dirname(__file__), "assets", "Skybox_0000")
            chemin0 = os.path.join(chemin_base, "skybox0.png")
            chemin1 = os.path.join(chemin_base, "Skybox1.png")
            
            if os.path.exists(chemin0):
                self.skybox0 = pygame.image.load(chemin0)
                self.skybox0 = pygame.transform.scale(self.skybox0, (LARGEUR, HAUTEUR // 2))
            
            if os.path.exists(chemin1):
                self.skybox1 = pygame.image.load(chemin1)
                self.skybox1 = pygame.transform.scale(self.skybox1, (LARGEUR, HAUTEUR // 2))
        except Exception as e:
            print(f"Erreur chargement skybox: {e}")

    def update(self, vitesse_jeu):
        pass

    def dessiner(self, ecran):
        if self.skybox1:
            ecran.blit(self.skybox1, (0, 0))
        if self.skybox0:
            ecran.blit(self.skybox0, (0, HAUTEUR // 2))


# ──────────────────────────────────────────────
#  DÉCOR DE BORDS + PISTES
# ──────────────────────────────────────────────
def dessiner_bords(ecran):
    pygame.draw.rect(ecran, BLEU_BORD, (0, 0, LARGEUR, 80))
    pygame.draw.rect(ecran, BLEU_BORD, (0, HAUTEUR - 80, LARGEUR, 80))
    for x in range(0, LARGEUR, 36):
        pygame.draw.rect(ecran, (80, 132, 255), (x, 63, 20, 17), border_radius=3)
        pygame.draw.rect(ecran, (80, 132, 255), (x, HAUTEUR - 80, 20, 17), border_radius=3)


def dessiner_piste(ecran, y_sol, label, couleur, offset_anim=0):
    pygame.draw.rect(ecran, (46, 130, 78), (0, y_sol + 2, LARGEUR, 55))
    pygame.draw.line(ecran, (35, 60, 35),    (0, y_sol + 2), (LARGEUR, y_sol + 2), 5)
    pygame.draw.line(ecran, (210, 230, 180), (0, y_sol),     (LARGEUR, y_sol),     2)
    carreau = 48
    off = int(offset_anim) % carreau
    for x in range(-carreau + off, LARGEUR + carreau, carreau):
        pygame.draw.line(ecran, (35, 105, 60), (x, y_sol + 4), (x, y_sol + 54), 1)
    txt = police(34).render(label, True, couleur)
    ecran.blit(txt, (22, y_sol - 32))


# ──────────────────────────────────────────────
#  JOUEUR avec ANIMATION SPRITE
# ──────────────────────────────────────────────
class Joueur:
    VIES_MAX = 3

    def __init__(self, x, y_sol, controles, nom, couleurs):
        self.x = float(x)
        self.y_sol = y_sol
        self.nom = nom
        self.couleurs = couleurs
        self.controles = controles

        self.largeur = 48
        self.hauteur = 66
        self.hauteur_slide = 36

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

        self.vies = self.VIES_MAX
        self.invincible = 0
        self.flash = 0
        self.en_vie = True

        # ANIMATION SPRITE
        self.utilise_sprite = False
        self.spritesheet = None
        self.frames = []
        self.index_frame = 0  
        self.animation_timer = 0
        self.vitesse_animation = 5
        self.vitesse_animation_slide = 2
        self.running_frames = []
        self.jumping_frames = []
        self.sliding_frames = []
        self.current_animation = []
        self.vient_de_sauter = False
        self.jump_sequence_index = 0

        # Anti-spam actions (pour lisibilité des animations)
        self.cooldown_saut = 0
        self.cooldown_slide = 0
        self.slide_timer = 0
        self.slide_duree_min = 14
        self.saut_appui_precedent = False
        self.slide_appui_precedent = False

        self._charger_sprite()

    @staticmethod
    def _est_pixel_sprite(couleur):
        r, g, b, a = couleur
        if a == 0:
            return False
        if r < 12 and g < 12 and b < 12:
            return False
        if g > 150 and b > 150 and r < 210:
            return False
        return True

    def _nettoyer_frame(self, frame_brute):
        largeur, hauteur = frame_brute.get_size()
        min_x, min_y = largeur, hauteur
        max_x, max_y = -1, -1

        for y in range(hauteur):
            for x in range(largeur):
                if self._est_pixel_sprite(frame_brute.get_at((x, y))):
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if max_x < min_x or max_y < min_y:
            return None

        marge = 6
        min_x = max(0, min_x - marge)
        min_y = max(0, min_y - marge)
        max_x = min(largeur - 1, max_x + marge)
        max_y = min(hauteur - 1, max_y + marge)

        zone = pygame.Rect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
        frame = pygame.Surface(zone.size, pygame.SRCALPHA)
        frame.blit(frame_brute, (0, 0), zone)

        for y in range(frame.get_height()):
            for x in range(frame.get_width()):
                r, g, b, a = frame.get_at((x, y))
                if a == 0:
                    continue
                if g > 150 and b > 150 and r < 210:
                    frame.set_at((x, y), (0, 0, 0, 0))
        return frame

    def _nettoyer_frame_alpha(self, frame_brute):
        frame_brute = frame_brute.copy()
        self._supprimer_fond_noir_connecte_bords(frame_brute)

        largeur, hauteur = frame_brute.get_size()
        min_x, min_y = largeur, hauteur
        max_x, max_y = -1, -1

        for y in range(hauteur):
            for x in range(largeur):
                if frame_brute.get_at((x, y)).a > 0:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if max_x < min_x or max_y < min_y:
            return None

        marge = 3
        min_x = max(0, min_x - marge)
        min_y = max(0, min_y - marge)
        max_x = min(largeur - 1, max_x + marge)
        max_y = min(hauteur - 1, max_y + marge)

        zone = pygame.Rect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
        frame = pygame.Surface(zone.size, pygame.SRCALPHA)
        frame.blit(frame_brute, (0, 0), zone)
        return frame

    def _supprimer_fond_noir_connecte_bords(self, surface):
        largeur, hauteur = surface.get_size()
        if largeur <= 0 or hauteur <= 0:
            return

        def est_noir_fond(c):
            r, g, b, a = c
            return a > 0 and r < 35 and g < 35 and b < 35

        visite = [[False] * hauteur for _ in range(largeur)]
        q = deque()

        for x in range(largeur):
            for y in (0, hauteur - 1):
                if not visite[x][y] and est_noir_fond(surface.get_at((x, y))):
                    visite[x][y] = True
                    q.append((x, y))

        for y in range(hauteur):
            for x in (0, largeur - 1):
                if not visite[x][y] and est_noir_fond(surface.get_at((x, y))):
                    visite[x][y] = True
                    q.append((x, y))

        while q:
            x, y = q.popleft()
            surface.set_at((x, y), (0, 0, 0, 0))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < largeur and 0 <= ny < hauteur and not visite[nx][ny]:
                    if est_noir_fond(surface.get_at((nx, ny))):
                        visite[nx][ny] = True
                        q.append((nx, ny))

    def _extraire_rangee(self, zone_x, zone_y, zone_largeur, zone_hauteur, nombre_frames, hauteur_cible):
        frames = []
        largeur_cellule = zone_largeur / nombre_frames
        for index in range(nombre_frames):
            x0 = round(zone_x + index * largeur_cellule)
            x1 = round(zone_x + (index + 1) * largeur_cellule)
            rect = pygame.Rect(x0, zone_y, x1 - x0, zone_hauteur)
            frame_brute = pygame.Surface(rect.size, pygame.SRCALPHA)
            frame_brute.blit(self.spritesheet, (0, 0), rect)
            frame = self._nettoyer_frame(frame_brute)
            if frame is None:
                continue
            ratio = hauteur_cible / max(1, frame.get_height())
            largeur_cible = max(1, int(frame.get_width() * ratio))
            frames.append(pygame.transform.smoothscale(frame, (largeur_cible, hauteur_cible)))
        return frames

    def _extraire_depuis_bande(self, surface, nombre_frames, hauteur_cible, ratio_hauteur=1.0):
        frames = []
        largeur, hauteur = surface.get_size()
        hauteur_zone = max(1, int(hauteur * ratio_hauteur))
        largeur_cellule = largeur / nombre_frames

        for index in range(nombre_frames):
            x0 = round(index * largeur_cellule)
            x1 = round((index + 1) * largeur_cellule)
            rect = pygame.Rect(x0, 0, x1 - x0, hauteur_zone)
            frame_brute = pygame.Surface(rect.size, pygame.SRCALPHA)
            frame_brute.blit(surface, (0, 0), rect)
            frame = self._nettoyer_frame_alpha(frame_brute)
            if frame is None:
                continue
            ratio = hauteur_cible / max(1, frame.get_height())
            largeur_cible = max(1, int(frame.get_width() * ratio))
            frames.append(pygame.transform.smoothscale(frame, (largeur_cible, hauteur_cible)))
        return frames

    def _normaliser_frames(self, frames, hauteur_cible=120):
        """Normaliser la taille de toutes les frames pour qu'elles aient la même hauteur et largeur"""
        if not frames:
            return frames
        
        # Calculer la largeur maximale en redimensionnant toutes à la hauteur cible
        largeur_max = 0
        frames_redimensionnees = []
        
        for frame in frames:
            if frame.get_height() > 0:
                ratio = hauteur_cible / frame.get_height()
                largeur = max(1, int(frame.get_width() * ratio))
                frame_resized = pygame.transform.smoothscale(frame, (largeur, hauteur_cible))
                frames_redimensionnees.append(frame_resized)
                largeur_max = max(largeur_max, largeur)
        
        # Créer les frames finales avec padding pour avoir la même taille
        frames_normalisees = []
        for frame_resized in frames_redimensionnees:
            # Créer une surface avec la taille cible (largeur_max × hauteur_cible)
            frame_final = pygame.Surface((largeur_max, hauteur_cible), pygame.SRCALPHA)
            # Centrer le sprite horizontalement
            x_offset = (largeur_max - frame_resized.get_width()) // 2
            frame_final.blit(frame_resized, (x_offset, 0))
            frames_normalisees.append(frame_final)
        
        return frames_normalisees

    def _charger_frames_depuis_dossier(self, dossier, nombre_attendu, hauteur_cible):
        if not os.path.isdir(dossier):
            return []

        def extraire_indice(nom_fichier):
            chiffres = "".join(caractere for caractere in nom_fichier if caractere.isdigit())
            return int(chiffres) if chiffres else 999

        fichiers_png = [nom for nom in os.listdir(dossier) if nom.lower().endswith(".png")]
        fichiers_png.sort(key=lambda nom: (extraire_indice(nom), nom.lower()))

        frames = []
        for nom in fichiers_png:
            chemin_frame = os.path.join(dossier, nom)
            frame = pygame.image.load(chemin_frame).convert_alpha()
            frame = self._nettoyer_frame_alpha(frame)
            if frame is not None:
                frames.append(frame)

        if len(frames) < nombre_attendu:
            return []
        return self._normaliser_frames(frames[:nombre_attendu], hauteur_cible=hauteur_cible)

    def _charger_sprite(self):
        try:
            dossier_courant = os.path.dirname(__file__)
            dossier_fox = os.path.join(dossier_courant, "assets", "Fox")
            dossier_courir = os.path.join(dossier_fox, "Courir_animation")
            dossier_saut = os.path.join(dossier_fox, "Saut_animation")
            dossier_accroupi = os.path.join(dossier_fox, "accroupie_animation")

            self.running_frames = self._charger_frames_depuis_dossier(dossier_courir, 6, 120)
            self.jumping_frames = self._charger_frames_depuis_dossier(dossier_saut, 5, 126)
            self.sliding_frames = self._charger_frames_depuis_dossier(dossier_accroupi, 5, 92)

            if self.running_frames:
                if not self.jumping_frames:
                    chemin_jump = os.path.join(dossier_courant, "assets", "Jumping_animation.png")
                    if os.path.exists(chemin_jump):
                        jump_surface = pygame.image.load(chemin_jump).convert_alpha()
                        jump_6 = self._extraire_depuis_bande(jump_surface, 6, 126, ratio_hauteur=1.0)
                        jump_5 = self._extraire_depuis_bande(jump_surface, 5, 126, ratio_hauteur=1.0)
                        self.jumping_frames = jump_5 if len(jump_5) >= 5 else jump_6

                if not self.jumping_frames:
                    self.jumping_frames = self.running_frames[:]
                if not self.sliding_frames:
                    self.sliding_frames = self.running_frames[:3]

                if self.sliding_frames:
                    self.slide_duree_min = max(
                        28,
                        int(len(self.sliding_frames) * self.vitesse_animation_slide * 1.5),
                    )

                self.frames = self.running_frames + self.jumping_frames + self.sliding_frames
                if self.running_frames and self.jumping_frames:
                    self.current_animation = self.running_frames
                    self.utilise_sprite = True
                    return
            
            # Fallback: Charger depuis Running_animation.png et Jumping_animation.png
            chemin_run = os.path.join(dossier_courant, "assets", "Running_animation.png")
            chemin_jump = os.path.join(dossier_courant, "assets", "Jumping_animation.png")

            if os.path.exists(chemin_run) and os.path.exists(chemin_jump):
                run_surface = pygame.image.load(chemin_run).convert_alpha()
                jump_surface = pygame.image.load(chemin_jump).convert_alpha()

                self.running_frames = self._extraire_depuis_bande(run_surface, 6, 120, ratio_hauteur=1.0)
                jump_6 = self._extraire_depuis_bande(jump_surface, 6, 126, ratio_hauteur=1.0)
                jump_5 = self._extraire_depuis_bande(jump_surface, 5, 126, ratio_hauteur=1.0)
                self.jumping_frames = jump_5 if len(jump_5) >= 5 else jump_6

                if not self.jumping_frames:
                    self.jumping_frames = self.running_frames[:]
                if not self.sliding_frames:
                    self.sliding_frames = self.running_frames[:3]

                if self.sliding_frames:
                    self.slide_duree_min = max(
                        28,
                        int(len(self.sliding_frames) * self.vitesse_animation_slide * 1.5),
                    )

                self.frames = self.running_frames + self.jumping_frames + self.sliding_frames
                if self.running_frames and self.jumping_frames:
                    self.current_animation = self.running_frames
                    self.utilise_sprite = True
                    return

            # Fallback: Charger depuis animation.png (ancienne format)
            chemin_image = os.path.join(dossier_courant, "assets", "animation.png")
            if not os.path.exists(chemin_image):
                chemin_image = os.path.join(dossier_courant, "assets", "animation.jpg")

            if os.path.exists(chemin_image):
                self.spritesheet = pygame.image.load(chemin_image).convert_alpha()
                self.running_frames = self._extraire_rangee(47, 63, 1095, 166, 6, 112)
                self.jumping_frames = self._extraire_rangee(49, 313, 1098, 292, 5, 118)
                self.sliding_frames = self._extraire_rangee(44, 710, 1103, 173, 4, 72)

                if self.sliding_frames:
                    self.slide_duree_min = max(
                        28,
                        int(len(self.sliding_frames) * self.vitesse_animation_slide * 1.5),
                    )

                self.frames = self.running_frames + self.jumping_frames + self.sliding_frames
                if self.running_frames:
                    self.current_animation = self.running_frames
                    self.utilise_sprite = True
        except Exception as e:
            print(f"✗ Erreur animation : {e}")
            self.utilise_sprite = False

    def touche(self):
        if self.invincible > 0:
            return False
        self.vies -= 1
        self.invincible = 90
        self.flash = 18
        if self.vies <= 0:
            self.en_vie = False
        return True

    def update(self, touches):
        if not self.en_vie:
            return
        self.vient_de_sauter = False
        jump_key, slide_key = self.controles
        sur_sol_avant = self.sur_sol

        if self.cooldown_saut > 0:
            self.cooldown_saut -= 1
        if self.cooldown_slide > 0:
            self.cooldown_slide -= 1

        saut_appuye = touches[jump_key]
        slide_appuye = touches[slide_key]
        declenche_saut = saut_appuye and not self.saut_appui_precedent
        declenche_slide = slide_appuye and not self.slide_appui_precedent

        if slide_appuye and not self.sur_sol:
            self.slide_buffer = True

        if declenche_saut and self.sur_sol and not self.slide and self.cooldown_saut == 0:
            self.vy = self.force_saut
            self.sur_sol = False
            self.vient_de_sauter = True
            self.cooldown_saut = 12

        vouloir_slide = slide_appuye or self.slide_buffer
        if self.sur_sol:
            if (
                not self.slide
                and vouloir_slide
                and self.cooldown_slide == 0
                and (declenche_slide or self.slide_buffer)
            ):
                self.slide = True
                self.y = float(self.y_sol - self.hauteur_slide)  # snap immédiat → évite sur_sol=False
                self.slide_timer = self.slide_duree_min
                self.cooldown_slide = 12
                self.slide_buffer = False
            elif self.slide:
                if self.slide_timer > 0:
                    self.slide_timer -= 1
                if self.slide_timer <= 0 and not slide_appuye:
                    self.slide = False
            else:
                self.slide = False
        else:
            self.slide = False

        self.vy += self.gravite
        self.y  += self.vy

        hauteur_actuelle = self.hauteur_slide if self.slide else self.hauteur
        y_cible_sol = self.y_sol - hauteur_actuelle

        if self.y >= y_cible_sol:
            self.y = y_cible_sol
            self.vy = 0
            self.sur_sol = True
            if not sur_sol_avant:
                self.atterrissage_timer = 8
                # On garde éventuellement un slide buffer pour déclencher un accroupi
                # juste après l'atterrissage si le joueur avait appuyé en l'air.
        else:
            self.sur_sol = False

        if self.atterrissage_timer > 0:
            self.atterrissage_timer -= 1
        if self.invincible > 0:
            self.invincible -= 1
        if self.flash > 0:
            self.flash -= 1

        self.etat_montee   = self.vy < -1 and not self.sur_sol
        self.etat_descente = self.vy > 1  and not self.sur_sol
        self.anim = (self.anim + 1) % 60

        # Animation sprite
        if self.utilise_sprite and len(self.current_animation) > 0:
            if self.slide and self.sliding_frames:
                if self.current_animation is not self.sliding_frames:
                    self.current_animation = self.sliding_frames
                    self.index_frame = 0
                    self.animation_timer = 0
                else:
                    self.animation_timer += 1
                    if self.animation_timer >= self.vitesse_animation_slide:
                        self.animation_timer = 0
                        if self.index_frame < len(self.sliding_frames) - 1:
                            self.index_frame += 1  # joue jusqu'à la dernière frame, puis freeze
            elif self.sur_sol:
                if self.current_animation is not self.running_frames:
                    self.current_animation = self.running_frames
                    self.index_frame = 0
                    self.animation_timer = 0
                    self.jump_sequence_index = 0
                else:
                    # Animation normale pour la course
                    seuil_animation = self.vitesse_animation
                    self.animation_timer += 1
                    if self.animation_timer >= seuil_animation:
                        self.animation_timer = 0
                        self.index_frame += 1
                        if self.index_frame >= len(self.current_animation):
                            self.index_frame = 0
            else:
                if self.current_animation is not self.jumping_frames:
                    self.current_animation = self.jumping_frames
                    self.index_frame = 0
                    self.animation_timer = 0
                    self.jump_sequence_index = 0
                else:
                    # Animation du saut
                    seuil_animation = self.vitesse_animation
                    self.animation_timer += 1
                    if self.animation_timer >= seuil_animation:
                        self.animation_timer = 0
                        if self.jump_sequence_index < len(self.jumping_frames) - 1:
                            self.jump_sequence_index += 1
                        self.index_frame = self.jump_sequence_index

        self.saut_appui_precedent = saut_appuye
        self.slide_appui_precedent = slide_appuye

    def get_rect(self):
        h = self.hauteur_slide if self.slide else self.hauteur
        return pygame.Rect(int(self.x), int(self.y), self.largeur, h)

    def dessiner(self, ecran):
        if not self.en_vie:
            return
        
        # Clignotement invincibilité
        if self.invincible > 0 and (self.invincible // 5) % 2 == 0:
            return

        rect = self.get_rect()
        
        # Dessiner avec sprite si disponible
        if self.utilise_sprite and len(self.current_animation) > 0:
            frame_a_dessiner = self.current_animation[self.index_frame]
            sprite_rect = frame_a_dessiner.get_rect()
            ancrage_bas = rect.bottom + (4 if self.slide else 6)
            sprite_rect.midbottom = (rect.centerx, ancrage_bas)
            if self.etat_montee:
                sprite_rect.y -= 3
            elif self.etat_descente:
                sprite_rect.y += 2

            ombre_largeur = max(18, int(sprite_rect.width * (0.42 if self.slide else 0.34)))
            pygame.draw.ellipse(
                ecran,
                (0, 0, 0, 90),
                (rect.centerx - ombre_largeur // 2, self.y_sol + 5, ombre_largeur, 10),
            )
            ecran.blit(frame_a_dessiner, sprite_rect)
        else:
            # Fallback sans sprite
            c1, c2 = self.couleurs
            ecrasement = 2 if self.atterrissage_timer > 0 else 0

            # Ombre
            pygame.draw.ellipse(ecran, (0, 0, 0),
                                (rect.x + 4, self.y_sol + 4, rect.width - 8, 10))
            # Corps
            corps_rect = rect.inflate(0, ecrasement)
            corps_c = (220, 60, 60) if self.flash > 0 else c1
            pygame.draw.rect(ecran, corps_c,   corps_rect, border_radius=10)
            pygame.draw.rect(ecran, (25, 25, 25), rect,    width=2, border_radius=10)

            # Tête
            if self.slide:            tete_offset = 2
            elif self.etat_descente:  tete_offset = -2
            elif self.etat_montee:    tete_offset = -14
            else:                     tete_offset = -10

            tete_y = rect.y + tete_offset
            tete_c = (220, 60, 60) if self.flash > 0 else c2
            pygame.draw.circle(ecran, tete_c,    (rect.centerx, tete_y + 12), 12)
            pygame.draw.circle(ecran, (25,25,25),(rect.centerx, tete_y + 12), 12, 2)

            pygame.draw.circle(ecran, BLANC, (rect.centerx - 4, tete_y + 10), 3)
            pygame.draw.circle(ecran, BLANC, (rect.centerx + 4, tete_y + 10), 3)
            pygame.draw.circle(ecran, NOIR,  (rect.centerx - 4, tete_y + 10), 1)
            pygame.draw.circle(ecran, NOIR,  (rect.centerx + 4, tete_y + 10), 1)

            # Bras
            off_bras = 2 if (self.anim // 10) % 2 == 0 else -2
            if self.etat_descente: off_bras = 5
            elif self.etat_montee: off_bras = -5

            pygame.draw.rect(ecran, c2, (rect.x - 5,     rect.y + 14 + off_bras, 8, 14), border_radius=3)
            pygame.draw.rect(ecran, c2, (rect.right - 3, rect.y + 14 - off_bras, 8, 14), border_radius=3)

            if self.etat_descente:
                for dx in (-12, 12):
                    pygame.draw.line(ecran, BLANC,
                                     (rect.centerx + dx, rect.y - 10),
                                     (rect.centerx + dx, rect.y + 4), 2)

        txt = police(28).render(self.nom, True, BLANC)
        ecran.blit(txt, (rect.x - 4, rect.y - 34))

    def dessiner_vies(self, ecran, x, y):
        """Dessine les vies sous forme de coeurs pygame (pas de Unicode)."""
        taille = 9  # rayon demi-coeur
        espacement = 24
        for i in range(self.VIES_MAX):
            col = ROUGE_VIF if i < self.vies else (60, 65, 80)
            cx_ = x + i * espacement + taille
            cy_ = y + taille
            # Deux cercles haut
            pygame.draw.circle(ecran, col, (cx_ - taille // 2, cy_ - 1), taille // 2 + 1)
            pygame.draw.circle(ecran, col, (cx_ + taille // 2, cy_ - 1), taille // 2 + 1)
            # Triangle bas
            pygame.draw.polygon(ecran, col, [
                (cx_ - taille,     cy_),
                (cx_ + taille + 1, cy_),
                (cx_,              cy_ + taille + 2)
            ])
            # Reflet (petit cercle clair en haut-gauche)
            if i < self.vies:
                pygame.draw.circle(ecran, (255, 160, 160), (cx_ - taille // 2 - 1, cy_ - 2), 2)


# ──────────────────────────────────────────────
#  OBSTACLES
# ──────────────────────────────────────────────
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

        self.anim = random.randint(0, 120)

    def deplacer(self, vitesse):
        self.x -= vitesse
        self.anim = (self.anim + 1) % 120

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.largeur, self.hauteur)

    def dessiner(self, ecran, pulse=0):
        rect = self.get_rect()
        if self.type == "low":
            pygame.draw.rect(ecran, (128, 85, 48),  rect, border_radius=6)
            pygame.draw.rect(ecran, (79,  51, 28),  rect, width=2, border_radius=6)
            for i in range(rect.y + 8, rect.bottom, 10):
                pygame.draw.line(ecran, (153, 105, 62),
                                 (rect.x + 6, i), (rect.right - 6, i), 1)
            # Chapeau du tronc
            pygame.draw.ellipse(ecran, (160, 110, 60),
                                (rect.x + 4, rect.y - 5, rect.width - 8, 12))
            pygame.draw.ellipse(ecran, (79, 51, 28),
                                (rect.x + 4, rect.y - 5, rect.width - 8, 12), 2)
        else:
            sway = math.sin(self.anim * 0.08) * 3
            bx = int(rect.x + sway)
            pygame.draw.rect(ecran, (88, 106, 68),
                             (bx, rect.y, rect.width, rect.height), border_radius=6)
            pygame.draw.rect(ecran, (52, 66,  42),
                             (bx, rect.y, rect.width, rect.height), width=2, border_radius=6)
            leaf_c = (70, min(255, 150 + pulse // 3), 75)
            for lx, ly in [
                (bx + 10,              rect.centery - 4),
                (bx + rect.width - 10, rect.centery - 4),
                (bx + rect.width // 2, rect.y - 6),
            ]:
                pygame.draw.circle(ecran, leaf_c, (lx, ly), 10)
            if self.anim % 30 < 15:
                pygame.draw.circle(ecran, (255, 230, 80),
                                   (bx + rect.width // 2, rect.y - 8), 5)


# ──────────────────────────────────────────────
#  CIRCUIT
# ──────────────────────────────────────────────
class Circuit:
    def __init__(self, y_sol, longueur_niveau, gap_min=300, gap_max=420, generer_obstacles=True):
        self.y_sol = y_sol
        self.longueur_niveau = longueur_niveau
        self.gap_min = gap_min
        self.gap_max = gap_max
        self.generer_obstacles = generer_obstacles
        self.obstacles: list[Obstacle] = []
        if self.generer_obstacles:
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
            x += random.randint(self.gap_min, self.gap_max)

    def update(self, vitesse):
        for obs in self.obstacles:
            obs.deplacer(vitesse)

    def dessiner(self, ecran, pulse):
        for obs in self.obstacles:
            if -120 < obs.x < LARGEUR + 120:
                obs.dessiner(ecran, pulse)


# ──────────────────────────────────────────────
#  HUD
# ──────────────────────────────────────────────
def dessiner_hud(ecran, j1, j2, distance, longueur_niveau, vitesse, vitesse_max,
                 nom_niveau, compte_a_rebours):
    progression = min(1.0, distance / longueur_niveau)
    score       = int(distance / 10)
    ratio_v     = min(1.0, vitesse / vitesse_max)

    # ── Un seul panneau divise en 3 sections
    PAD = 10
    PW, PH = 610, 92
    C_J1 = (255, 140, 80)
    C_J2 = (80,  170, 255)
    COL_LABEL = (130, 148, 180)

    # Fond
    surf = pygame.Surface((PW, PH), pygame.SRCALPHA)
    pygame.draw.rect(surf, (6, 10, 22, 215), (0, 0, PW, PH), border_radius=14)
    ecran.blit(surf, (PAD, PAD))
    # Liseré haut
    pygame.draw.rect(ecran, (55, 95, 195), (PAD + 2, PAD, PW - 4, 3), border_radius=2)
    # Bordure
    pygame.draw.rect(ecran, (65, 88, 130), (PAD, PAD, PW, PH), width=1, border_radius=14)

    # ─── SECTION 1 : Nom + vies  (x: 22..195)
    S1_X = PAD + 12
    ecran.blit(police(17).render(nom_niveau.upper(), True, (95, 195, 255)), (S1_X, PAD + 8))
    ecran.blit(police(18).render("J1", True, C_J1), (S1_X,      PAD + 32))
    j1.dessiner_vies(ecran,                          S1_X + 30,  PAD + 30)
    ecran.blit(police(18).render("J2", True, C_J2), (S1_X,      PAD + 60))
    j2.dessiner_vies(ecran,                          S1_X + 30,  PAD + 58)

    # Separateur 1
    SEP1 = PAD + 180
    pygame.draw.line(ecran, (45, 60, 90), (SEP1, PAD + 8), (SEP1, PAD + PH - 8), 1)

    # ─── SECTION 2 : Progression + Score  (x: SEP1+12..SEP1+255)
    S2_X = SEP1 + 12
    BAR_W, BAR_H = 210, 11

    # Progression
    ecran.blit(police(15).render("PROGRESSION", True, COL_LABEL), (S2_X, PAD + 8))
    pct = police(15).render(f"{int(progression * 100)}%", True, BLANC)
    ecran.blit(pct, (S2_X + BAR_W - pct.get_width(), PAD + 8))
    by_p = PAD + 26
    pygame.draw.rect(ecran, (28, 35, 52), (S2_X, by_p, BAR_W, BAR_H), border_radius=5)
    t = progression
    fill_col = (int(60 + 195 * t), int(220 - 160 * t), 70)
    pygame.draw.rect(ecran, fill_col, (S2_X, by_p, max(5, int(BAR_W * progression)), BAR_H), border_radius=5)
    pygame.draw.rect(ecran, (95, 115, 155), (S2_X, by_p, BAR_W, BAR_H), width=1, border_radius=5)

    # Score
    ecran.blit(police(15).render("SCORE", True, COL_LABEL), (S2_X, PAD + 48))
    score_str = f"{score:,}".replace(",", " ")
    ecran.blit(police(27).render(score_str, True, JAUNE), (S2_X, PAD + 62))

    # Separateur 2
    SEP2 = SEP1 + 240
    pygame.draw.line(ecran, (45, 60, 90), (SEP2, PAD + 8), (SEP2, PAD + PH - 8), 1)

    # ─── SECTION 3 : Vitesse  (x: SEP2+12..PW)
    S3_X = SEP2 + 12
    SPD_W = PAD + PW - S3_X - 12

    ecran.blit(police(15).render("VITESSE", True, COL_LABEL), (S3_X, PAD + 8))
    spd_col = (int(60 + 195 * ratio_v), int(220 - 160 * ratio_v), 60)
    by_v = PAD + 26
    pygame.draw.rect(ecran, (28, 35, 52), (S3_X, by_v, SPD_W, BAR_H), border_radius=5)
    pygame.draw.rect(ecran, spd_col, (S3_X, by_v, max(5, int(SPD_W * ratio_v)), BAR_H), border_radius=5)
    pygame.draw.rect(ecran, (95, 115, 155), (S3_X, by_v, SPD_W, BAR_H), width=1, border_radius=5)
    spd_val = police(27).render(f"{int(ratio_v * 100)}%", True, spd_col)
    ecran.blit(spd_val, (S3_X, PAD + 48))

    # ── Compte a rebours
    if compte_a_rebours > 0:
        voile = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
        voile.fill((0, 0, 0, 110))
        ecran.blit(voile, (0, 0))
        cx_, cy_c = LARGEUR // 2, HAUTEUR // 2 - 20
        pygame.draw.circle(ecran, (15, 20, 38), (cx_, cy_c), 90)
        pygame.draw.circle(ecran, JAUNE,        (cx_, cy_c), 90, 4)
        txt = police(140).render(str(compte_a_rebours), True, JAUNE)
        ecran.blit(txt, txt.get_rect(center=(cx_, cy_c)))
        sous = police(34).render("Preparez-vous !", True, BLANC)
        ecran.blit(sous, sous.get_rect(center=(cx_, cy_c + 110)))


# ──────────────────────────────────────────────
#  ÉCRAN DE FIN ANIMÉ
# ──────────────────────────────────────────────
class EcranFin:
    def __init__(self, victoire: bool, nom_niveau: str):
        self.victoire   = victoire
        self.nom_niveau = nom_niveau
        self.frame      = 0
        self.particules: list[Particule] = []
        self.image_perdu = None
        if not self.victoire:
            try:
                dossier_courant = os.path.dirname(__file__)
                chemin_lost = os.path.join(dossier_courant, "assets", "lost.png")
                if os.path.exists(chemin_lost):
                    image = pygame.image.load(chemin_lost).convert_alpha()
                    hauteur_cible = 165
                    ratio = hauteur_cible / max(1, image.get_height())
                    largeur_cible = max(1, int(image.get_width() * ratio))
                    self.image_perdu = pygame.transform.smoothscale(image, (largeur_cible, hauteur_cible))
            except Exception:
                self.image_perdu = None
        if victoire:
            for _ in range(80):
                c = random.choice([(255, 215, 0), (0, 255, 200), (255, 100, 200)])
                p = Particule(random.randint(0, LARGEUR), random.randint(0, HAUTEUR // 2), c)
                p.vie = random.randint(60, 120)
                p.vie_max = p.vie
                p.vy = random.uniform(-3, 0)
                self.particules.append(p)

    def update(self):
        self.frame += 1
        for p in self.particules:
            p.update()
        self.particules = [p for p in self.particules if p.vie > 0]
        if self.victoire and self.frame % 10 == 0:
            c = random.choice([(255, 215, 0), (0, 255, 200), (255, 100, 200)])
            np = Particule(random.randint(0, LARGEUR), 0, c)
            np.vy = random.uniform(1, 4)
            np.vie = random.randint(60, 100)
            np.vie_max = np.vie
            self.particules.append(np)

    def dessiner(self, ecran):
        overlay = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        ecran.blit(overlay, (0, 0))

        for p in self.particules:
            p.dessiner(ecran)

        if not self.victoire and self.image_perdu is not None:
            rect_lost = self.image_perdu.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 - 190))
            ecran.blit(self.image_perdu, rect_lost)

        bob = int(math.sin(self.frame * 0.08) * 8)
        titre_txt = "VICTOIRE !" if self.victoire else "GAME OVER"
        titre_col = VERT         if self.victoire else ROUGE
        sous_txt  = ("Les deux joueurs ont survécu jusqu'au bout !"
                     if self.victoire else "Un joueur a perdu toutes ses vies.")

        # Ombre + titre animé
        ombre = police(100).render(titre_txt, True, NOIR)
        ecran.blit(ombre, ombre.get_rect(center=(LARGEUR // 2 + 5, HAUTEUR // 2 - 80 + bob + 5)))
        titre = police(100).render(titre_txt, True, titre_col)
        ecran.blit(titre, titre.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 - 80 + bob)))

        ecran.blit(police(30).render(self.nom_niveau, True, CYAN),
                   police(30).render(self.nom_niveau, True, CYAN)
                   .get_rect(center=(LARGEUR // 2, HAUTEUR // 2 - 10)))

        ecran.blit(police(28).render(sous_txt, True, BLANC),
                   police(28).render(sous_txt, True, BLANC)
                   .get_rect(center=(LARGEUR // 2, HAUTEUR // 2 + 40)))

        if (self.frame // 25) % 2 == 0:
            aide = police(28).render("R = rejouer   |   ESC = retour au menu", True, BLANC)
            ecran.blit(aide, aide.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 + 90)))


# ──────────────────────────────────────────────
#  JEU PRINCIPAL
# ──────────────────────────────────────────────
class JeuDeuxJoueurs:
    COUNTDOWN_DUREE = 3

    def __init__(self, config_niveau=None):
        if config_niveau is None:
            config_niveau = {}
        self.config_niveau = config_niveau
        self.nom_niveau    = config_niveau.get("nom", "Libre")

        self.fond = Skybox()
        self.longueur_niveau = config_niveau.get("longueur", 9800)
        self.distance        = 0.0
        self.vitesse         = config_niveau.get("vitesse",      4.1)
        self.vitesse_max     = config_niveau.get("vitesse_max",  6.8)
        self.acceleration    = config_niveau.get("acceleration", 0.0009)

        self.y_sol_j1 = int(HAUTEUR * 0.48)
        self.y_sol_j2 = int(HAUTEUR * 0.82)

        self.joueur1 = Joueur(
            x=220, y_sol=self.y_sol_j1,
            controles=(pygame.K_z, pygame.K_s),
            nom="J1", couleurs=((225, 120, 90), (255, 170, 140)),
        )
        self.joueur2 = Joueur(
            x=220, y_sol=self.y_sol_j2,
            controles=(pygame.K_UP, pygame.K_DOWN),
            nom="J2", couleurs=((90, 145, 230), (140, 195, 255)),
        )

        gap_min = config_niveau.get("gap_min", 300)
        gap_max = config_niveau.get("gap_max", 420)
        generer_obstacles = config_niveau.get("generer_obstacles", True)
        self.circuit_j1 = Circuit(self.y_sol_j1, self.longueur_niveau, gap_min, gap_max, generer_obstacles)
        self.circuit_j2 = Circuit(self.y_sol_j2, self.longueur_niveau, gap_min, gap_max, generer_obstacles)

        # Pistes de sol
        self.piste_j1 = PisteSol(self.y_sol_j1)
        self.piste_j2 = PisteSol(self.y_sol_j2)

        self.game_over   = False
        self.victoire    = False
        self.frame       = 0
        self.particules: list[Particule] = []
        self.offset_piste = 0.0

        self.countdown_frames = self.COUNTDOWN_DUREE * FPS
        self.en_jeu = False
        self.ecran_fin: EcranFin | None = None
        self.derniere_seconde = self.COUNTDOWN_DUREE

    @property
    def termine(self):
        return self.game_over or self.victoire

    def _terminer(self, victoire: bool):
        self.game_over = not victoire
        self.victoire  = victoire
        self.ecran_fin = EcranFin(victoire, self.nom_niveau)
        SONS.play("win" if victoire else "lose")

    def update(self, touches):
        self.frame += 1

        if not self.en_jeu:
            self.countdown_frames -= 1
            seconde_restante = max(1, int(math.ceil(self.countdown_frames / FPS)))
            if seconde_restante != self.derniere_seconde and self.countdown_frames > 0:
                self.derniere_seconde = seconde_restante
                SONS.play("countdown")
            if self.countdown_frames <= 0:
                self.en_jeu = True
            return

        if self.termine:
            self.ecran_fin.update()
            return

        self.joueur1.update(touches)
        self.joueur2.update(touches)

        if self.joueur1.vient_de_sauter or self.joueur2.vient_de_sauter:
            SONS.play("jump")

        if self.vitesse < self.vitesse_max:
            self.vitesse += self.acceleration

        self.offset_piste += self.vitesse
        self.fond.update(self.vitesse)
        self.piste_j1.update(self.vitesse)
        self.piste_j2.update(self.vitesse)
        self.circuit_j1.update(self.vitesse)
        self.circuit_j2.update(self.vitesse)
        self.distance += self.vitesse

        for p in self.particules:
            p.update()
        self.particules = [p for p in self.particules if p.vie > 0]

        # Collisions avec marge de tolérance
        rect1 = self.joueur1.get_rect().inflate(-8, -8)
        for obs in self.circuit_j1.obstacles:
            if rect1.colliderect(obs.get_rect()):
                if self.joueur1.touche():
                    SONS.play("hit")
                    self._spawn_particules(self.joueur1)
                    if not self.joueur1.en_vie:
                        self._terminer(False)
                        return

        rect2 = self.joueur2.get_rect().inflate(-8, -8)
        for obs in self.circuit_j2.obstacles:
            if rect2.colliderect(obs.get_rect()):
                if self.joueur2.touche():
                    SONS.play("hit")
                    self._spawn_particules(self.joueur2)
                    if not self.joueur2.en_vie:
                        self._terminer(False)
                        return

        if self.distance >= self.longueur_niveau:
            self._terminer(True)

    def _spawn_particules(self, joueur):
        rect = joueur.get_rect()
        for _ in range(20):
            c = random.choice([ROUGE, ORANGE, JAUNE])
            self.particules.append(Particule(rect.centerx, rect.centery, c))

    def dessiner(self, ecran):
        self.fond.dessiner(ecran)

        pulse = int(60 * abs(((self.frame % 40) / 20) - 1))
        self.circuit_j1.dessiner(ecran, pulse)
        self.circuit_j2.dessiner(ecran, pulse)
        
        # Pistes de sol
        self.piste_j1.dessiner(ecran)
        self.piste_j2.dessiner(ecran)

        self.joueur1.dessiner(ecran)
        self.joueur2.dessiner(ecran)

        for p in self.particules:
            p.dessiner(ecran)

        compte_rebours_affiche = 0
        if not self.en_jeu:
            compte_rebours_affiche = max(1, int(math.ceil(self.countdown_frames / FPS)))

        dessiner_hud(ecran, self.joueur1, self.joueur2,
                     self.distance, self.longueur_niveau,
                     self.vitesse, self.vitesse_max,
                     self.nom_niveau, compte_rebours_affiche)

        if self.ecran_fin:
            self.ecran_fin.dessiner(ecran)


# ──────────────────────────────────────────────
#  BOUCLE PRINCIPALE
# ──────────────────────────────────────────────
def lancer_jeu(ecran, config_niveau=None):
    horloge = pygame.time.Clock()
    partie  = JeuDeuxJoueurs(config_niveau)

    while True:
        horloge.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if partie.termine and event.key == pygame.K_r:
                    return lancer_jeu(ecran, config_niveau)

        touches = pygame.key.get_pressed()
        partie.update(touches)
        partie.dessiner(ecran)
        pygame.display.flip()
