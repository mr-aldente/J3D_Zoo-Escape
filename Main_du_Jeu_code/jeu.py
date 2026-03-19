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
        "ai_j2": True,
    },
    1: {  # Niveau 1: Facile — calibré pour être finissable confortablement
        "nom": "Level 1 - EASY",
        "longueur": 8500,
        "vitesse": 2.8,
        "vitesse_max": 4.2,
        "acceleration": 0.0003,
        "gap_min": 580,
        "gap_max": 800,
        "generer_obstacles": True,
        "ai_j2": True,
        "vies": 5,
    },
    2: {  # Niveau 2: Moyen
        "nom": "Level 2 - MEDIUM",
        "longueur": 16000,
        "vitesse": 4.4,
        "vitesse_max": 7.0,
        "acceleration": 0.0010,
        "gap_min": 300,
        "gap_max": 430,
        "generer_obstacles": True,
        "ai_j2": True,
    },
    3: {  # Niveau 3: Difficile
        "nom": "Level 3 - HARD",
        "longueur": 18000,
        "vitesse": 5.0,
        "vitesse_max": 8.2,
        "acceleration": 0.0013,
        "gap_min": 230,
        "gap_max": 360,
        "generer_obstacles": True,
        "ai_j2": True,
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


# ──────────────────────────────────────────────
#  FAUX TOUCHES (IA J2)
# ──────────────────────────────────────────────
class FauxTouches:
    """Émule un tableau de touches pygame pour l'IA de J2."""
    def __init__(self, base, overrides: dict):
        self._base = base
        self._overrides = overrides

    def __getitem__(self, key):
        return self._overrides.get(key, self._base[key])


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
        # Ligne de sol brique (couleur extraite du Background_lvl1)
        pygame.draw.line(ecran, (60, 38, 22),  (0, self.y_sol),     (LARGEUR, self.y_sol),     4)
        pygame.draw.line(ecran, (155, 100, 62), (0, self.y_sol + 1), (LARGEUR, self.y_sol + 1), 1)
        # Motif briques animé
        bw, bh = 52, 8
        off = int(self.offset_anim) % bw
        for row_i in range(2):
            roff = (bw // 2) * (row_i % 2)
            ry   = self.y_sol + 2 + row_i * bh
            for x in range(-bw + off + roff, LARGEUR + bw, bw):
                pygame.draw.rect(ecran, (115, 74, 44), (max(0, x), ry, bw - 3, bh - 2), border_radius=1)
                pygame.draw.rect(ecran, (60, 38, 22),  (max(0, x), ry, bw - 3, bh - 2), 1, border_radius=1)


# ──────────────────────────────────────────────
#  SKYBOX (deux images: skybox0 en bas, Skybox1 en haut)
# ──────────────────────────────────────────────
class Skybox:
    def __init__(self):
        self.skybox0 = None
        self.skybox1 = None
        self.offset_x = 0.0
        self.coeff_scroll = 0.68
        self.palette_obstacles_haut = None
        self.palette_obstacles_bas = None
        self._charger_images()

    @staticmethod
    def _assombrir(couleur, facteur):
        return tuple(max(0, min(255, int(c * facteur))) for c in couleur)

    @staticmethod
    def _eclaircir(couleur, delta):
        return tuple(max(0, min(255, c + delta)) for c in couleur)

    @staticmethod
    def _moyenne_couleur(surface, y_ratio=0.82):
        if surface is None:
            return (120, 110, 95)

        largeur, hauteur = surface.get_size()
        if largeur <= 0 or hauteur <= 0:
            return (120, 110, 95)

        y = max(0, min(hauteur - 1, int(hauteur * y_ratio)))
        x_min = int(largeur * 0.12)
        x_max = int(largeur * 0.88)
        pas = max(1, (x_max - x_min) // 28)

        total_r = total_g = total_b = n = 0
        for x in range(x_min, x_max, pas):
            r, g, b, a = surface.get_at((x, y))
            if a == 0:
                continue
            total_r += r
            total_g += g
            total_b += b
            n += 1

        if n == 0:
            return (120, 110, 95)
        return (total_r // n, total_g // n, total_b // n)

    def _construire_palette_obstacles(self, image, base_defaut):
        """
        Palette accordée au Background_lvl1 (analyse pixel) :
          – Sol brique/brun : (143, 94, 67)  → obstacles "low"
          – Pierre/gris     : (127,127,127)  → obstacles "high"
        La base extraite de l'image affine légèrement ces valeurs.
        """
        base = self._moyenne_couleur(image, y_ratio=0.89) if image is not None else base_defaut

        # ── Palette "low" (briques brunes) ────────────────────────────────
        # On mélange la couleur extraite (~brique) avec le brun de référence
        brick_ref = (143, 94, 67)
        low_body  = tuple(int(base[i] * 0.55 + brick_ref[i] * 0.45) for i in range(3))
        low_out   = self._assombrir(low_body, 0.60)
        low_det   = self._eclaircir(low_body, 22)
        low_cap   = self._eclaircir(low_body, 35)

        # ── Palette "high" (pierre grise) ─────────────────────────────────
        stone_ref = (127, 127, 127)
        hi_body   = tuple(int(base[i] * 0.30 + stone_ref[i] * 0.70) for i in range(3))
        hi_out    = self._assombrir(hi_body, 0.52)
        hi_leaf   = self._eclaircir(hi_body, 30)
        hi_glow   = self._eclaircir(hi_body, 60)

        return {
            "low_body":    low_body,
            "low_outline": low_out,
            "low_detail":  low_det,
            "low_cap":     low_cap,
            "high_body":   hi_body,
            "high_outline":hi_out,
            "high_leaf":   hi_leaf,
            "high_glow":   hi_glow,
        }

    @staticmethod
    def _charger_et_redimensionner(chemin):
        if not os.path.exists(chemin):
            return None
        image = pygame.image.load(chemin).convert_alpha()
        cible_h = max(1, HAUTEUR // 2)
        ratio = cible_h / max(1, image.get_height())
        cible_w = max(LARGEUR, int(image.get_width() * ratio))
        return pygame.transform.smoothscale(image, (cible_w, cible_h))

    def _charger_images(self):
        try:
            chemin_assets = os.path.join(os.path.dirname(__file__), "assets")
            chemin_lvl1 = os.path.join(chemin_assets, "Background_lvl1.png")
            chemin_base = os.path.join(os.path.dirname(__file__), "assets", "Skybox_0000")
            chemin0 = os.path.join(chemin_base, "skybox0.png")
            chemin1 = os.path.join(chemin_base, "Skybox1.png")

            image_lvl1 = self._charger_et_redimensionner(chemin_lvl1)
            if image_lvl1 is not None:
                # Même fond pour les 2 zones (haut/bas), défilement synchronisé
                self.skybox1 = image_lvl1
                self.skybox0 = image_lvl1.copy()
            else:
                self.skybox0 = self._charger_et_redimensionner(chemin0)
                self.skybox1 = self._charger_et_redimensionner(chemin1)

            self.palette_obstacles_haut = self._construire_palette_obstacles(self.skybox1, (120, 135, 95))
            self.palette_obstacles_bas = self._construire_palette_obstacles(self.skybox0, (145, 110, 80))
        except Exception as e:
            print(f"Erreur chargement skybox: {e}")

    def update(self, vitesse_jeu):
        self.offset_x += max(0.0, vitesse_jeu) * self.coeff_scroll

    def palettes_obstacles(self):
        return self.palette_obstacles_haut, self.palette_obstacles_bas

    def _dessiner_couche(self, ecran, image, y):
        if image is None:
            return
        largeur_img = image.get_width()
        if largeur_img <= 0:
            return

        off = int(self.offset_x) % largeur_img
        x = -off
        while x < LARGEUR:
            ecran.blit(image, (x, y))
            x += largeur_img

    def dessiner(self, ecran):
        if self.skybox1 is None:
            pygame.draw.rect(ecran, (145, 205, 255), (0, 0, LARGEUR, HAUTEUR // 2))
        else:
            self._dessiner_couche(ecran, self.skybox1, 0)

        if self.skybox0 is None:
            pygame.draw.rect(ecran, (120, 175, 110), (0, HAUTEUR // 2, LARGEUR, HAUTEUR // 2))
        else:
            self._dessiner_couche(ecran, self.skybox0, HAUTEUR // 2)


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
    # Bande de sol en pierre/brique — couleurs extraites du Background_lvl1
    pygame.draw.rect(ecran, (88, 57, 35),  (0, y_sol + 2, LARGEUR, 55))
    pygame.draw.line(ecran, (48, 30, 18),  (0, y_sol + 2), (LARGEUR, y_sol + 2), 5)
    pygame.draw.line(ecran, (165, 108, 68),(0, y_sol),      (LARGEUR, y_sol),     2)
    # Motif briques animé
    bw, bh = 52, 14
    off = int(offset_anim) % bw
    for row_i, ry in enumerate(range(y_sol + 4, y_sol + 57, bh)):
        roff = (bw // 2) * (row_i % 2)
        for x in range(-bw + off + roff, LARGEUR + bw, bw):
            rect_b = pygame.Rect(max(0, x), ry, min(bw - 3, LARGEUR - max(0, x)), min(bh - 2, y_sol + 57 - ry))
            if rect_b.width > 2 and rect_b.height > 2:
                pygame.draw.rect(ecran, (120, 78, 48), rect_b, border_radius=1)
                pygame.draw.rect(ecran, (55, 34, 20),  rect_b, 1, border_radius=1)
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
        self.gravite = 0.52      # gravité très douce → long temps en l'air
        self.force_saut = -17.5  # élan initial fort → haute trajectoire

        self.sur_sol = True
        self.slide = False
        self.slide_buffer = False
        self.saut_buffer = 0     # jump-buffer : mémorise le saut en avance
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

        # Jump buffer : mémorise l'intention de saut pendant 10 frames
        if declenche_saut and not self.sur_sol:
            self.saut_buffer = 10
        if self.saut_buffer > 0:
            self.saut_buffer -= 1

        # Saut normal OU via buffer à l'atterrissage
        if (declenche_saut or self.saut_buffer > 0) and self.sur_sol and not self.slide and self.cooldown_saut == 0:
            self.vy = self.force_saut
            self.sur_sol = False
            self.vient_de_sauter = True
            self.cooldown_saut = 8
            self.saut_buffer = 0

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
    """
    Obstacles redessinés pour coller au Background_lvl1.png.
    Couleurs tirées de l'analyse du background :
      - Brique/brun  : (143, 94, 67)  → obstacles "low" (sauter par-dessus)
      - Pierre/gris  : (127, 127, 127) → obstacles "high" (se baisser en dessous)
    Sous-types visuels :
      low  → "crate" (caisse en bois), "barrel" (tonneau), "wall" (mur de briques)
      high → "stalactite" (roche suspendue), "beam" (poutre avec chaîne)
    """
    _LOW_SUBTYPES  = ("crate", "barrel", "wall")
    _HIGH_SUBTYPES = ("stalactite", "beam")

    def __init__(self, x, y_sol, obstacle_type, largeur=70, obstacle_palette=None):
        self.x       = float(x)
        self.y_sol   = y_sol
        self.type    = obstacle_type
        self.largeur = largeur

        # Palette accordée au Background_lvl1 (briques + pierre grise)
        self.palette = obstacle_palette or {
            "low_body":    (143, 94,  67),
            "low_outline": (90,  55,  28),
            "low_detail":  (175, 118, 80),
            "low_cap":     (185, 125, 75),
            "high_body":   (118, 118, 118),
            "high_outline":(68,  68,  68),
            "high_leaf":   (148, 148, 148),
            "high_glow":   (210, 210, 210),
        }

        if self.type == "low":
            self.hauteur = random.randint(44, 62)   # plus facile à sauter
            self.y       = y_sol - self.hauteur
            self.subtype = random.choice(self._LOW_SUBTYPES)
        else:
            self.hauteur = random.randint(18, 26)   # poutre fine
            self.y       = y_sol - random.randint(72, 82)  # assez haut pour forcer le slide
            self.subtype = random.choice(self._HIGH_SUBTYPES)

        self.anim = random.randint(0, 120)

    def deplacer(self, vitesse):
        self.x   -= vitesse
        self.anim = (self.anim + 1) % 120

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.largeur, self.hauteur)

    # ─── helpers palette ───────────────────────────────────────────────────────
    def _pal(self, key, default):
        return self.palette.get(key, default)

    # ─── visuel ────────────────────────────────────────────────────────────────
    def dessiner(self, ecran, pulse=0):
        rect      = self.get_rect()
        low_body  = self._pal("low_body",    (143, 94, 67))
        low_out   = self._pal("low_outline", (90, 55, 28))
        low_det   = self._pal("low_detail",  (175, 118, 80))
        low_cap   = self._pal("low_cap",     (185, 125, 75))
        hi_body   = self._pal("high_body",   (118, 118, 118))
        hi_out    = self._pal("high_outline",(68, 68, 68))
        hi_glow   = self._pal("high_glow",   (210, 210, 210))

        if self.type == "low":
            # ── Ombre portée ──
            pygame.draw.ellipse(ecran, (0, 0, 0),
                                (rect.x + 6, self.y_sol + 3, rect.width - 12, 9))

            if self.subtype == "barrel":
                # Tonneau brun avec cerclages métalliques
                pygame.draw.rect(ecran, low_body,  rect, border_radius=10)
                pygame.draw.rect(ecran, low_out,   rect, 2, border_radius=10)
                # Cerclages horizontaux
                for yi in (0.25, 0.50, 0.75):
                    y_b = int(rect.y + rect.height * yi)
                    pygame.draw.rect(ecran, (80, 80, 80),
                                     (rect.x - 2, y_b - 3, rect.width + 4, 6), border_radius=3)
                    pygame.draw.rect(ecran, (140, 140, 140),
                                     (rect.x - 2, y_b - 3, rect.width + 4, 6), 1, border_radius=3)
                # Bouchon du dessus
                pygame.draw.ellipse(ecran, low_cap,
                                    (rect.x + 4, rect.y - 6, rect.width - 8, 13))
                pygame.draw.ellipse(ecran, low_out,
                                    (rect.x + 4, rect.y - 6, rect.width - 8, 13), 2)

            elif self.subtype == "crate":
                # Caisse en bois avec croix
                pygame.draw.rect(ecran, low_body, rect, border_radius=4)
                pygame.draw.rect(ecran, low_out,  rect, 2, border_radius=4)
                pygame.draw.line(ecran, low_out, rect.topleft,    rect.bottomright, 2)
                pygame.draw.line(ecran, low_out, rect.topright,   rect.bottomleft,  2)
                # Reflet haut-gauche
                pygame.draw.line(ecran, low_det,
                                 (rect.x + 3, rect.y + 3), (rect.right - 4, rect.y + 3), 1)
                pygame.draw.line(ecran, low_det,
                                 (rect.x + 3, rect.y + 3), (rect.x + 3, rect.bottom - 4), 1)

            else:  # wall — mur de briques
                pygame.draw.rect(ecran, low_body, rect, border_radius=3)
                pygame.draw.rect(ecran, low_out,  rect, 2, border_radius=3)
                bw, bh = 20, 12
                for ri, by in enumerate(range(rect.y, rect.bottom, bh)):
                    roff = (bw // 2) * (ri % 2)
                    for bx in range(rect.x - roff, rect.right + bw, bw):
                        bx0 = max(rect.x, bx)
                        bw0 = min(rect.right, bx + bw - 2) - bx0
                        bh0 = min(bh - 2, rect.bottom - by)
                        if bw0 > 1 and bh0 > 1:
                            pygame.draw.rect(ecran, low_out, (bx0, by, bw0, bh0), 1)
                # Reflet léger sur la rangée du haut
                pygame.draw.line(ecran, low_det,
                                 (rect.x + 3, rect.y + 3), (rect.right - 3, rect.y + 3), 1)

        else:  # ── Obstacles en hauteur ──────────────────────────────────────
            sway = math.sin(self.anim * 0.07) * 3
            bx   = int(rect.x + sway)

            if self.subtype == "stalactite":
                # Stalactite en pierre qui dépasse du plafond
                w = rect.width
                h = rect.height
                pts = [
                    (bx,          rect.y),
                    (bx + w,      rect.y),
                    (bx + w * 3 // 4, rect.y + h // 2),
                    (bx + w // 2, rect.y + h),        # pointe
                    (bx + w // 4, rect.y + h // 2),
                ]
                pygame.draw.polygon(ecran, hi_body,  pts)
                pygame.draw.polygon(ecran, hi_out,   pts, 2)
                # Reflet
                pygame.draw.line(ecran, hi_glow,
                                 (bx + 4, rect.y + 5),
                                 (bx + w // 2 - 3, rect.y + h - 8), 2)
                # Goutte
                if self.anim % 40 < 20:
                    pygame.draw.circle(ecran, (140, 200, 240),
                                       (bx + w // 2, rect.bottom + 6), 4)

            else:  # beam — poutre suspendue par une chaîne
                # Chaîne
                cx_ = bx + rect.width // 2
                for cy_ in range(rect.y - 28, rect.y, 8):
                    pygame.draw.ellipse(ecran, hi_out, (cx_ - 4, cy_, 8, 6), 2)
                # Poutre
                pygame.draw.rect(ecran, hi_body,
                                 (bx, rect.y, rect.width, rect.height), border_radius=5)
                pygame.draw.rect(ecran, hi_out,
                                 (bx, rect.y, rect.width, rect.height), 2, border_radius=5)
                # Striures de bois
                for si in range(3):
                    lx_ = bx + 6 + si * (rect.width - 12) // 3
                    pygame.draw.line(ecran, hi_out,
                                     (lx_, rect.y + 3), (lx_, rect.bottom - 3), 1)
                # Pointes en bas
                for si in range(3):
                    spx = bx + 8 + si * (rect.width - 16) // 3
                    pygame.draw.polygon(ecran, hi_out, [
                        (spx, rect.bottom),
                        (spx + 7, rect.bottom),
                        (spx + 3, rect.bottom + 10),
                    ])


# ──────────────────────────────────────────────
#  PIÈCE COLLECTIBLE
# ──────────────────────────────────────────────
class Piece:
    """Pièce dorée collectible qui donne des points bonus."""
    __slots__ = ("x", "y", "rayon", "anim", "collectee")

    def __init__(self, x, y):
        self.x        = float(x)
        self.y        = float(y)
        self.rayon    = 9
        self.anim     = random.randint(0, 62)
        self.collectee = False

    def deplacer(self, vitesse):
        self.x   -= vitesse
        self.anim = (self.anim + 1) % 62

    def get_rect(self):
        r = self.rayon
        return pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)

    def dessiner(self, ecran):
        if self.collectee:
            return
        bob = int(math.sin(self.anim * 0.10) * 4)
        cx, cy, r = int(self.x), int(self.y) + bob, self.rayon
        # Ombre légère
        surf_omb = pygame.Surface((r * 4, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(surf_omb, (0, 0, 0, 60), surf_omb.get_rect())
        ecran.blit(surf_omb, (cx - r * 2, cy + r + 2))
        # Corps doré
        pygame.draw.circle(ecran, (255, 215, 0),   (cx, cy), r)
        pygame.draw.circle(ecran, (200, 155, 0),   (cx, cy), r, 2)
        # Reflet
        pygame.draw.circle(ecran, (255, 245, 160), (cx - 2, cy - 3), r // 3)
        # Symbole "$" / signe coin
        txt = pygame.font.Font(None, 16).render("$", True, (160, 120, 0))
        ecran.blit(txt, txt.get_rect(center=(cx, cy)))


# ──────────────────────────────────────────────
#  CIRCUIT
# ──────────────────────────────────────────────
class Circuit:
    def __init__(self, y_sol, longueur_niveau, gap_min=300, gap_max=420, generer_obstacles=True,
                 obstacle_palette=None):
        self.y_sol             = y_sol
        self.longueur_niveau   = longueur_niveau
        self.gap_min           = gap_min
        self.gap_max           = gap_max
        self.generer_obstacles = generer_obstacles
        self.obstacle_palette  = obstacle_palette
        self.obstacles: list[Obstacle] = []
        self.pieces:    list[Piece]    = []
        if self.generer_obstacles:
            self._generer()

    def _generer(self):
        x         = 920
        last_type = "low"
        # ── Obstacles ────────────────────────────────────────────────────────
        while x < self.longueur_niveau + 1600:
            # Alterner régulièrement ; 28 % de chance de répétition
            if random.random() < 0.72:
                obstacle_type = "high" if last_type == "low" else "low"
            else:
                obstacle_type = last_type
            largeur = random.randint(56, 84)
            self.obstacles.append(
                Obstacle(x, self.y_sol, obstacle_type, largeur, self.obstacle_palette)
            )
            last_type = obstacle_type
            x += random.randint(self.gap_min, self.gap_max)

        # ── Pièces (arcs entre obstacles) ────────────────────────────────────
        for obs in self.obstacles:
            count = random.randint(2, 5)
            for i in range(count):
                px = obs.x - 120 - i * 28
                # hauteur : un peu au-dessus du sol, accessible en courant/sautant
                py = self.y_sol - random.randint(35, 80)
                self.pieces.append(Piece(px, py))

    def update(self, vitesse):
        for obs in self.obstacles:
            obs.deplacer(vitesse)
        for piece in self.pieces:
            if not piece.collectee:
                piece.deplacer(vitesse)

    def dessiner(self, ecran, pulse):
        for piece in self.pieces:
            if not piece.collectee and -30 < piece.x < LARGEUR + 30:
                piece.dessiner(ecran)
        for obs in self.obstacles:
            if -120 < obs.x < LARGEUR + 120:
                obs.dessiner(ecran, pulse)


# ──────────────────────────────────────────────
#  HUD
# ──────────────────────────────────────────────
def dessiner_hud(ecran, j1, j2, distance, longueur_niveau, vitesse, vitesse_max,
                 nom_niveau, compte_a_rebours, score_pieces=0):
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

    # Score + pièces
    ecran.blit(police(15).render("SCORE", True, COL_LABEL), (S2_X, PAD + 48))
    score_str = f"{score:,}".replace(",", " ")
    ecran.blit(police(27).render(score_str, True, JAUNE), (S2_X, PAD + 62))
    # Icône pièce + compteur
    pygame.draw.circle(ecran, (255, 215, 0), (S2_X + BAR_W - 22, PAD + 72), 7)
    pygame.draw.circle(ecran, (200, 155, 0), (S2_X + BAR_W - 22, PAD + 72), 7, 2)
    ecran.blit(police(20).render(f"x{score_pieces}", True, (255, 215, 0)),
               (S2_X + BAR_W - 11, PAD + 66))

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
    def __init__(self, victoire: bool, nom_niveau: str, score_pieces: int = 0,
                 score_distance: int = 0):
        self.victoire       = victoire
        self.nom_niveau     = nom_niveau
        self.score_pieces   = score_pieces
        self.score_distance = score_distance
        self.frame          = 0
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

        bob      = int(math.sin(self.frame * 0.08) * 8)
        titre_txt = "VICTOIRE !" if self.victoire else "GAME OVER"
        titre_col = VERT         if self.victoire else ROUGE

        # ── Ombre + titre animé ──────────────────────────────────────────────
        ombre = police(100).render(titre_txt, True, NOIR)
        ecran.blit(ombre, ombre.get_rect(center=(LARGEUR // 2 + 5, HAUTEUR // 2 - 90 + bob + 5)))
        titre = police(100).render(titre_txt, True, titre_col)
        ecran.blit(titre, titre.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 - 90 + bob)))

        # ── Niveau ───────────────────────────────────────────────────────────
        ecran.blit(police(30).render(self.nom_niveau, True, CYAN),
                   police(30).render(self.nom_niveau, True, CYAN)
                   .get_rect(center=(LARGEUR // 2, HAUTEUR // 2 - 18)))

        # ── Tableau des scores ───────────────────────────────────────────────
        score_dist = self.score_distance
        score_tot  = score_dist + self.score_pieces * 50
        lignes_score = [
            (f"Distance :  {score_dist:,}".replace(",", " "), BLANC),
            (f"Pièces   :  {self.score_pieces}  (x50 pts)",    (255, 215, 0)),
            (f"TOTAL    :  {score_tot:,}".replace(",", " "),   JAUNE),
        ]
        for i, (txt, col) in enumerate(lignes_score):
            s = police(28).render(txt, True, col)
            ecran.blit(s, s.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 + 20 + i * 34)))

        # ── Message contextuel ───────────────────────────────────────────────
        if self.victoire:
            msg = "Bravo ! Les deux joueurs ont franchi la ligne d'arrivée !"
        else:
            msg = "Un joueur est tombé — les deux perdent. Appuyez sur R pour recommencer."
        ecran.blit(police(26).render(msg, True, (200, 200, 200)),
                   police(26).render(msg, True, (200, 200, 200))
                   .get_rect(center=(LARGEUR // 2, HAUTEUR // 2 + 122)))

        # ── Blink aide ───────────────────────────────────────────────────────
        if (self.frame // 25) % 2 == 0:
            aide = police(28).render("R = rejouer   |   ESC = retour au menu", True, BLANC)
            ecran.blit(aide, aide.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 + 155)))


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
        self.longueur_niveau = config_niveau.get("longueur", 14000)
        self.distance        = 0.0
        self.vitesse         = config_niveau.get("vitesse",      3.8)
        self.vitesse_max     = config_niveau.get("vitesse_max",  5.8)
        self.acceleration    = config_niveau.get("acceleration", 0.0007)

        # Y-sol calibrés sur la ligne de brique du Background_lvl1
        # (88-90 % de chaque demi-hauteur = ~342 px / ~726 px)
        self.y_sol_j1 = int(HAUTEUR * 0.445)
        self.y_sol_j2 = min(int(HAUTEUR * 0.945), HAUTEUR - 43)

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

        # Vies issues de la config du niveau (5 en easy, 3 en hard...)
        vies_niveau = config_niveau.get("vies", 3)
        self.joueur1.vies = vies_niveau
        self.joueur1.VIES_MAX = vies_niveau
        self.joueur2.vies = vies_niveau
        self.joueur2.VIES_MAX = vies_niveau

        gap_min           = config_niveau.get("gap_min", 400)
        gap_max           = config_niveau.get("gap_max", 560)
        generer_obstacles = config_niveau.get("generer_obstacles", True)
        palette_j1, palette_j2 = self.fond.palettes_obstacles()
        self.circuit_j1 = Circuit(
            self.y_sol_j1, self.longueur_niveau, gap_min, gap_max,
            generer_obstacles, obstacle_palette=palette_j1,
        )
        self.circuit_j2 = Circuit(
            self.y_sol_j2, self.longueur_niveau, gap_min, gap_max,
            generer_obstacles, obstacle_palette=palette_j2,
        )

        # Pistes de sol
        self.piste_j1 = PisteSol(self.y_sol_j1)
        self.piste_j2 = PisteSol(self.y_sol_j2)

        # ── IA J2 : activée par défaut → solo-friendly ──────────────────────
        self.ai_j2          = config_niveau.get("ai_j2", True)
        self.j2_manuel_detecte = False   # désactive l'IA si J2 appuie sur ses touches

        # ── Score pièces ────────────────────────────────────────────────────
        self.score_pieces = 0

        # ── Ligne d'arrivée ─────────────────────────────────────────────────
        # Placée en coordonnées monde : quand distance == longueur_niveau,
        # elle se trouve à x = longueur_niveau + 220 - longueur_niveau = 220
        # → pile sous le joueur, comme si on la franchit.
        self.finish_x = float(self.longueur_niveau + 260)

        # ── Milestones (25 % / 50 % / 75 %) ─────────────────────────────────
        self._milestones       = {int(self.longueur_niveau * p) for p in (0.25, 0.50, 0.75)}
        self._milestone_flash  = 0     # frames restantes d'affichage
        self._milestone_texte  = ""

        self.game_over   = False
        self.victoire    = False
        self.frame       = 0
        self.particules: list[Particule] = []
        self.offset_piste = 0.0

        self.countdown_frames = self.COUNTDOWN_DUREE * FPS
        self.en_jeu           = False
        self.ecran_fin: EcranFin | None = None
        self.derniere_seconde = self.COUNTDOWN_DUREE

    @property
    def termine(self):
        return self.game_over or self.victoire

    def _terminer(self, victoire: bool):
        self.game_over = not victoire
        self.victoire  = victoire
        self.ecran_fin = EcranFin(
            victoire, self.nom_niveau,
            score_pieces=self.score_pieces,
            score_distance=int(self.distance / 10),
        )
        SONS.play("win" if victoire else "lose")

    # ── IA simple pour J2 ────────────────────────────────────────────────────
    def _ia_touches_j2(self, touches_reelles):
        """Génère de fausses touches pour J2 en fonction des obstacles proches."""
        overrides = {}
        j2_x = self.joueur2.x
        obs_proches = [
            o for o in self.circuit_j2.obstacles
            if 90 <= o.x - j2_x <= 310
        ]
        if obs_proches:
            obs  = min(obs_proches, key=lambda o: o.x)
            dist = obs.x - j2_x
            if obs.type == "low" and dist <= 230 and self.joueur2.sur_sol:
                overrides[pygame.K_UP]   = True
                overrides[pygame.K_DOWN] = False
            elif obs.type == "high" and dist <= 200 and self.joueur2.sur_sol:
                overrides[pygame.K_DOWN] = True
                overrides[pygame.K_UP]   = False
        return FauxTouches(touches_reelles, overrides)

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

        # ── Détection jeu manuel J2 ──────────────────────────────────────────
        if touches[pygame.K_UP] or touches[pygame.K_DOWN]:
            self.j2_manuel_detecte = True

        # ── Mise à jour joueurs ──────────────────────────────────────────────
        self.joueur1.update(touches)
        if self.ai_j2 and not self.j2_manuel_detecte:
            self.joueur2.update(self._ia_touches_j2(touches))
        else:
            self.joueur2.update(touches)

        if self.joueur1.vient_de_sauter or self.joueur2.vient_de_sauter:
            SONS.play("jump")

        # ── Accélération ────────────────────────────────────────────────────
        if self.vitesse < self.vitesse_max:
            self.vitesse += self.acceleration

        self.offset_piste += self.vitesse
        self.fond.update(self.vitesse)
        self.piste_j1.update(self.vitesse)
        self.piste_j2.update(self.vitesse)
        self.circuit_j1.update(self.vitesse)
        self.circuit_j2.update(self.vitesse)
        self.distance += self.vitesse

        # ── Ligne d'arrivée (avance avec les obstacles) ──────────────────────
        self.finish_x -= self.vitesse

        # ── Particules ──────────────────────────────────────────────────────
        for p in self.particules:
            p.update()
        self.particules = [p for p in self.particules if p.vie > 0]

        # ── Milestones ──────────────────────────────────────────────────────
        dist_int = int(self.distance)
        for ms in list(self._milestones):
            if dist_int >= ms:
                self._milestones.discard(ms)
                pct = int(ms / self.longueur_niveau * 100)
                self._milestone_texte = f"{pct}% !"
                self._milestone_flash = 90
                SONS.play("countdown")

        if self._milestone_flash > 0:
            self._milestone_flash -= 1

        # ── Collisions J1 ────────────────────────────────────────────────────
        rect1 = self.joueur1.get_rect().inflate(-16, -18)
        for obs in self.circuit_j1.obstacles:
            if rect1.colliderect(obs.get_rect()):
                if self.joueur1.touche():
                    SONS.play("hit")
                    self._spawn_particules(self.joueur1)
                    if not self.joueur1.en_vie:
                        self._terminer(False)
                        return

        # ── Collisions J2 : sa mort = game over pour les deux ──────────────
        rect2 = self.joueur2.get_rect().inflate(-16, -18)
        for obs in self.circuit_j2.obstacles:
            if rect2.colliderect(obs.get_rect()):
                if self.joueur2.touche():
                    SONS.play("hit")
                    self._spawn_particules(self.joueur2)
                    if not self.joueur2.en_vie:
                        self._terminer(False)
                        return

        # ── Collecte des pièces ──────────────────────────────────────────────
        for circuit, joueur in ((self.circuit_j1, self.joueur1),
                                (self.circuit_j2, self.joueur2)):
            if not joueur.en_vie:
                continue
            jrect = joueur.get_rect()
            for piece in circuit.pieces:
                if not piece.collectee and jrect.colliderect(piece.get_rect()):
                    piece.collectee = True
                    self.score_pieces += 1
                    # Petites particules dorées
                    for _ in range(8):
                        self.particules.append(
                            Particule(piece.x, piece.y, (255, 215, 0))
                        )

        # ── Victoire : J1 atteint la fin ─────────────────────────────────────
        if self.distance >= self.longueur_niveau:
            self._terminer(True)

    def _spawn_particules(self, joueur):
        rect = joueur.get_rect()
        for _ in range(22):
            c = random.choice([ROUGE, ORANGE, JAUNE])
            self.particules.append(Particule(rect.centerx, rect.centery, c))

    # ── Dessin ───────────────────────────────────────────────────────────────
    def dessiner(self, ecran):
        self.fond.dessiner(ecran)

        pulse = int(60 * abs(((self.frame % 40) / 20) - 1))
        self.circuit_j1.dessiner(ecran, pulse)
        self.circuit_j2.dessiner(ecran, pulse)

        # Pistes de sol
        self.piste_j1.dessiner(ecran)
        self.piste_j2.dessiner(ecran)

        # ── Ligne d'arrivée ──────────────────────────────────────────────────
        if -50 < self.finish_x < LARGEUR + 50:
            lax = int(self.finish_x)
            tile = 24
            for yi in range(0, HAUTEUR, tile):
                col = BLANC if (yi // tile + (lax // tile)) % 2 == 0 else NOIR
                pygame.draw.rect(ecran, col, (lax - 15, yi, 30, tile))
            pygame.draw.rect(ecran, (255, 215, 0), (lax - 16, 0, 32, HAUTEUR), 2)
            txt_fin = police(38).render("FINISH!", True, (255, 215, 0))
            ecran.blit(txt_fin, txt_fin.get_rect(center=(lax, HAUTEUR // 2 - 20)))

        # ── Indicateur de zone d'arrivée (dernier 15 %) ──────────────────────
        if self.distance >= self.longueur_niveau * 0.85 and not self.termine:
            pct_fin = (self.distance - self.longueur_niveau * 0.85) / (self.longueur_niveau * 0.15)
            alpha_warn = int(min(1.0, pct_fin) * 180)
            warn_surf  = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
            warn_surf.fill((255, 215, 0, alpha_warn // 8))
            ecran.blit(warn_surf, (0, 0))
            txt_near = police(42).render("ARRIVÉE PROCHE !", True, (255, 215, 0))
            alpha_txt = int(abs(math.sin(self.frame * 0.10)) * 220)
            txt_near.set_alpha(alpha_txt)
            ecran.blit(txt_near, txt_near.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 - 70)))

        # ── Sillage de vitesse (traînées horizontales) ────────────────────────
        if self.vitesse > self.vitesse_max * 0.75 and self.en_jeu and not self.termine:
            ratio_spd = (self.vitesse - self.vitesse_max * 0.75) / (self.vitesse_max * 0.25)
            for _ in range(int(ratio_spd * 4)):
                ly = random.randint(80, HAUTEUR - 80)
                lx = random.randint(0, int(LARGEUR * 0.6))
                llen = random.randint(18, 55)
                alpha_l = random.randint(35, 90)
                ls = pygame.Surface((llen, 2), pygame.SRCALPHA)
                ls.fill((255, 255, 255, alpha_l))
                ecran.blit(ls, (lx, ly))

        # ── Joueurs ──────────────────────────────────────────────────────────
        self.joueur1.dessiner(ecran)
        self.joueur2.dessiner(ecran)

        # ── Particules ──────────────────────────────────────────────────────
        for p in self.particules:
            p.dessiner(ecran)

        # ── Flash milestone ──────────────────────────────────────────────────
        if self._milestone_flash > 0:
            a = int((self._milestone_flash / 90) * 200)
            ms_surf = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
            ms_surf.fill((255, 215, 0, a // 6))
            ecran.blit(ms_surf, (0, 0))
            ms_txt = police(72).render(self._milestone_texte, True, JAUNE)
            ms_txt.set_alpha(a)
            ecran.blit(ms_txt, ms_txt.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 - 50)))

        # ── Danger flash (vie critique) ──────────────────────────────────────
        if self.joueur1.vies == 1 and self.frame % 20 < 10:
            danger = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
            danger.fill((255, 0, 0, 28))
            ecran.blit(danger, (0, 0))

        # ── HUD ─────────────────────────────────────────────────────────────
        compte_rebours_affiche = 0
        if not self.en_jeu:
            compte_rebours_affiche = max(1, int(math.ceil(self.countdown_frames / FPS)))

        dessiner_hud(ecran, self.joueur1, self.joueur2,
                     self.distance, self.longueur_niveau,
                     self.vitesse, self.vitesse_max,
                     self.nom_niveau, compte_rebours_affiche,
                     self.score_pieces)

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
