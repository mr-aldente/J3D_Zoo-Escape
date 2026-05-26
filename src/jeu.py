"""
jeu.py — Moteur de jeu Zoo Escape
===================================
Contient toute la logique du jeu :
  - Définition des niveaux (NIVEAUX)
  - Génération procédurale des sons (GestionnaireSons)
  - Rendu du décor : Skybox, PisteSol, dessiner_bords
  - Joueur avec animations sprite et physique (saut, slide)
  - Obstacles et pièces collectibles (Circuit)
  - IA équilibrée pour le joueur 2 (IAJoueur2 + FauxTouches)
  - HUD et écran de fin (EcranFin)
  - Boucle principale du jeu (lancer_jeu)

Ce module est importé par menu.py, qui gère l'écran titre et les paramètres.
"""

import math
import random
import os
from array import array
from collections import deque

import pygame

import app_paths

# ── Constantes globales ────────────────────────────────────────────────────────
# Ces valeurs sont écrasées depuis menu.py selon la résolution choisie.
LARGEUR = 1024
HAUTEUR = 768
FPS = 144

# Frames attendues par personnage (dossiers assets/{dossier}/)
PERSONNAGE_ANIM = {
    "Fox":     {"run": 6, "jump": 5, "slide": 5},
    "Raton":   {"run": 6, "jump": 5, "slide": 4},
    "Shark":   {"run": 6, "jump": 6, "slide": 4},
    "Parrot":  {"run": 6, "jump": 6, "slide": 4},
    "Lion":    {"run": 6, "jump": 6, "slide": 4},
    "Penguin": {"run": 6, "jump": 6, "slide": 4},
}

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

# Chaque niveau est un dict avec les clés suivantes :
#   nom             : texte affiché dans le HUD
#   biome           : thème visuel (savanna, arctic, jungle, aquatic, boss_zoo)
#   longueur        : distance totale à parcourir (en px monde)
#   vitesse         : vitesse de défilement initiale (px/frame)
#   vitesse_max     : vitesse maximale après accélération
#   acceleration    : augmentation de vitesse par frame
#   gap_min/gap_max : espacement min/max entre obstacles (px)
#   generer_obstacles: False → niveau de test sans danger
#   ai_j2           : True  → J2 est piloté par l'IA si le joueur ne touche pas ses touches
#   vies            : vies au démarrage (optionnel, défaut=3)
#   mode_boss       : True → mini-boss à la fin (niveau 5)
BIOMES = {
    "default": {
        "palette": {
            "low_body": (143, 94, 67), "low_outline": (90, 55, 28),
            "low_detail": (175, 118, 80), "low_cap": (185, 125, 75),
            "high_body": (118, 118, 118), "high_outline": (68, 68, 68),
            "high_leaf": (148, 148, 148), "high_glow": (210, 210, 210),
        },
        "low_subtypes": ("crate", "barrel", "wall"),
        "high_subtypes": ("stalactite", "beam"),
        "ground": ((60, 38, 22), (155, 100, 62), (115, 74, 44), (60, 38, 22)),
        "tint": None,
    },
    "savanna": {
        "palette": {
            "low_body": (180, 130, 70), "low_outline": (110, 75, 35),
            "low_detail": (210, 165, 95), "low_cap": (220, 180, 110),
            "high_body": (120, 90, 55), "high_outline": (70, 50, 30),
            "high_leaf": (80, 140, 50), "high_glow": (180, 150, 90),
        },
        "low_subtypes": ("cactus", "rock", "crate"),
        "high_subtypes": ("branch", "vulture_nest"),
        "ground": ((90, 60, 30), (200, 160, 90), (160, 120, 70), (80, 50, 25)),
        "tint": (255, 210, 140, 18),
    },
    "arctic": {
        "palette": {
            "low_body": (190, 220, 245), "low_outline": (120, 160, 200),
            "low_detail": (230, 245, 255), "low_cap": (240, 250, 255),
            "high_body": (160, 210, 240), "high_outline": (90, 140, 190),
            "high_leaf": (200, 235, 255), "high_glow": (245, 252, 255),
        },
        "low_subtypes": ("iceberg", "snow_block", "icicle_ground"),
        "high_subtypes": ("icicle", "snow_overhang"),
        "ground": ((140, 170, 195), (230, 240, 250), (200, 220, 235), (100, 130, 160)),
        "tint": (180, 220, 255, 22),
    },
    "jungle": {
        "palette": {
            "low_body": (90, 65, 35), "low_outline": (50, 35, 18),
            "low_detail": (120, 90, 50), "low_cap": (130, 100, 60),
            "high_body": (40, 110, 45), "high_outline": (25, 70, 30),
            "high_leaf": (60, 160, 65), "high_glow": (100, 200, 90),
        },
        "low_subtypes": ("log", "vine_mound", "rock"),
        "high_subtypes": ("hanging_vine", "branch"),
        "ground": ((35, 55, 25), (80, 120, 50), (55, 85, 35), (25, 40, 18)),
        "tint": (60, 180, 80, 16),
    },
    "aquatic": {
        "palette": {
            "low_body": (230, 120, 100), "low_outline": (160, 70, 55),
            "low_detail": (255, 170, 140), "low_cap": (255, 200, 170),
            "high_body": (70, 160, 210), "high_outline": (35, 100, 150),
            "high_leaf": (120, 200, 240), "high_glow": (180, 230, 255),
        },
        "low_subtypes": ("coral", "seaweed_crate", "barrel"),
        "high_subtypes": ("jellyfish", "anchor"),
        "ground": ((30, 70, 110), (60, 130, 180), (45, 100, 150), (20, 50, 80)),
        "tint": (40, 120, 200, 20),
    },
    "boss_zoo": {
        "palette": {
            "low_body": (140, 140, 150), "low_outline": (70, 70, 80),
            "low_detail": (180, 180, 190), "low_cap": (200, 200, 210),
            "high_body": (200, 50, 50), "high_outline": (120, 20, 20),
            "high_leaf": (255, 200, 50), "high_glow": (255, 230, 120),
        },
        "low_subtypes": ("cage", "barrier", "sandbag"),
        "high_subtypes": ("spotlight", "cage_hanging"),
        "ground": ((50, 50, 60), (120, 120, 130), (80, 80, 90), (35, 35, 45)),
        "tint": (180, 40, 60, 24),
    },
}

NIVEAUX = {
    0: {
        "nom": "ANIMATION TEST",
        "biome": "default",
        "longueur": 6000,
        "vitesse": 3.5,
        "vitesse_max": 5.0,
        "acceleration": 0.0006,
        "gap_min": 300,
        "gap_max": 420,
        "generer_obstacles": False,
        "generer_gardes": False,
        "ai_j2": True,
    },
    1: {
        "nom": "Savanna",
        "biome": "savanna",
        "longueur": 8500,
        "vitesse": 3.6,
        "vitesse_max": 5.8,
        "acceleration": 0.00065,
        "gap_min": 700,
        "gap_max": 950,
        "generer_obstacles": True,
        "generer_gardes": True,
        "ai_j2": True,
        "vies": 5,
    },
    2: {
        "nom": "Arctic",
        "biome": "arctic",
        "longueur": 16000,
        "vitesse": 4.4,
        "vitesse_max": 7.0,
        "acceleration": 0.0010,
        "gap_min": 500,
        "gap_max": 700,
        "generer_obstacles": True,
        "generer_gardes": True,
        "ai_j2": True,
    },
    3: {
        "nom": "Jungle",
        "biome": "jungle",
        "longueur": 18000,
        "vitesse": 5.0,
        "vitesse_max": 8.2,
        "acceleration": 0.0013,
        "gap_min": 420,
        "gap_max": 600,
        "generer_obstacles": True,
        "generer_gardes": True,
        "ai_j2": True,
    },
    4: {
        "nom": "Aquatic",
        "biome": "aquatic",
        "longueur": 24000,
        "vitesse": 5.8,
        "vitesse_max": 9.5,
        "acceleration": 0.0016,
        "gap_min": 350,
        "gap_max": 520,
        "generer_obstacles": True,
        "generer_gardes": True,
        "ai_j2": True,
    },
    5: {
        "nom": "Directeur Magnus",
        "biome": "boss_zoo",
        "longueur": 26000,
        "vitesse": 4.5,
        "vitesse_max": 6.5,
        "acceleration": 0.0008,
        "gap_min": 450,
        "gap_max": 650,
        "generer_obstacles": True,
        "generer_gardes": True,
        "ai_j2": True,
        "mode_boss": True,
        "boss_zone_pct": 0.25,
        "boss_run_after": 0,
    },
}

# ──────────────────────────────────────────────
#  Polices pré-créées (évite de les recréer à chaque frame)
# ──────────────────────────────────────────────
_POLICES: dict = {}
_VOLUME_EFFETS = 0.7


class GestionnaireSons:
    """
    Génère tous les effets sonores du jeu de façon procédurale (pas de fichiers .wav).
    Les sons sont produits par synthèse : on remplit un buffer PCM 16-bit avec
    des formes d'onde (sinus, carré, triangle) puis on crée un pygame.mixer.Sound.

    Sons disponibles : "jump", "hit", "win", "lose", "countdown"
    """
    def __init__(self):
        self.actif = pygame.mixer.get_init() is not None
        self.sons = {}
        if self.actif:
            self._creer_sons()
            self.set_volume(_VOLUME_EFFETS)

    def _generer_tonalite(self, frequence, duree=0.16, volume=0.35, forme="sine", glide=0.0):
        # glide : décalage de fréquence total sur toute la durée (glissando).
        # L'enveloppe multiplie le volume : montée rapide (8 %) puis descente linéaire.
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
    """
    Émule le tableau de touches retourné par pygame.key.get_pressed() pour l'IA de J2.

    L'IA construit un dict d'overrides (ex: {K_UP: True}) et le passe ici.
    Quand le joueur 2 est testé avec `touches[K_UP]`, c'est cette classe qui répond,
    ce qui permet de simuler une pression de touche sans input réel du clavier.
    """
    def __init__(self, base, overrides: dict):
        self._base = base
        self._overrides = overrides

    def __getitem__(self, key):
        return self._overrides.get(key, self._base[key])


class IAJoueur2:
    """
    IA J2 (piste du bas). Mode fiable (solo + IA) : termine le niveau sans mourir,
    avec sauts/glissades légèrement décalés dans le temps pour paraître humains.
    """
    SAUT_KEY = pygame.K_UP
    SLIDE_KEY = pygame.K_DOWN

    def __init__(self, skill: float = 0.62, rng: random.Random | None = None, fiable: bool = False):
        self.fiable = fiable
        self.skill = max(0.48, min(0.82, skill))
        self._rng = rng if rng is not None else random.Random()
        self._plans: dict[int, dict] = {}
        self._slide_hold = 0
        self._tick = 0
        self._lock_obs = None

    def reset(self) -> None:
        self._plans.clear()
        self._slide_hold = 0
        self._tick = 0
        self._lock_obs = None

    def _nettoyer_plans(self, jx: float) -> None:
        morts = []
        for oid, plan in self._plans.items():
            obs = plan.get("obs")
            if obs is None or obs.x + getattr(obs, "largeur", 70) < jx - 80:
                morts.append(oid)
        for oid in morts:
            del self._plans[oid]

    def _enregistrer_obstacles(self, joueur, circuit, jx: float, vitesse: float,
                               extra_obstacles=None) -> None:
        horizon = 420 + vitesse * 38 if self.fiable else 280 + vitesse * 26
        toutes_obs = list(circuit.obstacles)
        if extra_obstacles:
            toutes_obs.extend(extra_obstacles)
        for obs in toutes_obs:
            dist = obs.x - jx
            if dist < 50 or dist > horizon:
                continue
            oid = id(obs)
            if oid in self._plans:
                continue
            action = "jump" if obs.type == "low" else "slide"
            if self.fiable:
                if action == "jump":
                    lo = int(165 + vitesse * 13)
                    hi = int(270 + vitesse * 22)
                else:
                    lo = int(145 + vitesse * 12)
                    hi = int(280 + vitesse * 22)
                trigger = self._rng.randint(lo, hi)
            else:
                if action == "jump":
                    lo = int(95 + vitesse * 18 + self.skill * 20)
                    hi = int(lo + 45)
                else:
                    lo = int(78 + vitesse * 15 + self.skill * 18)
                    hi = int(lo + 38)
                trigger = self._rng.randint(lo, hi)
            self._plans[oid] = {"action": action, "trigger": trigger, "obs": obs}

    def _urgence_obstacle(self, joueur, circuit, jx: float, vitesse: float, extra_obstacles=None):
        toutes_obs = list(circuit.obstacles)
        if extra_obstacles:
            toutes_obs.extend(extra_obstacles)
        for obs in toutes_obs:
            dist = obs.x - jx
            if dist > 120 or dist < -10:
                continue
            if obs.type == "low" and dist < 110 + vitesse * 7:
                return "jump", dist
            if obs.type == "high" and dist < 105 + vitesse * 7:
                return "slide", dist
        return None

    def _urgence_projectile(self, joueur, circuit, jx: float, vitesse: float,
                            extra_projectiles=None):
        meilleur = None
        projs = []
        for garde in circuit.gardes:
            projs.extend(garde.projectiles)
        if extra_projectiles:
            projs.extend(extra_projectiles)
        for proj in projs:
            if not proj.actif:
                continue
            dist = proj.x - jx
            if dist < -20 or dist > 320:
                continue
            haut = joueur.y_sol - Garde._TIR_OFFSET
            if abs(proj.y - haut) > 30 and abs(proj.y - (joueur.y_sol - 30)) > 30:
                continue
            lim = (175 + vitesse * 14) if proj.type_proj == "rapide" else (145 + vitesse * 11)
            if self.fiable:
                lim += 35
            if dist <= lim:
                if meilleur is None or dist < meilleur[1]:
                    meilleur = ("slide", dist)
        return meilleur

    def _obstacles_visibles(self, jx: float, vitesse: float):
        horizon = 450 + vitesse * 40 if self.fiable else 300 + vitesse * 28
        lows, highs = [], []
        for obs in self._plans.values():
            o = obs["obs"]
            d = o.x - jx
            if 0 < d <= horizon:
                (lows if o.type == "low" else highs).append((d, o))
        lows.sort()
        highs.sort()
        return lows, highs

    def _doit_annuler_slide(self, joueur, circuit, jx: float, vitesse: float,
                            extra_obstacles=None) -> bool:
        """Glissade en cours mais obstacle bas imminent → repasser en saut."""
        obs_list = list(circuit.obstacles)
        if extra_obstacles:
            obs_list.extend(extra_obstacles)
        for obs in obs_list:
            if obs.type != "low":
                continue
            d = obs.x - jx
            if 0 < d < 140 + vitesse * 10:
                return True
        return False

    def _choisir_action(self, joueur, jx: float, vitesse: float, lows, highs):
        """Priorité : glissade sous le haut si proche, sinon saut par-dessus le bas."""
        slide_zone = (220 + vitesse * 16) if self.fiable else (160 + vitesse * 12)
        jump_urg = 105 + vitesse * 8
        slide_urg = 110 + vitesse * 8
        slide_plan = None
        jump_plan = None

        for plan in self._plans.values():
            d = plan["obs"].x - jx
            if d <= 0:
                continue
            if plan["action"] == "slide" and d <= plan["trigger"]:
                slide_plan = d if slide_plan is None else min(slide_plan, d)
            if plan["action"] == "jump" and d <= plan["trigger"]:
                jump_plan = d if jump_plan is None else min(jump_plan, d)

        hd = highs[0][0] if highs else 9999.0
        ld = lows[0][0] if lows else 9999.0

        if joueur.sur_sol and highs and hd <= slide_zone:
            if ld > 90 + vitesse * 6 or hd <= ld:
                return "slide"

        if lows and ld <= jump_urg + 40:
            if joueur.sur_sol and highs and hd < 200 + vitesse * 12 and hd < ld - 15:
                return "slide"

        if highs and hd <= slide_urg:
            return "slide"
        if slide_plan is not None and hd <= slide_plan + 50:
            return "slide"

        if lows and (ld <= jump_urg or jump_plan is not None):
            if joueur.sur_sol and highs and hd < ld and hd < slide_zone:
                return "slide"
            return "jump"

        if slide_plan is not None:
            return "slide"
        if jump_plan is not None:
            return "jump"
        return None

    def _anticipation_projectile(self, joueur, circuit, jx: float, vitesse: float):
        """Glissade anticipée (avant la zone d'urgence) pour paraître naturel."""
        if not self.fiable:
            return None
        meilleur = None
        for garde in circuit.gardes:
            for proj in garde.projectiles:
                if not proj.actif:
                    continue
                dist = proj.x - jx
                if dist < 10 or dist > 360:
                    continue
                haut = joueur.y_sol - Garde._TIR_OFFSET
                if abs(proj.y - haut) > 24:
                    continue
                if proj.type_proj == "rapide":
                    zone = 240 + vitesse * 16
                else:
                    zone = 200 + vitesse * 13
                if dist <= zone:
                    if meilleur is None or dist < meilleur:
                        meilleur = dist
        return "slide" if meilleur is not None else None

    def _appliquer_saut(self, joueur, overrides: dict, urgent: bool) -> None:
        """Impulsions répétées sur ↑ (front montant) + jump-buffer en approche."""
        self._slide_hold = 0
        self._tick += 1
        if urgent or self.fiable:
            # Mode fiable / urgence : fronts montants fréquents + buffer en l'air
            cycle = self._tick % 4
            pulse = cycle in (0, 1) if joueur.sur_sol else (cycle in (0, 1, 2))
        elif joueur.sur_sol:
            pulse = (self._tick % 6 == 0)
        else:
            pulse = (self._tick % 4 == 0)
        overrides[self.SAUT_KEY] = pulse
        overrides[self.SLIDE_KEY] = False

    def _appliquer_slide(self, joueur, overrides: dict, urgent: bool) -> None:
        duree = max(20, joueur.slide_duree_min + 10)
        if urgent or self.fiable:
            duree = max(duree, joueur.slide_duree_min + 18)
        if self.fiable and self._lock_obs is not None and getattr(self._lock_obs, "type", None) == "high":
            duree = max(duree, joueur.slide_duree_min + 28)
        self._slide_hold = max(self._slide_hold, duree)
        overrides[self.SLIDE_KEY] = True
        overrides[self.SAUT_KEY] = False

    def _decider_fiable(self, joueur, circuit, jx: float, vitesse: float,
                        extra_obstacles=None, extra_projectiles=None) -> dict:
        """Mode solo+IA : franchit le niveau ; timing de saut/glissade légèrement variable."""
        overrides: dict = {}
        obs_list = list(circuit.obstacles)
        if extra_obstacles:
            obs_list.extend(extra_obstacles)
        projs = []
        for g in circuit.gardes:
            projs.extend(g.projectiles)
        if extra_projectiles:
            projs.extend(extra_projectiles)

        # Urgence : menace la plus proche, glissade prioritaire sous les obstacles hauts
        menaces_urg = []
        for obs in obs_list:
            dist = obs.x - jx
            if dist < -25 or dist > 155 + vitesse * 10:
                continue
            menaces_urg.append((dist, obs))
        menaces_urg.sort(key=lambda t: t[0])
        if menaces_urg:
            highs_u = [(d, o) for d, o in menaces_urg if o.type == "high"]
            lows_u  = [(d, o) for d, o in menaces_urg if o.type == "low"]
            zone_h = 210 + vitesse * 15
            zone_l = 155 + vitesse * 10
            if highs_u and highs_u[0][0] < zone_h:
                hd = highs_u[0][0]
                ld = lows_u[0][0] if lows_u else 9999.0
                if hd <= ld + 55 or hd < zone_h - 30:
                    self._lock_obs = highs_u[0][1]
                    self._appliquer_slide(joueur, overrides, urgent=hd < 115)
                    return overrides
            if lows_u and lows_u[0][0] < zone_l:
                self._lock_obs = lows_u[0][1]
                self._appliquer_saut(joueur, overrides, urgent=lows_u[0][0] < 120)
                return overrides
            if highs_u and joueur.sur_sol and highs_u[0][0] < zone_h:
                self._lock_obs = highs_u[0][1]
                self._appliquer_slide(joueur, overrides, urgent=True)
                return overrides
            if highs_u and not joueur.sur_sol and highs_u[0][0] < 125 + vitesse * 8:
                self._lock_obs = highs_u[0][1]
                self._appliquer_slide(joueur, overrides, urgent=True)
                return overrides

        # ── Engagement en cours ───────────────────────────────────────────────
        if self._lock_obs is not None:
            obs = self._lock_obs
            dist = obs.x - jx
            largeur = getattr(obs, "largeur", 70)
            if obs.type == "high":
                marge = 58 + int(vitesse * 4)
                if obs.x + largeur < jx - marge:
                    self._lock_obs = None
                    self._slide_hold = 0
                else:
                    self._appliquer_slide(joueur, overrides, urgent=dist < 100)
                    return overrides
            elif obs.x + largeur < jx - 28 or dist <= -18:
                self._lock_obs = None
                self._slide_hold = 0
            elif joueur.sur_sol:
                for o in obs_list:
                    if o.type != "high":
                        continue
                    hd = o.x - jx
                    if 0 < hd < 215 + vitesse * 14:
                        self._lock_obs = o
                        self._appliquer_slide(joueur, overrides, urgent=hd < 120)
                        return overrides
                self._appliquer_saut(joueur, overrides, urgent=(dist < 140))
                return overrides
            else:
                self._appliquer_saut(joueur, overrides, urgent=True)
                return overrides

        if self._slide_hold > 0:
            if self._doit_annuler_slide(joueur, circuit, jx, vitesse, extra_obstacles):
                self._lock_obs = None
                self._slide_hold = 0
                self._appliquer_saut(joueur, overrides, urgent=True)
                return overrides
            self._appliquer_slide(joueur, overrides, urgent=False)
            return overrides

        # ── Projectiles ───────────────────────────────────────────────────────
        meilleur_proj = None
        for proj in projs:
            if not proj.actif:
                continue
            dist = proj.x - jx
            if dist < -25 or dist > 360 + vitesse * 24:
                continue
            haut = joueur.y_sol - Garde._TIR_OFFSET
            if abs(proj.y - haut) > 28:
                continue
            if meilleur_proj is None or dist < meilleur_proj:
                meilleur_proj = dist
        if meilleur_proj is not None and meilleur_proj < 280 + vitesse * 20:
            self._appliquer_slide(joueur, overrides, urgent=meilleur_proj < 130)
            return overrides

        # ── Obstacles planifiés ───────────────────────────────────────────────
        horizon = 400 + vitesse * 34
        menaces = []
        for obs in obs_list:
            dist = obs.x - jx
            if 30 < dist <= horizon:
                menaces.append((dist, obs))
        menaces.sort(key=lambda t: t[0])
        if not menaces:
            return overrides

        dist, obs = menaces[0]
        oid = id(obs)
        if oid not in self._plans:
            if obs.type == "low":
                lo, hi = int(230 + vitesse * 20), int(340 + vitesse * 28)
            else:
                lo, hi = int(220 + vitesse * 19), int(335 + vitesse * 27)
            self._plans[oid] = {
                "action": "jump" if obs.type == "low" else "slide",
                "trigger": self._rng.randint(lo, hi),
                "obs": obs,
            }
        trigger = self._plans[oid]["trigger"]

        highs = [(d, o) for d, o in menaces if o.type == "high"]
        lows  = [(d, o) for d, o in menaces if o.type == "low"]

        if highs and joueur.sur_sol:
            hd, hobs = highs[0]
            if hd <= trigger or hd <= 240 + vitesse * 16:
                if not lows or hd <= lows[0][0] + 40:
                    self._lock_obs = hobs
                    self._appliquer_slide(joueur, overrides, urgent=False)
                    return overrides

        if obs.type == "low" and dist <= trigger:
            if joueur.sur_sol or dist < 150:
                self._lock_obs = obs
                self._appliquer_saut(joueur, overrides, urgent=False)
            return overrides

        if obs.type == "high" and dist <= trigger and joueur.sur_sol:
            self._lock_obs = obs
            self._appliquer_slide(joueur, overrides, urgent=False)
            return overrides

        return overrides

    def decider(self, joueur, circuit, vitesse_jeu: float, _frame: int = 0,
                extra_obstacles=None, extra_projectiles=None) -> dict:
        overrides: dict = {}
        if not joueur.en_vie:
            return overrides

        vitesse = max(2.0, min(12.0, vitesse_jeu))
        jx = joueur.x

        if self.fiable:
            return self._decider_fiable(
                joueur, circuit, jx, vitesse, extra_obstacles, extra_projectiles,
            )

        if self._slide_hold > 0:
            if self._doit_annuler_slide(joueur, circuit, jx, vitesse, extra_obstacles):
                self._slide_hold = 0
                self._appliquer_saut(joueur, overrides, urgent=True)
                return overrides
            self._slide_hold -= 1
            overrides[self.SLIDE_KEY] = True
            overrides[self.SAUT_KEY] = False
            return overrides

        self._nettoyer_plans(jx)
        self._enregistrer_obstacles(joueur, circuit, jx, vitesse, extra_obstacles)

        urgence = self._urgence_obstacle(joueur, circuit, jx, vitesse, extra_obstacles)
        if urgence is None:
            urgence = self._urgence_projectile(joueur, circuit, jx, vitesse, extra_projectiles)

        if urgence is not None:
            action, _ = urgence
            if action == "jump":
                self._appliquer_saut(joueur, overrides, urgent=True)
            else:
                self._appliquer_slide(joueur, overrides, urgent=True)
            return overrides

        proj_action = self._anticipation_projectile(joueur, circuit, jx, vitesse)
        if proj_action == "slide" and joueur.sur_sol:
            self._appliquer_slide(joueur, overrides, urgent=False)
            return overrides

        lows, highs = self._obstacles_visibles(jx, vitesse)
        action = self._choisir_action(joueur, jx, vitesse, lows, highs)
        if action == "jump":
            if joueur.slide:
                return overrides
            self._appliquer_saut(joueur, overrides, urgent=False)
        elif action == "slide":
            if not joueur.sur_sol:
                return overrides
            self._appliquer_slide(joueur, overrides, urgent=False)

        return overrides


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
    def __init__(self, y_sol, ground_colors=None):
        self.y_sol = y_sol
        self.offset_anim = 0.0
        g = ground_colors or ((60, 38, 22), (155, 100, 62), (115, 74, 44), (60, 38, 22))
        self.col_dark, self.col_line, self.col_brick, self.col_border = g

    def update(self, vitesse):
        self.offset_anim += vitesse * 0.25

    def dessiner(self, ecran):
        pygame.draw.line(ecran, self.col_dark,  (0, self.y_sol),     (LARGEUR, self.y_sol),     4)
        pygame.draw.line(ecran, self.col_line, (0, self.y_sol + 1), (LARGEUR, self.y_sol + 1), 1)
        bw, bh = 52, 8
        off = int(self.offset_anim) % bw
        for row_i in range(2):
            roff = (bw // 2) * (row_i % 2)
            ry   = self.y_sol + 2 + row_i * bh
            for x in range(-bw + off + roff, LARGEUR + bw, bw):
                pygame.draw.rect(ecran, self.col_brick, (max(0, x), ry, bw - 3, bh - 2), border_radius=1)
                pygame.draw.rect(ecran, self.col_border,  (max(0, x), ry, bw - 3, bh - 2), 1, border_radius=1)


# ──────────────────────────────────────────────
#  SKYBOX (deux images: skybox0 en bas, Skybox1 en haut)
# ──────────────────────────────────────────────
class Skybox:
    def __init__(self, biome="default"):
        self.biome = biome
        self.tint = BIOMES.get(biome, BIOMES["default"]).get("tint")
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
            chemin_assets = os.path.join(app_paths.resource_dir(), "assets")
            
            # Mapping biome -> fichier image de niveau
            noms_images = {
                "default": "Background_lvl1.png",                               # Niveau 0 (test)
                "savanna": "Background_lvl1.png",                               # Niveau 1 - Savanna
                "arctic": "Niveau 2 fini(1)_0000.png",                          # Niveau 2 - Arctic
                "jungle": os.path.join("Niveau_3", "Niveau 3 fini_0000.png"),  # Niveau 3 - Jungle
                "aquatic": os.path.join("Niveau_4", "Niveau 4 fini_0000.png"), # Niveau 4 - Aquatic
                "boss_zoo": "Background_lvl1.png",                              # Boss (à définir plus tard)
            }
            
            nom_image = noms_images.get(self.biome, "Background_lvl1.png")
            chemin_image = os.path.join(chemin_assets, nom_image)
            
            image_chargee = self._charger_et_redimensionner(chemin_image)
            
            if image_chargee is not None:
                # Même fond pour les 2 zones (haut/bas), défilement synchronisé
                self.skybox1 = image_chargee
                self.skybox0 = image_chargee.copy()
            else:
                # Fallback sur les skybox par défaut si le fichier n'existe pas
                chemin_base = os.path.join(app_paths.resource_dir(), "assets", "Skybox_0000")
                chemin0 = os.path.join(chemin_base, "skybox0.png")
                chemin1 = os.path.join(chemin_base, "Skybox1.png")
                self.skybox0 = self._charger_et_redimensionner(chemin0)
                self.skybox1 = self._charger_et_redimensionner(chemin1)

            self.palette_obstacles_haut = self._construire_palette_obstacles(self.skybox1, (120, 135, 95))
            self.palette_obstacles_bas = self._construire_palette_obstacles(self.skybox0, (145, 110, 80))
        except Exception as e:
            print(f"Erreur chargement skybox: {e}")

    def update(self, vitesse_jeu):
        self.offset_x += max(0.0, vitesse_jeu) * self.coeff_scroll

    def palettes_obstacles(self):
        biome_pal = BIOMES.get(self.biome, BIOMES["default"])["palette"]
        return biome_pal, biome_pal

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

        if self.tint:
            overlay = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
            overlay.fill(self.tint)
            ecran.blit(overlay, (0, 0))


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
    """
    Représente un personnage jouable (J1 ou J2).

    Physique :
      - Gravité constante appliquée chaque frame (vy += gravite)
      - Saut : impulsion négative instantanée sur vy
      - Slide : hauteur réduite, durée minimale imposée pour l'animation

    Animations :
      - Priorité : dossier assets/{personnage}/ → sprites individuels PNG
      - Fallback 1 : Running_animation.png + Jumping_animation.png (bandes de frames)
      - Fallback 2 : animation.png (ancien format spritesheet)
      - Fallback 3 : rendu géométrique pygame (rectangles + cercles)

    Invincibilité post-coup : 90 frames (~0.6 s à 144 FPS), clignotement visible.
    """
    VIES_MAX = 3

    def __init__(self, x, y_sol, controles, nom, couleurs, personnage="Fox"):
        self.x = float(x)
        self.y_sol = y_sol     # Y du sol pour cette piste (ancre verticale)
        self.nom = nom
        self.couleurs = couleurs
        self.personnage = personnage if personnage in PERSONNAGE_ANIM else "Fox"
        self.controles = controles  # (touche_saut, touche_slide)

        self.largeur = 48
        self.hauteur = 66
        self.hauteur_slide = 36

        self.y = float(y_sol - self.hauteur)
        self.vy = 0.0
        self.gravite = 0.68      # gravité augmentée → sauts plus rapides
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

        # Anti-spam / cooldowns
        # cooldown_saut/slide : frames d'attente avant de pouvoir re-déclencher l'action.
        # saut_appui_precedent / slide_appui_precedent : détection du front montant (edge trigger)
        # afin de n'activer le saut/slide qu'à la pression initiale, pas au maintien.
        self.cooldown_saut = 0
        self.cooldown_slide = 0
        self.slide_timer = 0
        self.slide_duree_min = 14      # durée minimale d'un slide (ajustée selon le nb de frames d'anim)
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
        """
        Flood-fill depuis les bords de la surface pour rendre transparent
        tout pixel noir connecté au bord (fond d'image non masqué).
        Utile quand le sprite n'a pas de canal alpha propre.
        """
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
            dossier_courant = app_paths.resource_dir()
            anim = PERSONNAGE_ANIM[self.personnage]
            dossier_perso = os.path.join(dossier_courant, "assets", self.personnage)
            dossier_courir = os.path.join(dossier_perso, "Courir_animation")
            dossier_saut = os.path.join(dossier_perso, "Saut_animation")
            dossier_accroupi = os.path.join(dossier_perso, "accroupie_animation")

            self.running_frames = self._charger_frames_depuis_dossier(
                dossier_courir, anim["run"], 120,
            )
            self.jumping_frames = self._charger_frames_depuis_dossier(
                dossier_saut, anim["jump"], 126,
            )
            self.sliding_frames = self._charger_frames_depuis_dossier(
                dossier_accroupi, anim["slide"], 92,
            )

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
                            self.index_frame += 1
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
    Obstacles thématiques par biome.
    low  → sauter par-dessus   |   high → glisser en dessous
  """
    _LOW_DEFAULT  = ("crate", "barrel", "wall")
    _HIGH_DEFAULT = ("stalactite", "beam")

    def __init__(self, x, y_sol, obstacle_type, largeur=70, obstacle_palette=None, biome="default"):
        self.x       = float(x)
        self.y_sol   = y_sol
        self.type    = obstacle_type
        self.largeur = largeur
        self.biome   = biome

        biome_cfg = BIOMES.get(biome, BIOMES["default"])
        self.palette = obstacle_palette or biome_cfg["palette"]
        low_sub  = biome_cfg.get("low_subtypes",  self._LOW_DEFAULT)
        high_sub = biome_cfg.get("high_subtypes", self._HIGH_DEFAULT)

        if self.type == "low":
            self.hauteur = random.randint(40, 56)
            self.y       = y_sol - self.hauteur
            self.subtype = random.choice(low_sub)
        else:
            self.hauteur = random.randint(18, 26)
            self.y       = y_sol - random.randint(95, 110)
            self.subtype = random.choice(high_sub)

        self.anim = random.randint(0, 120)

    def deplacer(self, vitesse):
        self.x   -= vitesse
        self.anim = (self.anim + 1) % 120

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.largeur, self.hauteur)

    def _pal(self, key, default):
        return self.palette.get(key, default)

    def _dessiner_ombre(self, ecran, rect):
        pygame.draw.ellipse(ecran, (0, 0, 0),
                            (rect.x + 6, self.y_sol + 3, rect.width - 12, 9))

    def dessiner(self, ecran, pulse=0):
        """Formes simples (couleurs du biome) — le détail visuel est sur les personnages."""
        rect = self.get_rect()
        low_body = self._pal("low_body", (143, 94, 67))
        low_out = self._pal("low_outline", (90, 55, 28))
        hi_body = self._pal("high_body", (118, 118, 118))
        hi_out = self._pal("high_outline", (68, 68, 68))
        self._dessiner_ombre(ecran, rect)
        if self.type == "low":
            if self.subtype == "cage":
                pygame.draw.rect(ecran, low_body, rect, border_radius=4)
                pygame.draw.rect(ecran, low_out, rect, 2, border_radius=4)
                for bx in range(rect.x + 6, rect.right, 12):
                    pygame.draw.line(ecran, low_out, (bx, rect.y + 2), (bx, rect.bottom - 2), 2)
            else:
                pygame.draw.rect(ecran, low_body, rect, border_radius=6)
                pygame.draw.rect(ecran, low_out, rect, 2, border_radius=6)
        else:
            pts = [
                (rect.x, rect.y + 6), (rect.right, rect.y + 6),
                (rect.right - 8, rect.bottom), (rect.x + 8, rect.bottom),
            ]
            pygame.draw.polygon(ecran, hi_body, pts)
            pygame.draw.polygon(ecran, hi_out, pts, 2)


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
        bob = int(math.sin(self.anim * 0.10) * 3)
        cx, cy, r = int(self.x), int(self.y) + bob, self.rayon
        pygame.draw.circle(ecran, (255, 210, 50), (cx, cy), r)
        pygame.draw.circle(ecran, (180, 140, 20), (cx, cy), r, 2)


# ──────────────────────────────────────────────
#  PROJECTILE
# ──────────────────────────────────────────────
class Projectile:
    """
    Projectile tiré par un Garde ennemi vers la gauche (vers les joueurs).

    Deux types :
      "rapide" → petit (r=5), rapide, jaune/orange — tire fréquemment
      "lent"   → gros (r=13), lent, violet        — tire lentement

    Mécanique d'esquive : le projectile voyage à y = y_sol - 45, hauteur qui
    touche un joueur DEBOUT mais passe au-dessus d'un joueur ACCROUPI.
    """
    _COULEURS = {"rapide": (255, 200, 50), "lent": (175, 50, 255)}

    def __init__(self, x, y, type_proj):
        self.x          = float(x)
        self.y          = float(y)
        self.type_proj  = type_proj
        if type_proj == "rapide":
            self.vitesse_propre = 7
            self.rayon_visuel   = 5
            self.rayon_hitbox   = 5
        else:
            self.vitesse_propre = 2
            self.rayon_visuel   = 13
            self.rayon_hitbox   = 10   # hitbox légèrement réduite pour être fair
        self.couleur = self._COULEURS[type_proj]
        self.anim    = random.randint(0, 30)
        self.actif   = True

    def update(self, vitesse):
        self.x -= self.vitesse_propre + vitesse
        self.anim = (self.anim + 1) % 30
        if self.x < -80:
            self.actif = False

    def get_rect(self):
        r = self.rayon_hitbox
        return pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)

    def dessiner(self, ecran):
        cx, cy = int(self.x), int(self.y)
        spin = self.anim * 0.35
        if self.type_proj == "rapide":
            # Fléchette de tranquillisant
            cos_s, sin_s = math.cos(spin), math.sin(spin)
            pts = []
            for lx, ly in ((14, 0), (-8, -5), (-4, 0), (-8, 5)):
                pts.append((cx + lx * cos_s - ly * sin_s, cy + lx * sin_s + ly * cos_s))
            pygame.draw.polygon(ecran, (60, 160, 80), pts)
            pygame.draw.polygon(ecran, (30, 90, 45), pts, 2)
            pygame.draw.circle(ecran, (200, 240, 210), (int(cx - cos_s * 6), int(cy - sin_s * 6)), 4)
            for i in range(2):
                tx = cx + cos_s * (10 + i * 7)
                ty = cy + sin_s * (10 + i * 7)
                pygame.draw.circle(ecran, (120, 200, 140), (int(tx), int(ty)), 3 - i)
        else:
            # Filet de capture roulé
            pulse = int(abs(math.sin(self.anim * 0.18)) * 2)
            r = self.rayon_visuel + pulse
            pygame.draw.circle(ecran, (50, 90, 140), (cx, cy), r + 2)
            pygame.draw.circle(ecran, (100, 170, 220), (cx, cy), r)
            for i in range(4):
                ang = i * math.pi / 2 + spin * 0.5
                x1 = cx + int(math.cos(ang) * r)
                y1 = cy + int(math.sin(ang) * r)
                x2 = cx - int(math.cos(ang) * r)
                y2 = cy - int(math.sin(ang) * r)
                pygame.draw.line(ecran, (40, 70, 110), (x1, y1), (x2, y2), 2)
            pygame.draw.circle(ecran, (180, 220, 255), (cx - 3, cy - 3), max(3, r // 3))


class ProjectileBoss:
    """Projectiles du Directeur Magnus : plus gros et visuellement distincts des gardes."""

    _SPECS = {
        "boss_dart":      {"vx": 8,  "r_vis": 11, "r_hit": 9,  "couleur": (255, 60, 60)},
        "boss_net":       {"vx": 3,  "r_vis": 18, "r_hit": 14, "couleur": (90, 200, 255)},
        "boss_megaphone": {"vx": 6,  "r_vis": 15, "r_hit": 12, "couleur": (255, 210, 50)},
        "boss_staple":    {"vx": 9,  "r_vis": 10, "r_hit": 8,  "couleur": (180, 180, 200)},
    }

    def __init__(self, x, y, type_proj):
        spec = self._SPECS.get(type_proj, self._SPECS["boss_dart"])
        self.x = float(x)
        self.y = float(y)
        self.type_proj = type_proj
        self.vitesse_propre = spec["vx"]
        self.rayon_visuel = spec["r_vis"]
        self.rayon_hitbox = spec["r_hit"]
        self.couleur = spec["couleur"]
        self.anim = random.randint(0, 40)
        self.actif = True

    def update(self, vitesse):
        self.x -= self.vitesse_propre + vitesse
        self.anim = (self.anim + 1) % 60
        if self.x < -100:
            self.actif = False

    def get_rect(self):
        r = self.rayon_hitbox
        return pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)

    def dessiner(self, ecran):
        cx, cy = int(self.x), int(self.y)
        pulse = int(abs(math.sin(self.anim * 0.18)) * 3)
        wob = math.sin(self.anim * 0.12) * 4
        if self.type_proj == "boss_dart":
            # Feuille « INTERDIT » pliée en avion
            pts = [
                (cx + 16, cy + int(wob)), (cx - 12, cy - 10 + int(wob)),
                (cx - 6, cy + int(wob)), (cx - 12, cy + 10 + int(wob)),
            ]
            pygame.draw.polygon(ecran, (250, 245, 230), pts)
            pygame.draw.polygon(ecran, (200, 50, 50), pts, 2)
            pygame.draw.line(ecran, (220, 60, 60), (cx - 8, cy - 4 + int(wob)), (cx + 4, cy - 4 + int(wob)), 2)
            pygame.draw.line(ecran, (220, 60, 60), (cx - 8, cy + 2 + int(wob)), (cx + 2, cy + 2 + int(wob)), 2)
        elif self.type_proj == "boss_net":
            r = self.rayon_visuel + pulse
            surf = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            mid = r + 4
            for i in range(5):
                off = -r + i * (2 * r // 4)
                pygame.draw.line(surf, (80, 140, 200, 200), (mid + off, 4), (mid + off, r * 2), 2)
                pygame.draw.line(surf, (80, 140, 200, 200), (4, mid + off), (r * 2, mid + off), 2)
            pygame.draw.rect(surf, (120, 180, 230, 90), (4, 4, r * 2, r * 2), 2, border_radius=4)
            ecran.blit(surf, (cx - mid, cy - mid))
        elif self.type_proj == "boss_megaphone":
            for i in range(4):
                rr = 8 + i * 9 + pulse
                col = (255, 200 - i * 30, 60 - i * 10)
                pygame.draw.arc(ecran, col, (cx - rr, cy - rr, rr * 2, rr * 2), -0.55, 0.55, 4 - i)
            pygame.draw.polygon(ecran, (200, 40, 40), [
                (cx + 14, cy), (cx + 2, cy - 8), (cx + 2, cy + 8),
            ])
            pygame.draw.ellipse(ecran, (240, 200, 50), (cx - 2, cy - 6, 10, 12))
        else:
            # Trousseau de clés du directeur
            ang = self.anim * 0.3
            pygame.draw.circle(ecran, (180, 150, 50), (cx, cy), 5)
            for i, la in enumerate((0, 1.2, 2.4)):
                kx = cx + int(math.cos(ang + la) * 10)
                ky = cy + int(math.sin(ang + la) * 8)
                pygame.draw.circle(ecran, (200, 200, 210), (kx, ky), 4)
                pygame.draw.circle(ecran, (120, 120, 130), (kx, ky), 4, 1)
                pygame.draw.line(ecran, (160, 160, 170), (cx, cy), (kx, ky), 2)


class ProjectileJoueur:
    """Projectile visé vers le boss : direction initiale + léger homing."""

    VITESSE = 11.5

    def __init__(self, x, y, couleur, cible_x: float, cible_y: float):
        self.x = float(x)
        self.y = float(y)
        self.couleur = couleur
        self.cible_x = float(cible_x)
        self.cible_y = float(cible_y)
        dx = self.cible_x - self.x
        dy = self.cible_y - self.y
        dist = math.hypot(dx, dy)
        if dist < 12:
            dx = max(12.0, self.cible_x - self.x)
            dy = self.cible_y - self.y
            dist = math.hypot(dx, dy) or 12.0
        self.vx = dx / dist * self.VITESSE
        self.vy = dy / dist * self.VITESSE
        self.rayon = 8
        self.anim = random.randint(0, 20)
        self.actif = True
        self.angle = math.atan2(self.vy, self.vx)

    def update(self, cible_x=None, cible_y=None):
        if cible_x is not None and cible_y is not None:
            dx = cible_x - self.x
            dy = cible_y - self.y
            dist = math.hypot(dx, dy)
            if dist > 4:
                self.vx += (dx / dist) * 0.65
                self.vy += (dy / dist) * 0.65
                spd = math.hypot(self.vx, self.vy) or 1
                self.vx = self.vx / spd * self.VITESSE
                self.vy = self.vy / spd * self.VITESSE
                self.angle = math.atan2(self.vy, self.vx)
        self.x += self.vx
        self.y += self.vy
        self.anim += 1
        if self.x > LARGEUR + 50 or self.y < -40 or self.y > HAUTEUR + 40:
            self.actif = False

    def get_rect(self):
        r = self.rayon
        return pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)

    def _rot_point(self, cx, cy, lx, ly, cos_a, sin_a):
        return (cx + lx * cos_a - ly * sin_a, cy + lx * sin_a + ly * cos_a)

    def dessiner(self, ecran):
        cx, cy = float(self.x), float(self.y)
        ang = self.angle + math.sin(self.anim * 0.4) * 0.2
        cos_a, sin_a = math.cos(ang), math.sin(ang)
        rot = lambda lx, ly: self._rot_point(cx, cy, lx, ly, cos_a, sin_a)

        # Traînée de miettes jaunes
        for i in range(3):
            tx, ty = rot(-10 - i * 9, math.sin(self.anim * 0.5 + i) * 1.5)
            pygame.draw.circle(ecran, (255, 235, 120), (int(tx), int(ty)), max(2, 4 - i))

        # Forme banane (croissant)
        pts_haut, pts_bas = [], []
        for i in range(16):
            u = i / 15
            lx = -14 + u * 28
            courbe = math.sin(u * math.pi) * 6
            pts_haut.append(rot(lx, -courbe * 0.55))
            pts_bas.append(rot(lx, courbe * 0.45 + 2))
        pts = [tuple(map(int, p)) for p in pts_haut + pts_bas[::-1]]

        pygame.draw.polygon(ecran, (255, 228, 70), pts)
        pygame.draw.polygon(ecran, (190, 150, 35), pts, 2)
        # Reflet
        ref_x, ref_y = rot(2, -2)
        pygame.draw.ellipse(ecran, (255, 248, 160), (int(ref_x) - 3, int(ref_y) - 2, 8, 4))
        # Extrémités brunes
        bout1 = rot(15, 0)
        bout2 = rot(-15, 0)
        pygame.draw.circle(ecran, (130, 80, 40), (int(bout1[0]), int(bout1[1])), 3)
        pygame.draw.circle(ecran, (100, 65, 30), (int(bout2[0]), int(bout2[1])), 2)


# ──────────────────────────────────────────────
#  GARDE
# ──────────────────────────────────────────────
class Garde:
    """
    Ennemi perché sur un obstacle "high" existant (stalactite ou beam).
    La collision du slide est déjà gérée par l'obstacle sous-jacent.

    Le garde commence à tirer avant d'être visible (~500 px off-screen) :
    les joueurs voient d'abord les projectiles arriver, puis découvrent le garde.

    Deux types :
      "rapide" → orange, tir fréquent (~0.55 s), petit projectile jaune
      "lent"   → violet, tir espacé  (~1.4 s),  gros projectile violet

    Axe de tir : y_sol - 45
      → touche un joueur DEBOUT (hitbox top = y_sol - 57)
      → passe AU-DESSUS d'un joueur ACCROUPI (hitbox top = y_sol - 27)
    """
    _TIR_OFFSET = 45

    _TIMERS  = {"rapide": 80, "lent": 200}
    _COULEURS = {"rapide": (255, 145, 30), "lent": (155, 45, 215)}

    def __init__(self, x_centre, y_sol, type_garde, obs_y):
        self.x       = float(x_centre)   # centre horizontal de l'obstacle porteur
        self.y_sol   = y_sol
        self.type    = type_garde
        self.obs_y   = obs_y              # y du dessus de l'obstacle (pieds du garde)
        self.couleur = self._COULEURS[type_garde]
        self.projectiles: list[Projectile] = []
        self.timer   = random.randint(20, self._TIMERS[type_garde])
        self.actif   = False
        self.anim    = random.randint(0, 60)

    @property
    def _y_tir(self):
        return self.y_sol - self._TIR_OFFSET

    def update(self, vitesse):
        self.x   -= vitesse
        self.anim = (self.anim + 1) % 60

        if not self.actif and self.x <= LARGEUR + 480:
            self.actif = True

        if self.actif and self.x > -60:
            self.timer -= 1
            if self.timer <= 0:
                self.projectiles.append(Projectile(self.x, self._y_tir, self.type))
                self.timer = self._TIMERS[self.type]

        for p in self.projectiles:
            p.update(vitesse)
        self.projectiles = [p for p in self.projectiles if p.actif]

    def dessiner_garde(self, ecran):
        """Gardien du zoo perché sur l'obstacle."""
        cx = int(self.x)
        if not (-30 < cx < LARGEUR + 30):
            return

        yp = int(self.obs_y)
        rapide = self.type == "rapide"
        uni = (75, 115, 65) if rapide else (45, 65, 110)
        uni_s = (45, 75, 40) if rapide else (28, 42, 75)
        peau = (235, 195, 160)
        bob = int(math.sin(self.anim * 0.1) * 2)

        # Jambes + bottes
        pygame.draw.rect(ecran, uni_s, (cx - 10, yp - 14 + bob, 8, 14), border_radius=2)
        pygame.draw.rect(ecran, uni_s, (cx + 2, yp - 14 + bob, 8, 14), border_radius=2)
        pygame.draw.rect(ecran, (50, 35, 25), (cx - 11, yp - 4 + bob, 10, 5), border_radius=2)
        pygame.draw.rect(ecran, (50, 35, 25), (cx + 1, yp - 4 + bob, 10, 5), border_radius=2)

        # Torse + ceinture radio
        corps_y = yp - 48 + bob
        pygame.draw.rect(ecran, uni, (cx - 14, corps_y, 28, 34), border_radius=5)
        pygame.draw.rect(ecran, uni_s, (cx - 14, corps_y, 28, 34), 2, border_radius=5)
        pygame.draw.rect(ecran, (40, 40, 45), (cx - 8, corps_y + 22, 16, 8), border_radius=2)
        pygame.draw.circle(ecran, (80, 200, 255), (cx - 4, corps_y + 26), 2)

        # Tête + casquette zoo
        tete_y = corps_y - 16
        pygame.draw.circle(ecran, peau, (cx, tete_y), 12)
        pygame.draw.arc(ecran, uni, (cx - 14, tete_y - 20, 28, 18), 0, math.pi, 0)
        pygame.draw.rect(ecran, uni, (cx - 14, tete_y - 12, 28, 6))
        pygame.draw.rect(ecran, (220, 50, 50), (cx - 5, tete_y - 10, 10, 4))
        pygame.draw.circle(ecran, (25, 25, 35), (cx - 5, tete_y - 2), 2)
        pygame.draw.circle(ecran, (25, 25, 35), (cx + 3, tete_y - 2), 2)
        pygame.draw.line(ecran, (180, 80, 60), (cx - 4, tete_y + 4), (cx + 2, tete_y + 5), 2)

        # Bras + arme vers les joueurs
        bras_y = corps_y + 12
        pygame.draw.line(ecran, uni, (cx + 12, bras_y), (cx + 22, bras_y + 6), 4)
        if rapide:
            pygame.draw.rect(ecran, (55, 55, 60), (cx - 28, bras_y + 2, 18, 6), border_radius=2)
            pygame.draw.rect(ecran, (80, 180, 100), (cx - 32, bras_y + 3, 6, 4), border_radius=1)
            if self.timer < 15:
                pygame.draw.circle(ecran, (255, 255, 150), (cx - 34, bras_y + 5), 4)
        else:
            pygame.draw.line(ecran, (90, 70, 50), (cx - 26, bras_y - 4), (cx - 26, bras_y + 18), 3)
            pygame.draw.ellipse(ecran, (120, 170, 210), (cx - 32, bras_y + 14, 14, 12))
            pygame.draw.ellipse(ecran, (60, 100, 150), (cx - 32, bras_y + 14, 14, 12), 2)

    def dessiner_projectiles(self, ecran):
        for p in self.projectiles:
            if -40 < p.x < LARGEUR + 40:
                p.dessiner(ecran)


# ──────────────────────────────────────────────
#  MINI-BOSS — Le Directeur Magnus
# ──────────────────────────────────────────────
class MiniBoss:
    """
    Mini-boss final : combat de 25 % à 100 % du parcours.
    La vie baisse avec la distance parcourue ; bananes et esquives = effet visuel seul.
    """
    ATTACK_DUREE = 165
    REPOS_DUREE = 95
    ATTACKS = ("dart_double", "cage_drop", "net_sweep", "megaphone")
    EXPLOSION_DUREE = 150

    def __init__(self, y_sol_j1: float, y_sol_j2: float, solo_j1: bool = False):
        self.y_sol_j1 = y_sol_j1
        self.y_sol_j2 = y_sol_j2
        self.solo_j1 = solo_j1
        self.x = float(LARGEUR - 110)
        self.actif = False
        self.vaincu = False
        self.vie_ratio = 1.0
        self.zone_start = 0.0
        self.zone_fin = 1.0
        self.phase_idx = 0
        self.timer = 0
        self.en_attaque = False
        self.projectiles: list[ProjectileBoss] = []
        self.obstacles_j1: list[Obstacle] = []
        self.obstacles_j2: list[Obstacle] = []
        self.anim = 0
        self.vulnerable_flash = 0
        self.intro_flash = 0
        self.explosion_timer = 0
        self.explosion_debris: list[dict] = []
        self._wave_j1_touche = False
        self._wave_j2_touche = False
        self._palette = BIOMES["boss_zoo"]["palette"]

    def set_zone_boss(self, debut: float, fin: float):
        self.zone_start = debut
        self.zone_fin = max(debut + 1, fin)

    def mettre_a_jour_vie(self, distance: float):
        if distance <= self.zone_start:
            self.vie_ratio = 1.0
        elif distance >= self.zone_fin:
            self.vie_ratio = 0.0
        else:
            self.vie_ratio = 1.0 - (distance - self.zone_start) / (self.zone_fin - self.zone_start)

    def demarrer(self):
        self.actif = True
        self.intro_flash = 180
        self.timer = self.REPOS_DUREE
        self.en_attaque = False

    def notifier_touche(self, joueur_num: int):
        if joueur_num == 1:
            self._wave_j1_touche = True
        else:
            self._wave_j2_touche = True

    def _y_tir_j1(self):
        return self.y_sol_j1 - Garde._TIR_OFFSET

    def _y_tir_j2(self):
        return self.y_sol_j2 - Garde._TIR_OFFSET

    def _lancer_attaque(self):
        attaque = self.ATTACKS[self.phase_idx % len(self.ATTACKS)]
        self.phase_idx += 1
        bx = self.x - 30

        if attaque == "dart_double":
            self.projectiles.append(ProjectileBoss(bx, self._y_tir_j1(), "boss_dart"))
            self.projectiles.append(ProjectileBoss(bx, self._y_tir_j2(), "boss_dart"))
            self.projectiles.append(ProjectileBoss(bx - 20, self._y_tir_j1() - 25, "boss_staple"))
        elif attaque == "cage_drop":
            self.obstacles_j1.append(
                Obstacle(LARGEUR + 60, self.y_sol_j1, "low", 70, self._palette, "boss_zoo"))
            self.obstacles_j2.append(
                Obstacle(LARGEUR + 60, self.y_sol_j2, "low", 70, self._palette, "boss_zoo"))
            for obs in (self.obstacles_j1[-1], self.obstacles_j2[-1]):
                obs.subtype = "cage"
                obs.hauteur = 52
                obs.y = obs.y_sol - obs.hauteur
        elif attaque == "net_sweep":
            y_mid_j1 = self.y_sol_j1 - 30
            y_mid_j2 = self.y_sol_j2 - 30
            self.projectiles.append(ProjectileBoss(bx, y_mid_j1, "boss_net"))
            self.projectiles.append(ProjectileBoss(bx + 45, y_mid_j2, "boss_net"))
            self.projectiles.append(ProjectileBoss(bx + 20, (y_mid_j1 + y_mid_j2) / 2, "boss_net"))
        else:
            for i, y_t in enumerate((self._y_tir_j1(), self._y_tir_j2(), self._y_tir_j1() - 20)):
                self.projectiles.append(ProjectileBoss(bx + i * 35, y_t, "boss_megaphone"))

    def _demarrer_explosion(self):
        self.vaincu = True
        self.en_attaque = False
        self.explosion_timer = self.EXPLOSION_DUREE
        SONS.play("hit")
        self.projectiles.clear()
        self.obstacles_j1.clear()
        self.obstacles_j2.clear()
        bx, by = int(self.x), 130
        for _ in range(55):
            self.explosion_debris.append({
                "x": float(bx + random.randint(-60, 60)),
                "y": float(by + random.randint(-40, 80)),
                "vx": random.uniform(-6, 6),
                "vy": random.uniform(-9, 2),
                "vie": random.randint(40, 90),
                "taille": random.randint(4, 14),
                "couleur": random.choice([
                    (220, 60, 60), (255, 180, 50), (70, 70, 90),
                    (240, 200, 170), (255, 120, 40),
                ]),
            })

    def recevoir_tir_joueur(self) -> bool:
        """Impact visuel uniquement — la vie suit la progression du niveau."""
        if self.vaincu or self.intro_flash > 40:
            return False
        self.vulnerable_flash = 14
        return True

    def get_hitbox_rect(self):
        bx = int(self.x)
        return pygame.Rect(bx - 52, 55, 104, HAUTEUR // 2 - 30)

    def cible_y_centre(self):
        return 115 + int(math.sin(self.anim * 0.08) * 4)

    def _fin_vague(self):
        j1_ok = not self._wave_j1_touche
        j2_ok = self.solo_j1 or not self._wave_j2_touche
        if j1_ok and j2_ok:
            self.vulnerable_flash = 20
        self._wave_j1_touche = False
        self._wave_j2_touche = False

    def update(self, vitesse: float):
        if not self.actif:
            return
        self.anim += 1

        if self.explosion_timer > 0:
            self.explosion_timer -= 1
            for d in self.explosion_debris:
                d["x"] += d["vx"]
                d["y"] += d["vy"]
                d["vy"] += 0.18
                d["vie"] -= 1
            self.explosion_debris = [d for d in self.explosion_debris if d["vie"] > 0]
            return

        if self.vaincu:
            return

        if self.intro_flash > 0:
            self.intro_flash -= 1

        if self.en_attaque:
            self.timer -= 1
            if self.timer <= 0:
                self.en_attaque = False
                self._fin_vague()
                pause = max(55, int(self.REPOS_DUREE * (0.55 + 0.45 * self.vie_ratio)))
                self.timer = pause
        else:
            self.timer -= 1
            if self.timer <= 0:
                self.en_attaque = True
                self._lancer_attaque()
                intensite = 1.0 - self.vie_ratio * 0.35
                self.timer = max(90, int(self.ATTACK_DUREE * intensite))

        for proj in self.projectiles:
            if proj.actif:
                proj.update(vitesse)
        self.projectiles = [p for p in self.projectiles if p.actif]

        for obs_list in (self.obstacles_j1, self.obstacles_j2):
            for obs in obs_list:
                obs.deplacer(vitesse)
            obs_list[:] = [o for o in obs_list if o.x > -120]

        if self.vulnerable_flash > 0:
            self.vulnerable_flash -= 1

    def dessiner(self, ecran):
        if not self.actif:
            return
        if self.explosion_timer > 0:
            self._dessiner_explosion(ecran)
            return
        if self.vaincu:
            return
        bx = int(self.x)
        bob = int(math.sin(self.anim * 0.08) * 4)
        tour_h = HAUTEUR // 2 - 75

        # QG du zoo — tour en briques
        pygame.draw.rect(ecran, (120, 55, 45), (bx - 62, 55 + bob, 124, tour_h), border_radius=10)
        pygame.draw.rect(ecran, (80, 35, 30), (bx - 62, 55 + bob, 124, tour_h), 4, border_radius=10)
        for row in range(0, tour_h, 22):
            for col in range(0, 120, 28):
                if (row // 22 + col // 28) % 2 == 0:
                    pygame.draw.rect(ecran, (100, 45, 38),
                                     (bx - 56 + col, 62 + row + bob, 24, 16), border_radius=2)
        # Enseigne ZOO
        pygame.draw.rect(ecran, (240, 210, 50), (bx - 40, 68 + bob, 80, 22), border_radius=4)
        signe = police(20).render("ZOO", True, (180, 40, 30))
        ecran.blit(signe, signe.get_rect(center=(bx, 79 + bob)))
        # Fenêtre vitrée
        fenetre = pygame.Rect(bx - 38, 98 + bob, 76, 52)
        pygame.draw.rect(ecran, (150, 210, 245), fenetre, border_radius=6)
        pygame.draw.rect(ecran, (50, 70, 100), fenetre, 3, border_radius=6)
        pygame.draw.line(ecran, (50, 70, 100), (bx, fenetre.y), (bx, fenetre.bottom), 2)
        pygame.draw.line(ecran, (50, 70, 100), (fenetre.x, fenetre.centery), (fenetre.right, fenetre.centery), 2)

        # Directeur Magnus
        cx, cy = bx, 118 + bob
        pygame.draw.circle(ecran, (245, 210, 175), (cx, cy), 20)
        pygame.draw.ellipse(ecran, (60, 35, 25), (cx - 18, cy + 6, 36, 14))
        pygame.draw.rect(ecran, (170, 25, 35), (cx - 26, cy + 12, 52, 38), border_radius=6)
        pygame.draw.rect(ecran, (140, 15, 25), (cx - 26, cy + 12, 52, 38), 2, border_radius=6)
        pygame.draw.rect(ecran, (220, 180, 50), (cx - 30, cy + 16, 10, 10))
        pygame.draw.rect(ecran, (220, 180, 50), (cx + 20, cy + 16, 10, 10))
        pygame.draw.rect(ecran, (25, 25, 35), (cx - 24, cy - 14, 48, 16), border_radius=4)
        pygame.draw.circle(ecran, (255, 255, 255), (cx + 10, cy - 4), 6)
        pygame.draw.circle(ecran, (30, 30, 40), (cx + 12, cy - 4), 2)
        pygame.draw.line(ecran, (40, 25, 15), (cx - 8, cy + 2), (cx - 2, cy + 2), 2)
        pygame.draw.line(ecran, (40, 25, 15), (cx + 4, cy + 2), (cx + 10, cy + 2), 2)
        if self.en_attaque and self.anim % 20 < 10:
            pygame.draw.polygon(ecran, (220, 50, 50), [
                (cx + 28, cy + 8), (cx + 18, cy), (cx + 18, cy + 16),
            ])
            pygame.draw.rect(ecran, (240, 200, 60), (cx + 26, cy + 2, 14, 10), border_radius=2)

        # Barre de vie (liée à la progression 25 % → 100 %)
        bar_w, bar_h = 340, 18
        bar_x = LARGEUR // 2 - bar_w // 2
        pct = int(self.vie_ratio * 100)
        pygame.draw.rect(ecran, (22, 24, 35), (bar_x - 2, 8, bar_w + 4, bar_h + 22), border_radius=8)
        pygame.draw.rect(ecran, (35, 38, 52), (bar_x, 22, bar_w, bar_h), border_radius=6)
        fill_w = max(0, int(bar_w * self.vie_ratio))
        if fill_w > 0:
            col_hp = (220, 55, 55) if self.vie_ratio > 0.35 else (255, 140, 40)
            pygame.draw.rect(ecran, col_hp, (bar_x, 22, fill_w, bar_h), border_radius=6)
            shine = pygame.Surface((fill_w, bar_h), pygame.SRCALPHA)
            pygame.draw.rect(shine, (255, 255, 255, 45), (0, 0, fill_w, bar_h // 2), border_radius=4)
            ecran.blit(shine, (bar_x, 22))
        pygame.draw.rect(ecran, (190, 195, 210), (bar_x, 22, bar_w, bar_h), 2, border_radius=6)
        nom = police(17).render("DIRECTEUR MAGNUS", True, (255, 210, 210))
        ecran.blit(nom, nom.get_rect(center=(LARGEUR // 2, 14)))
        vie_lbl = police(15).render(f"VIE  {pct} %", True, BLANC)
        ecran.blit(vie_lbl, vie_lbl.get_rect(center=(LARGEUR // 2, 32)))
        prog_boss = 1.0 - self.vie_ratio
        phase = police(13).render(
            f"Phase boss  {int(25 + prog_boss * 75)} % du parcours", True, (160, 170, 195))
        ecran.blit(phase, phase.get_rect(center=(LARGEUR // 2, 48)))

        if self.vulnerable_flash > 0 and self.vulnerable_flash % 8 < 4:
            flash = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
            flash.fill((255, 80, 80, 40))
            ecran.blit(flash, (0, 0))

    def dessiner_obstacles(self, ecran, pulse: int):
        for obs in self.obstacles_j1 + self.obstacles_j2:
            if -120 < obs.x < LARGEUR + 120:
                obs.dessiner(ecran, pulse)

    def dessiner_projectiles(self, ecran):
        for proj in self.projectiles:
            if proj.actif:
                proj.dessiner(ecran)

    def _dessiner_explosion(self, ecran):
        bx = int(self.x)
        prog = 1.0 - self.explosion_timer / self.EXPLOSION_DUREE
        shake = int(math.sin(self.anim * 0.9) * 6 * prog)
        # Flash initial
        if prog < 0.25:
            alpha = int((1.0 - prog / 0.25) * 160)
            flash = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
            flash.fill((255, 240, 200, alpha))
            ecran.blit(flash, (0, 0))
        # Onde de choc
        rayon = int(30 + prog * 220)
        onde = pygame.Surface((rayon * 2, rayon * 2), pygame.SRCALPHA)
        pygame.draw.circle(onde, (255, 120, 60, max(0, 120 - int(prog * 120))), (rayon, rayon), rayon, 4)
        ecran.blit(onde, (bx - rayon + shake, 100 - rayon // 2))
        # Débris
        for d in self.explosion_debris:
            alpha = min(255, d["vie"] * 6)
            s = pygame.Surface((d["taille"] * 2, d["taille"] * 2), pygame.SRCALPHA)
            pygame.draw.rect(s, (*d["couleur"], alpha),
                             (0, 0, d["taille"] * 2, d["taille"] * 2), border_radius=2)
            ecran.blit(s, (int(d["x"]) - d["taille"], int(d["y"]) - d["taille"]))
        # Fumée centrale
        for i in range(4):
            rr = int(20 + prog * (50 + i * 25))
            smoke = pygame.Surface((rr * 2, rr * 2), pygame.SRCALPHA)
            pygame.draw.circle(smoke, (80, 80, 90, 50 - i * 10), (rr, rr), rr)
            ecran.blit(smoke, (bx - rr + shake, 90 - rr + i * 8))


# ──────────────────────────────────────────────
#  CIRCUIT
# ──────────────────────────────────────────────
class Circuit:
    """
    Gère les obstacles et les pièces d'une piste (J1 ou J2).

    À la création, _generer() place :
      - Des obstacles alternant "low" (sauter) et "high" (se baisser),
        espacés de [gap_min, gap_max] pixels, sur toute la longueur du niveau.
      - Des pièces en arc devant chaque obstacle (2-5 par obstacle).

    Chaque frame, update(vitesse) fait avancer tous les objets vers la gauche.
    """
    def __init__(self, y_sol, longueur_niveau, gap_min=300, gap_max=420, generer_obstacles=True,
                 obstacle_palette=None, generer_gardes=False, biome="default",
                 longueur_obstacles=None):
        self.y_sol             = y_sol
        self.longueur_niveau   = longueur_niveau
        self.gap_min           = gap_min
        self.gap_max           = gap_max
        self.generer_obstacles = generer_obstacles
        self.obstacle_palette  = obstacle_palette
        self.biome             = biome
        self.longueur_obstacles = longueur_obstacles or (longueur_niveau + 1600)
        self.obstacles: list[Obstacle] = []
        self.pieces:    list[Piece]    = []
        self.gardes:    list[Garde]    = []
        if self.generer_obstacles:
            self._generer()
        if generer_gardes:
            self._generer_gardes()

    def _generer(self):
        x         = 920
        last_type = "low"
        limite    = self.longueur_obstacles
        while x < limite:
            if random.random() < 0.72:
                obstacle_type = "high" if last_type == "low" else "low"
            else:
                obstacle_type = last_type
            largeur = random.randint(56, 84)
            self.obstacles.append(
                Obstacle(x, self.y_sol, obstacle_type, largeur,
                         self.obstacle_palette, self.biome)
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

    def _generer_gardes(self):
        """
        Place 4 gardes sur des obstacles "high" existants (stalactite / beam),
        répartis à ≈ 20 / 40 / 60 / 80 % du niveau.
        Types alternés : rapide → lent → rapide → lent.

        Chaque garde hérite de l'x-centre et du y-dessus de l'obstacle choisi.
        La collision "slide" est déjà gérée par l'obstacle lui-même.
        """
        hauts = sorted(
            [obs for obs in self.obstacles if obs.type == "high"],
            key=lambda o: o.x,
        )
        if len(hauts) < 4:
            return   # pas assez d'obstacles hauts pour placer 4 gardes

        pcts  = [0.20, 0.40, 0.60, 0.80]
        types = ["rapide", "lent", "rapide", "lent"]
        deja  = set()

        for pct, tg in zip(pcts, types):
            cible_x = pct * self.longueur_niveau + 220
            candidats = [o for o in hauts if id(o) not in deja]
            if not candidats:
                break
            obs = min(candidats, key=lambda o: abs(o.x - cible_x))
            deja.add(id(obs))
            # Centre horizontal de l'obstacle ; obs.y = dessus (pieds du garde)
            cx = obs.x + obs.largeur // 2
            self.gardes.append(Garde(cx, self.y_sol, tg, obs_y=obs.y))

    def update(self, vitesse):
        for obs in self.obstacles:
            obs.deplacer(vitesse)
        for piece in self.pieces:
            if not piece.collectee:
                piece.deplacer(vitesse)
        for garde in self.gardes:
            garde.update(vitesse)

    def dessiner(self, ecran, pulse):
        for piece in self.pieces:
            if not piece.collectee and -30 < piece.x < LARGEUR + 30:
                piece.dessiner(ecran)
        for obs in self.obstacles:
            if -120 < obs.x < LARGEUR + 120:
                obs.dessiner(ecran, pulse)
        # Gardes dessinés APRÈS les obstacles (perchés dessus)
        for garde in self.gardes:
            if -40 < garde.x < LARGEUR + 40:
                garde.dessiner_garde(ecran)

    def dessiner_projectiles(self, ecran):
        """Projectiles dessinés APRÈS les joueurs pour rester visibles au premier plan."""
        for garde in self.gardes:
            garde.dessiner_projectiles(ecran)


# ──────────────────────────────────────────────
#  HUD
# ──────────────────────────────────────────────
def dessiner_hud(ecran, j1, j2, distance, longueur_niveau, vitesse, vitesse_max,
                 nom_niveau, compte_a_rebours, score_pieces=0, j2_ia=False):
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
    if j2 is not None:
        label_j2 = "J2 IA" if j2_ia else "J2"
        ecran.blit(police(18).render(label_j2, True, C_J2), (S1_X,      PAD + 60))
        j2.dessiner_vies(ecran,                          S1_X + (58 if j2_ia else 30),  PAD + 58)
    else:
        # Mode solo J1 : affiche "SOLO" à la place de J2
        ecran.blit(police(18).render("SOLO", True, (140, 140, 160)), (S1_X, PAD + 60))

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
#  ÉCRAN DE FIN — transition vers le niveau suivant
# ──────────────────────────────────────────────
_COULEUR_BIOME = {
    "default": (150, 150, 165),
    "savanna": (230, 185, 65),
    "arctic": (150, 215, 255),
    "jungle": (75, 195, 95),
    "aquatic": (55, 145, 225),
    "boss_zoo": (215, 55, 75),
}

_TEASER_BIOME = {
    "savanna": "Chaleur, gardes nerveux et pistes plus longues…",
    "arctic": "La glace accélère tout — restez groupés !",
    "jungle": "Végétation dense, ennemis partout dans la jungle.",
    "aquatic": "Zone humide : vitesse max en hausse, gardes acharnés.",
    "boss_zoo": "Le Directeur Magnus règle ses comptes. Boss final !",
    "default": "De nouveaux pièges vous attendent plus loin.",
}

_AUTO_SUITE_SEC = 9


def _info_prochain_niveau(numero_niveau):
    if numero_niveau is None:
        return None
    suivant = numero_niveau + 1
    if suivant not in NIVEAUX:
        return None
    cfg = NIVEAUX[suivant]
    biome = cfg.get("biome", "default")
    return {
        "numero": suivant,
        "nom": cfg.get("nom", f"Niveau {suivant}"),
        "biome": biome,
        "couleur": _COULEUR_BIOME.get(biome, (180, 180, 190)),
        "teaser": _TEASER_BIOME.get(biome, _TEASER_BIOME["default"]),
        "boss": cfg.get("mode_boss", False),
    }


def _config_niveau_suivant(config_actuelle, numero_suivant):
    cfg = dict(NIVEAUX[numero_suivant], _numero=numero_suivant)
    for cle in (
        "ai_j2", "j2_force_ia", "solo_j1", "controles_j1", "biome",
        "mode_boss", "boss_zone_pct", "boss_run_after",
        "couleurs_j1", "nom_j1", "personnage_j1",
        "couleurs_j2", "nom_j2", "personnage_j2", "vies",
    ):
        if cle in config_actuelle:
            cfg[cle] = config_actuelle[cle]
    return cfg


class EcranFin:
    def __init__(self, victoire: bool, nom_niveau: str, score_pieces: int = 0,
                 score_distance: int = 0, numero_niveau: int = None):
        self.victoire = victoire
        self.nom_niveau = nom_niveau
        self.score_pieces = score_pieces
        self.score_distance = score_distance
        self.numero_niveau = numero_niveau
        self.frame = 0
        self.particules: list[Particule] = []
        self.prochain = _info_prochain_niveau(numero_niveau) if victoire else None
        self.auto_continue_rest = FPS * _AUTO_SUITE_SEC if self.prochain else 0
        self.image_perdu = None
        if not self.victoire:
            try:
                dossier_courant = app_paths.resource_dir()
                chemin_lost = os.path.join(dossier_courant, "assets", "lost.png")
                if os.path.exists(chemin_lost):
                    image = pygame.image.load(chemin_lost).convert_alpha()
                    hauteur_cible = 165
                    ratio = hauteur_cible / max(1, image.get_height())
                    largeur_cible = max(1, int(image.get_width() * ratio))
                    self.image_perdu = pygame.transform.smoothscale(
                        image, (largeur_cible, hauteur_cible))
            except Exception:
                self.image_perdu = None
        if victoire:
            for _ in range(90):
                c = random.choice([(255, 215, 0), (0, 255, 200), (255, 100, 200)])
                p = Particule(random.randint(0, LARGEUR), random.randint(0, HAUTEUR // 2), c)
                p.vie = random.randint(70, 130)
                p.vie_max = p.vie
                p.vy = random.uniform(-3, 0)
                self.particules.append(p)

    def annuler_auto_continue(self):
        self.auto_continue_rest = 0

    def tick_auto_continue(self) -> bool:
        if self.auto_continue_rest <= 0:
            return False
        self.auto_continue_rest -= 1
        return self.auto_continue_rest <= 0

    @property
    def score_total(self):
        return self.score_distance + self.score_pieces * 50

    def update(self):
        self.frame += 1
        for p in self.particules:
            p.update()
        self.particules = [p for p in self.particules if p.vie > 0]

    def _layout_victoire(self):
        """Positions verticales fixes (aucun chevauchement)."""
        footer_h = 102
        card_h = 150
        score_h = 134
        prog_h = 58
        marge = 14
        bas = HAUTEUR - footer_h
        card_y = bas - card_h - marge
        score_y = card_y - score_h - marge
        prog_y = score_y - prog_h - marge
        return {
            "footer_h": footer_h,
            "footer_y": bas,
            "card_y": card_y,
            "card_h": card_h,
            "score_y": score_y,
            "score_h": score_h,
            "prog_y": prog_y,
            "prog_h": prog_h,
        }

    def _dessiner_parcours_sur_surface(self, surf, cy_local):
        nums = [n for n in sorted(NIVEAUX.keys()) if n >= 1]
        if not nums:
            return
        sw = surf.get_width()
        esp = min(100, (sw - 80) // max(1, len(nums) - 1))
        x0 = sw // 2 - (len(nums) - 1) * esp // 2
        actuel = self.numero_niveau or 1
        for i, num in enumerate(nums):
            cx = x0 + i * esp
            fait = num <= actuel
            suivant = self.prochain and num == self.prochain["numero"]
            r = 15
            if fait:
                col = VERT
            elif suivant:
                col = self.prochain["couleur"]
            else:
                col = (58, 62, 78)
            pygame.draw.circle(surf, col, (cx, cy_local), r)
            pygame.draw.circle(surf, (22, 26, 38), (cx, cy_local), r, 2)
            if fait:
                pygame.draw.line(surf, BLANC, (cx - 5, cy_local), (cx - 1, cy_local + 4), 2)
                pygame.draw.line(surf, BLANC, (cx - 1, cy_local + 4), (cx + 6, cy_local - 5), 2)
            else:
                lbl = police(14).render(str(num), True, BLANC if suivant else (115, 120, 135))
                surf.blit(lbl, lbl.get_rect(center=(cx, cy_local)))
            if i < len(nums) - 1:
                col_l = VERT if num < actuel else (75, 80, 95)
                pygame.draw.line(surf, col_l, (cx + r, cy_local), (cx + esp - r, cy_local), 3)

    def _dessiner_barre_basse(self, ecran, ly):
        y0 = ly["footer_y"]
        fh = ly["footer_h"]
        pygame.draw.rect(ecran, (6, 10, 22), (0, y0, LARGEUR, fh))
        pygame.draw.line(ecran, (75, 95, 140), (0, y0), (LARGEUR, y0), 2)

        pulse = 0.88 + 0.12 * abs(math.sin(self.frame * 0.08))
        if self.prochain:
            titre = police(30).render("ENTRÉE  ou  ESPACE  —  Continuer l'aventure", True,
                                      (255, int(215 + 40 * pulse), int(75 + 35 * pulse)))
        else:
            titre = police(28).render("ENTRÉE  —  Menu principal", True, (225, 230, 245))
        ecran.blit(titre, titre.get_rect(center=(LARGEUR // 2, y0 + 26)))

        if self.prochain:
            l1 = police(19).render(
                "ENTRÉE  ·  ESPACE  ·  N   =   niveau suivant", True, (215, 220, 235))
            l2 = police(19).render(
                "R  =  rejouer     ·     D  =  carte     ·     ESC  =  menu", True, (215, 220, 235))
            ecran.blit(l1, l1.get_rect(center=(LARGEUR // 2, y0 + 52)))
            ecran.blit(l2, l2.get_rect(center=(LARGEUR // 2, y0 + 76)))
            if self.auto_continue_rest > 0:
                sec = max(0, self.auto_continue_rest // FPS)
                cd = police(15).render(f"Suite auto dans {sec} s  (une touche annule)", True, (130, 140, 165))
                ecran.blit(cd, cd.get_rect(center=(LARGEUR // 2, y0 + fh - 10)))
        else:
            ecran.blit(police(20).render("R  rejouer     ·     ESC  menu", True, (200, 208, 225)),
                       police(20).render("R  rejouer     ·     ESC  menu", True, (200, 208, 225))
                       .get_rect(center=(LARGEUR // 2, y0 + 58)))

    def dessiner(self, ecran):
        if self.victoire:
            ecran.fill((10, 14, 26))
            self._dessiner_victoire(ecran)
            return
        overlay = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 240))
        ecran.blit(overlay, (0, 0))
        self._dessiner_game_over(ecran)

    def _dessiner_game_over(self, ecran):
        if self.image_perdu is not None:
            ecran.blit(self.image_perdu,
                       self.image_perdu.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 - 200)))
        bob = int(math.sin(self.frame * 0.08) * 6)
        titre = police(88).render("GAME OVER", True, ROUGE)
        ecran.blit(titre, titre.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 - 100 + bob)))
        ecran.blit(police(28).render(self.nom_niveau, True, CYAN),
                   police(28).render(self.nom_niveau, True, CYAN)
                   .get_rect(center=(LARGEUR // 2, HAUTEUR // 2 - 20)))
        msg = "Un joueur est tombé — réessayez à deux !"
        ecran.blit(police(24).render(msg, True, (190, 190, 200)),
                   police(24).render(msg, True, (190, 190, 200))
                   .get_rect(center=(LARGEUR // 2, HAUTEUR // 2 + 30)))
        bar = pygame.Surface((LARGEUR, 56), pygame.SRCALPHA)
        bar.fill((8, 12, 24, 250))
        ecran.blit(bar, (0, HAUTEUR - 56))
        aide = police(22).render("R  =  réessayer          ESC  =  menu", True, (210, 215, 230))
        ecran.blit(aide, aide.get_rect(center=(LARGEUR // 2, HAUTEUR - 28)))

    def _dessiner_victoire(self, ecran):
        ly = self._layout_victoire()
        bob = int(math.sin(self.frame * 0.09) * 3)

        # ── En-tête ──────────────────────────────────────────────────────────
        ecran.blit(police(58).render("ÉVASION RÉUSSIE !", True, VERT),
                   police(58).render("ÉVASION RÉUSSIE !", True, VERT)
                   .get_rect(center=(LARGEUR // 2, 48 + bob)))
        ecran.blit(police(22).render(f"Zone terminée : {self.nom_niveau}", True, CYAN),
                   police(22).render(f"Zone terminée : {self.nom_niveau}", True, CYAN)
                   .get_rect(center=(LARGEUR // 2, 98)))

        # ── Parcours 1 → 5 (bandeau isolé) ───────────────────────────────────
        pw = LARGEUR - 80
        strip = pygame.Surface((pw, ly["prog_h"]))
        strip.fill((18, 24, 40))
        pygame.draw.rect(strip, (60, 78, 115), (0, 0, pw, ly["prog_h"]), 2, border_radius=10)
        self._dessiner_parcours_sur_surface(strip, ly["prog_h"] // 2)
        ecran.blit(strip, (40, ly["prog_y"]))

        # ── Score (sous le parcours, jamais par-dessus) ──────────────────────
        sw, sh = min(520, LARGEUR - 60), ly["score_h"]
        sx = (LARGEUR - sw) // 2
        score = pygame.Surface((sw, sh))
        score.fill((16, 22, 38))
        pygame.draw.rect(score, (80, 105, 155), (0, 0, sw, sh), 2, border_radius=12)
        score.blit(police(21).render("SCORE DE LA ZONE", True, (145, 170, 210)), (18, 10))
        pygame.draw.line(score, (50, 60, 85), (14, 36), (sw - 14, 36), 1)
        lignes = [
            ("Distance", f"{self.score_distance:,}".replace(",", " "), BLANC),
            ("Pièces", str(self.score_pieces), (255, 215, 0)),
            ("Total", f"{self.score_total:,}".replace(",", " "), JAUNE),
        ]
        for i, (label, val, col) in enumerate(lignes):
            yy = 46 + i * 28
            score.blit(police(19).render(label, True, (125, 140, 165)), (22, yy))
            vs = police(26).render(val, True, col)
            score.blit(vs, (sw - 22 - vs.get_width(), yy - 2))
        ecran.blit(score, (sx, ly["score_y"]))

        # ── Prochain niveau ──────────────────────────────────────────────────
        if self.prochain:
            p = self.prochain
            cw, ch = min(540, LARGEUR - 50), ly["card_h"]
            cx = (LARGEUR - cw) // 2
            card = pygame.Surface((cw, ch))
            card.fill((14, 20, 34))
            pygame.draw.rect(card, p["couleur"], (0, 0, cw, 7))
            pygame.draw.rect(card, p["couleur"], (0, 0, cw, ch), 3, border_radius=14)
            card.blit(police(19).render("PROCHAIN NIVEAU", True, (170, 185, 215)),
                      police(19).render("PROCHAIN NIVEAU", True, (170, 185, 215))
                      .get_rect(midtop=(cw // 2, 14)))
            card.blit(police(36).render(p["nom"].upper(), True, BLANC),
                      police(36).render(p["nom"].upper(), True, BLANC).get_rect(midtop=(cw // 2, 40)))
            ty = 88
            if p["boss"]:
                card.blit(police(16).render("BOSS FINAL", True, (255, 100, 100)),
                          police(16).render("BOSS FINAL", True, (255, 100, 100))
                          .get_rect(midtop=(cw // 2, ty)))
                ty += 22
            card.blit(police(17).render(p["teaser"], True, (180, 190, 210)),
                      police(17).render(p["teaser"], True, (180, 190, 210))
                      .get_rect(midtop=(cw // 2, ty)))
            ecran.blit(card, (cx, ly["card_y"]))
        else:
            fin_y = ly["card_y"] + ly["card_h"] // 2 - 30
            ecran.blit(police(28).render("ZOO ENTIEREMENT ECHAPPE !", True, JAUNE),
                       police(28).render("ZOO ENTIEREMENT ECHAPPE !", True, JAUNE)
                       .get_rect(center=(LARGEUR // 2, fin_y)))

        self._dessiner_barre_basse(ecran, ly)


# ──────────────────────────────────────────────
#  JEU PRINCIPAL
# ──────────────────────────────────────────────
class JeuDeuxJoueurs:
    """
    Contrôleur principal d'une partie.

    Responsabilités :
      - Initialiser J1, J2 et leurs circuits respectifs selon la config du niveau
      - Gérer le compte à rebours de départ
      - Mettre à jour la physique, les collisions, la collecte de pièces
      - Piloter l'IA de J2 (mode solo) via FauxTouches
      - Déclencher la fin de partie (victoire ou game over)
      - Déléguer le rendu à dessiner()

    Deux pistes indépendantes : J1 dans la moitié haute, J2 dans la moitié basse.
    La mort de l'un entraîne le game over des deux (coopération obligatoire).

    Paramètres réseau (optionnels) :
      client_reseau : instance de ClientReseau déjà connectée
      player_id     : 0 → ce PC contrôle J1, 1 → ce PC contrôle J2
      seed          : graine random partagée pour synchroniser les obstacles
    """
    COUNTDOWN_DUREE = 3

    def __init__(self, config_niveau=None, client_reseau=None, player_id=0, seed=None):
        if config_niveau is None:
            config_niveau = {}
        self.config_niveau  = config_niveau
        self.nom_niveau     = config_niveau.get("nom", "Libre")
        self.numero_niveau  = config_niveau.get("_numero")  # int ou None

        self.fond = Skybox(config_niveau.get("biome", "default"))
        self.longueur_pre_boss = config_niveau.get("longueur", 14000)
        self.mode_boss = config_niveau.get("mode_boss", False)
        self.boss_zone_pct = config_niveau.get("boss_zone_pct", 0.25)
        self.boss_run_after = config_niveau.get("boss_run_after", 4500)
        self.boss_zone_start = int(self.longueur_pre_boss * self.boss_zone_pct)
        self.longueur_niveau = self.longueur_pre_boss
        self.distance        = 0.0
        self.vitesse         = config_niveau.get("vitesse",      3.8)
        self.vitesse_max     = config_niveau.get("vitesse_max",  5.8)
        self.acceleration    = config_niveau.get("acceleration", 0.0007)

        # Y-sol calibrés selon le biome/niveau
        # Chaque biome a ses positions spécifiques pour aligner correctement avec le fond
        biome = config_niveau.get("biome", "default")
        y_sol_ratios = {
            "default": 0.445,    # Niveau 0 et 1 (Background_lvl1.png)
            "savanna": 0.445,    # Niveau 1 (Background_lvl1.png)
            "arctic": 0.43,      # Niveau 2 (Niveau 2 fini(1)_0000.png)
            "jungle": 0.45,      # Niveau 3 (plus bas)
            "aquatic": 0.44,     # Niveau 4 (haut inchangé)
            "boss_zoo": 0.445,   # Boss (Background_lvl1.png par défaut)
        }
        y_sol_ratio = y_sol_ratios.get(biome, 0.445)
        self.y_sol_j1 = int(HAUTEUR * y_sol_ratio)
        # J2 avec offset différent par biome
        y_sol_j2_offsets = {
            "default": 58,       # Niveau 0
            "savanna": 40,       # Niveau 1 - descendu encore plus
            "arctic": 48,        # Niveau 2
            "jungle": 38,        # Niveau 3 - plus bas
            "aquatic": 52,       # Niveau 4 - remonte vraiment le joueur bas
            "boss_zoo": 58,      # Boss
        }
        y_sol_j2_offset = y_sol_j2_offsets.get(biome, 58)
        self.y_sol_j2 = min(int(HAUTEUR - y_sol_j2_offset), HAUTEUR - 43)

        controles_j1 = config_niveau.get("controles_j1", (pygame.K_z, pygame.K_s))
        couleurs_j1  = config_niveau.get("couleurs_j1", ((225, 120, 90), (255, 170, 140)))
        couleurs_j2  = config_niveau.get("couleurs_j2", ((140, 150, 170), (200, 210, 225)))
        nom_j1       = config_niveau.get("nom_j1", "J1")
        nom_j2       = config_niveau.get("nom_j2", "J2")
        personnage_j1 = config_niveau.get("personnage_j1", "Fox")
        personnage_j2 = config_niveau.get("personnage_j2", "Raton")
        self.joueur1 = Joueur(
            x=220, y_sol=self.y_sol_j1,
            controles=controles_j1,
            nom=nom_j1, couleurs=couleurs_j1,
            personnage=personnage_j1,
        )
        self.joueur2 = Joueur(
            x=220, y_sol=self.y_sol_j2,
            controles=(pygame.K_UP, pygame.K_DOWN),
            nom=nom_j2, couleurs=couleurs_j2,
            personnage=personnage_j2,
        )

        # Vies issues de la config du niveau (5 en easy, 3 en hard...)
        vies_niveau = config_niveau.get("vies", 3)
        self.joueur1.vies = vies_niveau
        self.joueur1.VIES_MAX = vies_niveau
        self.joueur2.vies = vies_niveau
        self.joueur2.VIES_MAX = vies_niveau

        # ── Mode réseau ──────────────────────────────────────────────────────
        # client_reseau : instance de ClientReseau connectée, ou None si local/solo
        # player_id     : 0 = ce PC joue J1, 1 = ce PC joue J2
        # En mode réseau on fixe le seed random pour que les deux PCs génèrent
        # exactement les mêmes obstacles (même séquence aléatoire).
        self.client_reseau = client_reseau
        self.player_id     = player_id
        self._heartbeat_counter = 0  # Envoie un ping toutes les 30 frames (0.2 sec à 144 FPS)
        if seed is not None:
            random.seed(seed)

        gap_min           = config_niveau.get("gap_min", 400)
        gap_max           = config_niveau.get("gap_max", 560)
        generer_obstacles = config_niveau.get("generer_obstacles", True)
        generer_gardes    = config_niveau.get("generer_gardes",    False)
        biome             = config_niveau.get("biome", "default")
        palette_j1, palette_j2 = self.fond.palettes_obstacles()
        long_obs = int(self.boss_zone_start * 0.92) if self.mode_boss else None
        self.circuit_j1 = Circuit(
            self.y_sol_j1, self.longueur_pre_boss, gap_min, gap_max,
            generer_obstacles, obstacle_palette=palette_j1,
            generer_gardes=generer_gardes, biome=biome,
            longueur_obstacles=long_obs,
        )
        self.circuit_j2 = Circuit(
            self.y_sol_j2, self.longueur_pre_boss, gap_min, gap_max,
            generer_obstacles, obstacle_palette=palette_j2,
            generer_gardes=generer_gardes, biome=biome,
            longueur_obstacles=long_obs,
        )

        ground = BIOMES.get(biome, BIOMES["default"])["ground"]
        self.piste_j1 = PisteSol(self.y_sol_j1, ground)
        self.piste_j2 = PisteSol(self.y_sol_j2, ground)

        # ── Mode solo J1 seul ────────────────────────────────────────────────
        # Si True : J2 n'existe pas (pas de mise à jour, pas de dessin, pas de collision).
        # La piste du bas est quand même rendue (fond + sol qui défile) mais vide.
        self.solo_j1 = config_niveau.get("solo_j1", False)

        # ── IA J2 : solo+IA (obligatoire) ou local (secours jusqu'à ↑/↓) ─────
        # Désactivée en réseau (chaque PC contrôle son joueur) et en solo_j1 (pas de J2).
        self.j2_force_ia        = config_niveau.get("j2_force_ia", False)
        self.ai_j2             = (config_niveau.get("ai_j2", False)
                                  and client_reseau is None
                                  and not self.solo_j1)
        self.j2_manuel_detecte = False   # désactive l'IA si J2 appuie sur ses touches (local)
        self._ia_j2: IAJoueur2 | None = None
        if self.ai_j2:
            ia_seed = seed if seed is not None else random.randint(0, 2**31)
            self._ia_j2 = IAJoueur2(
                skill=0.78 if self.j2_force_ia else 0.60,
                rng=random.Random(ia_seed),
                fiable=self.j2_force_ia,
            )

        # ── Score pièces ────────────────────────────────────────────────────
        self.score_pieces = 0

        # ── Ligne d'arrivée ─────────────────────────────────────────────────
        # Placée en coordonnées monde : quand distance == longueur_niveau,
        # elle se trouve à x = longueur_niveau + 220 - longueur_niveau = 220
        # → pile sous le joueur, comme si on la franchit.
        # Niveau boss : la ligne FINISH n'existe qu'après la défaite du boss.
        self.finish_x = -8000.0 if self.mode_boss else float(self.longueur_niveau + 260)

        # ── Milestones (25 % / 50 % / 75 %) ─────────────────────────────────
        self._milestones       = {int(self.longueur_pre_boss * p) for p in (0.25, 0.50, 0.75)}
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

        # ── Mini-boss (niveau 5) ─────────────────────────────────────────────
        self.en_boss = False
        self.boss_defeated = False
        self._boss_annonce = False
        self.mini_boss: MiniBoss | None = None
        if self.mode_boss:
            self.mini_boss = MiniBoss(self.y_sol_j1, self.y_sol_j2, solo_j1=self.solo_j1)
        self._boss_msg_flash = 0
        self._boss_msg_texte = ""
        self.tirs_joueurs: list[ProjectileJoueur] = []
        self._j1_etait_slide = False
        self._j2_etait_slide = False
        self._boss_tir_cd_j1 = 0
        self._boss_tir_cd_j2 = 0

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
            numero_niveau=self.numero_niveau,
        )
        SONS.play("win" if victoire else "lose")

    def _j2_subit_degats(self) -> bool:
        """En solo+IA le partenaire IA ne fait pas perdre la partie."""
        if self.j2_force_ia:
            return False
        return self.joueur2.touche()

    def _ia_touches_j2(self, touches_reelles):
        """Délègue à IAJoueur2 (obstacles + projectiles, timing selon la vitesse)."""
        if self._ia_j2 is None:
            return touches_reelles
        extra_obs, extra_proj = [], []
        if self.mini_boss and self.en_boss:
            extra_obs = self.mini_boss.obstacles_j2
            extra_proj = self.mini_boss.projectiles
        overrides = self._ia_j2.decider(
            self.joueur2, self.circuit_j2, self.vitesse, self.frame,
            extra_obstacles=extra_obs, extra_projectiles=extra_proj,
        )
        return FauxTouches(touches_reelles, overrides)

    def _ia_corriger_posture_j2(self) -> None:
        """Solo+IA : maintient glissade/saut de dernière seconde pour franchir le niveau."""
        if not self.j2_force_ia:
            return
        j = self.joueur2
        jx = j.x
        v = self.vitesse

        for garde in self.circuit_j2.gardes:
            for proj in garde.projectiles:
                if not proj.actif:
                    continue
                d = proj.x - jx
                if d < -15 or d > 260 + v * 18:
                    continue
                haut = j.y_sol - Garde._TIR_OFFSET
                if abs(proj.y - haut) > 32:
                    continue
                if j.sur_sol:
                    j.slide = True
                    j.y = float(j.y_sol - j.hauteur_slide)
                    j.slide_timer = max(j.slide_timer, 20)
                return

        for obs in self.circuit_j2.obstacles:
            if obs.type != "high":
                continue
            d = obs.x - jx
            largeur = getattr(obs, "largeur", 70)
            proche_sol = j.y >= j.y_sol - j.hauteur - 12
            if d + largeur < -12 or d > 95 + v * 8:
                continue
            rect_j = j.get_rect().inflate(-16, -18)
            chevauche = rect_j.colliderect(obs.get_rect())
            if j.sur_sol or (proche_sol and d < 70):
                if not j.slide:
                    j.slide = True
                    j.y = float(j.y_sol - j.hauteur_slide)
                j.slide_timer = max(j.slide_timer, max(24, j.slide_duree_min + 10))
            elif chevauche and proche_sol:
                j.y = float(j.y_sol - j.hauteur_slide)
                j.slide = True
                j.slide_timer = max(j.slide_timer, 18)
            return

        rect_j = j.get_rect().inflate(-16, -18)
        for obs in self.circuit_j2.obstacles:
            if obs.type != "low":
                continue
            d = obs.x - jx
            if d < -10 or d > 88 + v * 5:
                continue
            if rect_j.colliderect(obs.get_rect()) and j.sur_sol and not j.slide:
                j.vy = j.force_saut
                j.sur_sol = False
                j.vient_de_sauter = True
                j.cooldown_saut = 8
                j.saut_buffer = 0
                return
            if j.sur_sol and not j.slide and d < 72 + v * 4:
                j.vy = j.force_saut
                j.sur_sol = False
                j.vient_de_sauter = True
                j.cooldown_saut = 8
                j.saut_buffer = 0
            return

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

        # ── Mode réseau : échange d'états avec le serveur ───────────────────
        if self.client_reseau is not None:
            self._update_reseau(touches)
            return

        # ── Mise à jour joueurs ──────────────────────────────────────────────
        self.joueur1.update(touches)
        if self.joueur1.vient_de_sauter:
            SONS.play("jump")

        if not self.solo_j1:
            # En local, ↑/↓ reprennent la main sur l'IA ; en solo+IA, J2 reste IA.
            if not self.j2_force_ia and (touches[pygame.K_UP] or touches[pygame.K_DOWN]):
                self.j2_manuel_detecte = True
            if self.ai_j2 and not self.j2_manuel_detecte:
                self.joueur2.update(self._ia_touches_j2(touches))
                if self.j2_force_ia:
                    self._ia_corriger_posture_j2()
            else:
                self.joueur2.update(touches)
            if self.joueur2.vient_de_sauter:
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

        self._update_boss_et_arrivee()

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

        # ── Collisions J1 (obstacles + projectiles des gardes) ───────────────
        rect1 = self.joueur1.get_rect().inflate(-16, -18)
        for obs in self.circuit_j1.obstacles:
            if rect1.colliderect(obs.get_rect()):
                if self.joueur1.touche():
                    SONS.play("hit")
                    self._spawn_particules(self.joueur1)
                    if not self.joueur1.en_vie:
                        self._terminer(False)
                        return
        for garde in self.circuit_j1.gardes:
            for proj in garde.projectiles:
                if rect1.colliderect(proj.get_rect()):
                    proj.actif = False
                    if self.joueur1.touche():
                        SONS.play("hit")
                        self._spawn_particules(self.joueur1)
                        if not self.joueur1.en_vie:
                            self._terminer(False)
                            return

        if self._collisions_mini_boss_joueur(self.joueur1, 1):
            return

        # ── Collisions J2 (désactivées en solo_j1) ───────────────────────────
        if not self.solo_j1:
            rect2 = self.joueur2.get_rect().inflate(-16, -18)
            for obs in self.circuit_j2.obstacles:
                if rect2.colliderect(obs.get_rect()):
                    if self._j2_subit_degats():
                        SONS.play("hit")
                        self._spawn_particules(self.joueur2)
                        if not self.joueur2.en_vie:
                            self._terminer(False)
                            return
            for garde in self.circuit_j2.gardes:
                for proj in garde.projectiles:
                    if rect2.colliderect(proj.get_rect()):
                        proj.actif = False
                        if self._j2_subit_degats():
                            SONS.play("hit")
                            self._spawn_particules(self.joueur2)
                            if not self.joueur2.en_vie:
                                self._terminer(False)
                                return

            if self._collisions_mini_boss_joueur(self.joueur2, 2):
                return
        elif self.joueur2.en_vie and self.en_boss:
            # Solo + IA : J2 participe quand même au combat boss
            if self._collisions_mini_boss_joueur(self.joueur2, 2):
                return

        # ── Collecte des pièces ──────────────────────────────────────────────
        circuits_actifs = [(self.circuit_j1, self.joueur1)]
        if not self.solo_j1:
            circuits_actifs.append((self.circuit_j2, self.joueur2))
        for circuit, joueur in circuits_actifs:
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

        # ── Victoire ─────────────────────────────────────────────────────────
        if self.mode_boss:
            if (self.boss_defeated and self.mini_boss
                    and self.mini_boss.explosion_timer <= 0):
                self._terminer(True)
        elif self.distance >= self.longueur_niveau:
            self._terminer(True)

    # ── Réseau ───────────────────────────────────────────────────────────────

    def _update_reseau(self, touches):
        """
        Boucle de mise à jour en mode réseau.

        Principe :
          - Ce PC contrôle uniquement son joueur local (player_id 0→J1, 1→J2).
          - La physique du joueur local est calculée normalement (touches clavier).
          - L'état du joueur local est envoyé au serveur chaque frame.
          - L'état du joueur distant (reçu du serveur) est appliqué visuellement.
          - Les deux PCs tournent le même seed random → mêmes obstacles.
          - Chacun détecte ses propres collisions et victoire de façon indépendante.
        """
        joueur_local   = self.joueur1 if self.player_id == 0 else self.joueur2
        joueur_distant = self.joueur2 if self.player_id == 0 else self.joueur1
        circuit_local  = self.circuit_j1 if self.player_id == 0 else self.circuit_j2

        # ── Mise à jour du joueur local ──────────────────────────────────────
        joueur_local.update(touches)
        if joueur_local.vient_de_sauter:
            SONS.play("jump")

        # ── Envoie l'état local au serveur ───────────────────────────────────
        self.client_reseau.envoyer_etat_joueur(joueur_local)

        # Heartbeat toutes les 30 frames (~0.2 sec à 144 FPS) pour maintenir la connexion
        self._heartbeat_counter += 1
        if self._heartbeat_counter >= 30:
            self._heartbeat_counter = 0
            try:
                self.client_reseau._envoyer({'type': 'heartbeat'})
            except Exception as e:
                print(f"[JEU] Erreur heartbeat: {e}")
                if not self.client_reseau.connecte:
                    print("[JEU] Connexion perdue après heartbeat")
                    self._terminer(False)
                    return

        # ── Reçoit et applique l'état du joueur distant ──────────────────────
        etat_distant = self.client_reseau.get_etat_joueur_distant()
        if etat_distant:
            self._appliquer_etat_reseau(joueur_distant, etat_distant)

        # ── Vérifie les messages spéciaux (déconnexion, game_over serveur) ───
        etat_jeu = self.client_reseau.get_etat_jeu()
        if etat_jeu:
            t = etat_jeu.get('type')
            if t in ('player_disconnected', 'server_shutdown') and not self.termine:
                print(f"[JEU] Message spécial réseau: {t}")
                self._terminer(False)
                return

        # ── Accélération + décor ─────────────────────────────────────────────
        if self.vitesse < self.vitesse_max:
            self.vitesse += self.acceleration
        self.offset_piste += self.vitesse
        self.fond.update(self.vitesse)
        self.piste_j1.update(self.vitesse)
        self.piste_j2.update(self.vitesse)
        self.circuit_j1.update(self.vitesse)
        self.circuit_j2.update(self.vitesse)
        self.distance += self.vitesse
        self._update_boss_et_arrivee()

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

        # ── Collisions du joueur local uniquement (obstacles + projectiles) ───
        rect_local = joueur_local.get_rect().inflate(-16, -18)
        for obs in circuit_local.obstacles:
            if rect_local.colliderect(obs.get_rect()):
                if joueur_local.touche():
                    SONS.play("hit")
                    self._spawn_particules(joueur_local)
                    if not joueur_local.en_vie:
                        self._terminer(False)
                        return
        for garde in circuit_local.gardes:
            for proj in garde.projectiles:
                if rect_local.colliderect(proj.get_rect()):
                    proj.actif = False
                    if joueur_local.touche():
                        SONS.play("hit")
                        self._spawn_particules(joueur_local)
                        if not joueur_local.en_vie:
                            self._terminer(False)
                            return

        # ── Collecte des pièces (joueur local seulement) ─────────────────────
        jrect = joueur_local.get_rect()
        for piece in circuit_local.pieces:
            if not piece.collectee and jrect.colliderect(piece.get_rect()):
                piece.collectee = True
                self.score_pieces += 1
                for _ in range(8):
                    self.particules.append(Particule(piece.x, piece.y, (255, 215, 0)))

        # ── Victoire ────────────────────────────────────────────────────────
        if self.mode_boss:
            if (self.boss_defeated and self.mini_boss
                    and self.mini_boss.explosion_timer <= 0):
                self._terminer(True)
        elif self.distance >= self.longueur_niveau:
            self._terminer(True)

        # ── Collisions mini-boss (joueur local, tous modes) ─────────────────
        num_local = 1 if joueur_local is self.joueur1 else 2
        if self._collisions_mini_boss_joueur(joueur_local, num_local):
            return

    def _appliquer_etat_reseau(self, joueur, etat: dict):
        """
        Applique l'état reçu du réseau sur le joueur distant (visuel uniquement).
        On met à jour position, vitesse verticale et animation mais on ne
        recalcule pas la physique — c'est le PC distant qui la gère.
        """
        joueur.x      = etat.get('x',          joueur.x)
        joueur.y      = etat.get('y',          joueur.y)
        joueur.vy     = etat.get('velocity_y', joueur.vy)
        joueur.sur_sol = not etat.get('is_jumping', False)
        joueur.slide   = etat.get('is_sliding', False)

        # Synchronise l'animation avec l'état reçu
        if joueur.utilise_sprite:
            anim_state = etat.get('animation_state', 'run')
            if anim_state == 'slide' and joueur.sliding_frames:
                if joueur.current_animation is not joueur.sliding_frames:
                    joueur.current_animation = joueur.sliding_frames
                    joueur.index_frame = 0
            elif anim_state == 'jump' and joueur.jumping_frames:
                if joueur.current_animation is not joueur.jumping_frames:
                    joueur.current_animation = joueur.jumping_frames
                    joueur.index_frame = 0
            else:
                if joueur.current_animation is not joueur.running_frames:
                    joueur.current_animation = joueur.running_frames
                    joueur.index_frame = 0
            # Avance l'animation côté distant pour qu'elle ne soit pas figée
            joueur.animation_timer += 1
            if joueur.animation_timer >= joueur.vitesse_animation:
                joueur.animation_timer = 0
                joueur.index_frame = (joueur.index_frame + 1) % max(1, len(joueur.current_animation))

    def _spawn_particules(self, joueur):
        rect = joueur.get_rect()
        for _ in range(22):
            c = random.choice([ROUGE, ORANGE, JAUNE])
            self.particules.append(Particule(rect.centerx, rect.centery, c))

    def _arrivee_visible(self) -> bool:
        """La ligne FINISH n'apparaît qu'en fin de niveau normal, ou après le boss."""
        return not self.mode_boss or self.boss_defeated

    def _get_cible_boss_xy(self):
        mb = self.mini_boss
        bob = int(math.sin(mb.anim * 0.08) * 4)
        return float(mb.x - 28), float(118 + bob)

    def _origine_tir_joueur(self, joueur):
        """Point de départ du tir : devant le personnage, vers la fenêtre du boss."""
        rect = joueur.get_rect()
        ox = float(rect.right - 6)
        if joueur.slide:
            oy = float(rect.centery)
        elif joueur.sur_sol:
            oy = float(rect.centery - 10)
        else:
            oy = float(rect.centery - 4)
        return ox, oy

    def _update_boss_et_arrivee(self):
        """Boss, tirs joueurs et ligne d'arrivée — partagé local / solo / 2P / réseau."""
        if self.mode_boss and self.mini_boss:
            if not self.en_boss and self.distance >= self.boss_zone_start:
                self.en_boss = True
                self.mini_boss.demarrer()
                self._boss_msg_texte = "LE DIRECTEUR MAGNUS !"
                self._boss_msg_flash = 150
            if self.en_boss:
                mb = self.mini_boss
                mb.set_zone_boss(self.boss_zone_start, self.longueur_pre_boss)
                if mb.intro_flash <= 0:
                    mb.mettre_a_jour_vie(self.distance)
                else:
                    mb.vie_ratio = 1.0
                mb.update(self.vitesse)
                if (self.distance >= self.longueur_pre_boss
                        and not mb.vaincu and mb.explosion_timer == 0):
                    mb._demarrer_explosion()
                self._gerer_tirs_joueurs_boss()
                self._update_tirs_joueurs()
                if mb.explosion_timer == mb.EXPLOSION_DUREE - 1:
                    self.tirs_joueurs.clear()
                if mb.vaincu and mb.explosion_timer <= 0 and not self.boss_defeated:
                    self.boss_defeated = True
                    self._boss_msg_texte = "DIRECTEUR VAINCU !"
                    self._boss_msg_flash = 150
                    SONS.play("win")
                    for _ in range(50):
                        self.particules.append(
                            Particule(mb.x, 150, (255, 80, 60))
                        )
        if self._boss_msg_flash > 0:
            self._boss_msg_flash -= 1
        if self._arrivee_visible():
            self.finish_x -= self.vitesse

    def _tirer_sur_boss(self, joueur, couleur):
        if not self.en_boss or not self.mini_boss or self.mini_boss.vaincu:
            return
        if self.mini_boss.intro_flash > 60 or not joueur.en_vie:
            return
        ox, oy = self._origine_tir_joueur(joueur)
        cx, cy = self._get_cible_boss_xy()
        self.tirs_joueurs.append(ProjectileJoueur(ox, oy, couleur, cx, cy))

    def _gerer_tir_joueur_boss(self, joueur, cd_attr: str, etait_slide_attr: str):
        cd = getattr(self, cd_attr)
        if cd > 0:
            setattr(self, cd_attr, cd - 1)
            return
        etait_slide = getattr(self, etait_slide_attr)
        slide_debut = joueur.slide and not etait_slide
        # Tir uniquement au saut, au slide, ou en course au sol (pas en plein vol)
        tirer = False
        if joueur.vient_de_sauter or slide_debut:
            tirer = True
        elif joueur.sur_sol and not joueur.slide and self.frame % 24 == (0 if cd_attr == "_boss_tir_cd_j1" else 12):
            tirer = True
        setattr(self, etait_slide_attr, joueur.slide)
        if tirer:
            self._tirer_sur_boss(joueur, joueur.couleurs[0])
            setattr(self, cd_attr, 10)

    def _gerer_tirs_joueurs_boss(self):
        mb = self.mini_boss
        if not mb or mb.vaincu or mb.explosion_timer > 0:
            return
        self._gerer_tir_joueur_boss(self.joueur1, "_boss_tir_cd_j1", "_j1_etait_slide")
        if self.joueur2.en_vie:
            self._gerer_tir_joueur_boss(self.joueur2, "_boss_tir_cd_j2", "_j2_etait_slide")

        hitbox = mb.get_hitbox_rect()
        for tir in self.tirs_joueurs:
            if not tir.actif:
                continue
            if hitbox.colliderect(tir.get_rect()):
                tir.actif = False
                if mb.recevoir_tir_joueur():
                    for _ in range(6):
                        self.particules.append(
                            Particule(tir.x, tir.y, (255, 200, 80))
                        )

    def _update_tirs_joueurs(self):
        cx, cy = (None, None)
        if self.en_boss and self.mini_boss and not self.mini_boss.vaincu:
            cx, cy = self._get_cible_boss_xy()
        for tir in self.tirs_joueurs:
            if tir.actif:
                tir.update(cx, cy)
        self.tirs_joueurs = [t for t in self.tirs_joueurs if t.actif]

    def _collisions_mini_boss_joueur(self, joueur, joueur_num: int = 1):
        if not (self.en_boss and self.mini_boss and not self.mini_boss.vaincu
                and self.mini_boss.explosion_timer == 0):
            return False
        mb = self.mini_boss
        rect = joueur.get_rect().inflate(-16, -18)
        subit = joueur.touche if joueur_num == 1 else self._j2_subit_degats
        for proj in mb.projectiles:
            if not proj.actif:
                continue
            if rect.colliderect(proj.get_rect()):
                proj.actif = False
                if subit():
                    mb.notifier_touche(joueur_num)
                    SONS.play("hit")
                    self._spawn_particules(joueur)
                    if not joueur.en_vie:
                        self._terminer(False)
                        return True
        obs_list = mb.obstacles_j1 if joueur_num == 1 else mb.obstacles_j2
        for obs in obs_list:
            if rect.colliderect(obs.get_rect()):
                if subit():
                    mb.notifier_touche(joueur_num)
                    SONS.play("hit")
                    self._spawn_particules(joueur)
                    if not joueur.en_vie:
                        self._terminer(False)
                        return True
        return False

    # ── Dessin ───────────────────────────────────────────────────────────────
    def dessiner(self, ecran):
        self.fond.dessiner(ecran)

        pulse = int(60 * abs(((self.frame % 40) / 20) - 1))
        self.circuit_j1.dessiner(ecran, pulse)
        # En solo_j1 : pas d'obstacles ni pièces sur la piste basse, mais le sol défile
        if not self.solo_j1:
            self.circuit_j2.dessiner(ecran, pulse)

        # Pistes de sol (toujours visibles, même en solo_j1)
        self.piste_j1.dessiner(ecran)
        self.piste_j2.dessiner(ecran)

        # ── Ligne d'arrivée (jamais pendant le combat boss) ─────────────────
        if self._arrivee_visible() and -50 < self.finish_x < LARGEUR + 50:
            lax = int(self.finish_x)
            tile = 24
            for yi in range(0, HAUTEUR, tile):
                col = BLANC if (yi // tile + (lax // tile)) % 2 == 0 else NOIR
                pygame.draw.rect(ecran, col, (lax - 15, yi, 30, tile))
            pygame.draw.rect(ecran, (255, 215, 0), (lax - 16, 0, 32, HAUTEUR), 2)
            txt_fin = police(38).render("FINISH!", True, (255, 215, 0))
            ecran.blit(txt_fin, txt_fin.get_rect(center=(lax, HAUTEUR // 2 - 20)))

        # ── Indicateur de zone d'arrivée (dernier 15 %) ──────────────────────
        if not self.mode_boss and self.distance >= self.longueur_niveau * 0.85 and not self.termine:
            pct_fin = (self.distance - self.longueur_niveau * 0.85) / (self.longueur_niveau * 0.15)
            alpha_warn = int(min(1.0, pct_fin) * 180)
            warn_surf  = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
            warn_surf.fill((255, 215, 0, alpha_warn // 8))
            ecran.blit(warn_surf, (0, 0))
            txt_near = police(42).render("ARRIVÉE PROCHE !", True, (255, 215, 0))
            alpha_txt = int(abs(math.sin(self.frame * 0.10)) * 220)
            txt_near.set_alpha(alpha_txt)
            ecran.blit(txt_near, txt_near.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 - 70)))

        if self.mode_boss and not self.en_boss and self.distance >= self.boss_zone_start * 0.85 and not self.termine:
            pct_fin = (self.distance - self.boss_zone_start * 0.85) / max(1, self.boss_zone_start * 0.15)
            alpha_warn = int(min(1.0, max(0, pct_fin)) * 180)
            warn_surf  = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
            warn_surf.fill((255, 60, 60, alpha_warn // 8))
            ecran.blit(warn_surf, (0, 0))
            txt_near = police(42).render("ZONE DU BOSS !", True, (255, 100, 100))
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

        # ── Mini-boss (tour, avant les joueurs ; explosion dessinée après) ───
        if self.en_boss and self.mini_boss and self.mini_boss.explosion_timer == 0:
            self.mini_boss.dessiner(ecran)

        # ── Joueurs ──────────────────────────────────────────────────────────
        self.joueur1.dessiner(ecran)
        if not self.solo_j1:
            self.joueur2.dessiner(ecran)

        if self.en_boss and self.mini_boss and self.mini_boss.explosion_timer > 0:
            self.mini_boss.dessiner(ecran)

        # ── Projectiles des gardes (au premier plan, après les joueurs) ──────
        self.circuit_j1.dessiner_projectiles(ecran)
        if not self.solo_j1:
            self.circuit_j2.dessiner_projectiles(ecran)

        if self.en_boss and self.mini_boss:
            self.mini_boss.dessiner_obstacles(ecran, pulse)
            self.mini_boss.dessiner_projectiles(ecran)

        for tir in self.tirs_joueurs:
            if tir.actif:
                tir.dessiner(ecran)

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

        # ── Annonce boss ─────────────────────────────────────────────────────
        if self._boss_msg_flash > 0:
            a = int((self._boss_msg_flash / 150) * 255)
            boss_txt = police(52).render(self._boss_msg_texte, True, (255, 80, 80))
            boss_txt.set_alpha(min(255, a))
            ecran.blit(boss_txt, boss_txt.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 - 90)))

        # ── Danger flash (vie critique) ──────────────────────────────────────
        if self.joueur1.vies == 1 and self.frame % 20 < 10:
            danger = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
            danger.fill((255, 0, 0, 28))
            ecran.blit(danger, (0, 0))

        # ── HUD ─────────────────────────────────────────────────────────────
        compte_rebours_affiche = 0
        if not self.en_jeu:
            compte_rebours_affiche = max(1, int(math.ceil(self.countdown_frames / FPS)))

        j2_hud = None if self.solo_j1 else self.joueur2
        dessiner_hud(ecran, self.joueur1, j2_hud,
                     self.distance, self.longueur_niveau,
                     self.vitesse, self.vitesse_max,
                     self.nom_niveau, compte_rebours_affiche,
                     self.score_pieces, j2_ia=self.j2_force_ia)

        if self.ecran_fin:
            self.ecran_fin.dessiner(ecran)
            return


# ──────────────────────────────────────────────
#  BOUCLE PRINCIPALE
# ──────────────────────────────────────────────
def lancer_jeu(ecran, config_niveau=None, client_reseau=None, player_id=0, seed=None,
               get_nouveau_niveau=None):
    """
    Boucle principale d'une partie.

    Appelée depuis menu.py après sélection du niveau.
    Retourne True  si le joueur revient au menu (ESC ou fin de partie).
    Retourne False si la fenêtre est fermée.

    Paramètres réseau (optionnels, passés depuis menu.py) :
      client_reseau    : ClientReseau connecté, ou None (local/solo)
      player_id        : 0 = J1, 1 = J2
      seed             : graine random partagée (synchronise les obstacles en réseau)
      get_nouveau_niveau : callable() → config_niveau | None  (pour la touche D)

    Touches en fin de partie :
      R   = rejouer le même niveau (mode local/solo uniquement)
      N   = niveau suivant (si existe)
      D   = choisir un autre niveau (via get_nouveau_niveau callback)
      ESC = retour au menu
    """
    horloge   = pygame.time.Clock()
    partie    = JeuDeuxJoueurs(config_niveau,
                               client_reseau=client_reseau,
                               player_id=player_id,
                               seed=seed)
    flash_msg  = ""   # message temporaire affiché sur l'écran de fin
    flash_timer = 0   # durée restante en frames

    while True:
        horloge.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True

                if partie.termine and client_reseau is None:
                    fin = partie.ecran_fin

                    # R = rejouer le même niveau
                    if event.key == pygame.K_r:
                        return lancer_jeu(ecran, config_niveau,
                                          get_nouveau_niveau=get_nouveau_niveau)

                    # Suite : Entrée, Espace ou N
                    if partie.victoire and event.key in (
                        pygame.K_RETURN, pygame.K_SPACE, pygame.K_n,
                    ):
                        if fin and fin.prochain:
                            return lancer_jeu(
                                ecran, _config_niveau_suivant(config_niveau, fin.prochain["numero"]),
                                get_nouveau_niveau=get_nouveau_niveau,
                            )
                        if event.key == pygame.K_n:
                            flash_msg = "Bientôt disponible !"
                            flash_timer = 180

                    if fin and event.key not in (
                        pygame.K_RETURN, pygame.K_SPACE, pygame.K_n, pygame.K_r,
                    ):
                        fin.annuler_auto_continue()

                    # D = choisir un autre niveau (via menu)
                    if event.key == pygame.K_d and partie.victoire and get_nouveau_niveau:
                        nouveau = get_nouveau_niveau()
                        if nouveau is not None:
                            nouveau = dict(nouveau)
                            nouveau["ai_j2"]       = config_niveau.get("ai_j2",   False)
                            nouveau["j2_force_ia"] = config_niveau.get("j2_force_ia", False)
                            nouveau["solo_j1"]     = config_niveau.get("solo_j1", False)
                            for cle in ("biome", "mode_boss", "boss_zone_pct", "boss_run_after"):
                                if cle in config_niveau:
                                    nouveau[cle] = config_niveau[cle]
                            return lancer_jeu(ecran, nouveau,
                                              get_nouveau_niveau=get_nouveau_niveau)

        if flash_timer > 0:
            flash_timer -= 1

        touches = pygame.key.get_pressed()
        partie.update(touches)

        if (partie.termine and partie.victoire and partie.ecran_fin
                and partie.ecran_fin.prochain and client_reseau is None):
            if partie.ecran_fin.tick_auto_continue():
                return lancer_jeu(
                    ecran,
                    _config_niveau_suivant(config_niveau, partie.ecran_fin.prochain["numero"]),
                    get_nouveau_niveau=get_nouveau_niveau,
                )

        partie.dessiner(ecran)

        # Flash message (ex : "Bientôt disponible !")
        if flash_timer > 0:
            alpha = min(255, flash_timer * 6)
            surf = police(30).render(flash_msg, True, JAUNE)
            surf.set_alpha(alpha)
            ecran.blit(surf, surf.get_rect(center=(LARGEUR // 2, HAUTEUR // 2 + 190)))

        pygame.display.flip()
