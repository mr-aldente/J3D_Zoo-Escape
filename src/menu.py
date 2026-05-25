"""
menu.py — Menu principal de Zoo Escape
========================================
Point d'entrée du jeu (lancé directement : python menu.py).

Responsabilités :
  - Charger / sauvegarder les paramètres utilisateur (config.json)
  - Afficher le menu principal avec fond vidéo (background.mp4) et logo animé
  - Gérer le sous-menu Paramètres (volume, résolution) via MenuParametres
  - Afficher l'écran de sélection de mode (SOLO / LOCAL / RÉSEAU)
  - Afficher l'écran réseau (Héberger / Rejoindre + saisie IP)
  - Afficher l'écran de sélection de niveaux (afficher_selection_niveaux)
  - Lancer une partie via jeu.lancer_jeu()

Structure :
  CONFIG_FILE              → chemin vers config.json (résolution, volumes)
  Slider                   → composant UI pour les sliders de volume
  Bouton              → bouton plein avec survol
  BoutonTransparent   → bouton semi-transparent style menu principal
  MenuParametres      → logique + rendu du sous-menu paramètres
  afficher_menu()     → boucle principale du menu
"""

import pygame
import sys
import os
import json
import math
import subprocess
import socket as _socket
import jeu
import client_reseau as reseau
pygame.init()
pygame.mixer.init()

LARGEUR = 1024
HAUTEUR = 768
FPS = 60

BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
ACCENT = (56, 189, 248)
VERT = (80, 240, 130)
RANGE = (255, 140, 0)
JAUNE_LOGO = (252, 227, 13)  # Couleur du logo Zoo Escape
JAUNE = (255, 215, 0)
GRIS = (100, 100, 100)

# ── Persistance ────────────────────────────────────────────────────────────────
# config.json est stocké dans le même dossier que ce script.
# Il contient : largeur, hauteur, volume_musique, volume_sons, resolution_index.
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def charger_config():
    config_defaut = {
        "largeur": 1024,
        "hauteur": 768,
        "volume_musique": 0.5,
        "volume_sons": 0.7,
        "resolution_index": 1,
        # layout_clavier absent → demandé au premier lancement
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                config_defaut.update(config)
        except:
            pass
    return config_defaut

def sauvegarder_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Erreur sauvegarde config: {e}")

CONFIG = charger_config()
LARGEUR = int(CONFIG["largeur"])
HAUTEUR = int(CONFIG["hauteur"])

ecran = pygame.display.set_mode((LARGEUR, HAUTEUR))

# ── Layout clavier (AZERTY / QWERTY) ───────────────────────────────────────────
# Chargé depuis config.json ; mis à jour par afficher_selection_clavier().
# AZERTY : haut J1 = Z  (K_z), gauche menu = Q (K_q)
# QWERTY : haut J1 = W  (K_w), gauche menu = A (K_a)
LAYOUT_CLAVIER: str = CONFIG.get("layout_clavier", "azerty")
K_J1_HAUT     : int = pygame.K_z if LAYOUT_CLAVIER == "azerty" else pygame.K_w
K_MENU_GAUCHE : int = pygame.K_q if LAYOUT_CLAVIER == "azerty" else pygame.K_a


def _appliquer_layout(layout: str) -> None:
    """Met à jour les variables de touches globales selon le layout choisi."""
    global LAYOUT_CLAVIER, K_J1_HAUT, K_MENU_GAUCHE
    LAYOUT_CLAVIER = layout
    K_J1_HAUT      = pygame.K_z if layout == "azerty" else pygame.K_w
    K_MENU_GAUCHE  = pygame.K_q if layout == "azerty" else pygame.K_a
    CONFIG["layout_clavier"] = layout
    sauvegarder_config(CONFIG)

# ── Personnages jouables ────────────────────────────────────────────────────────
PERSONNAGES = [
    {"nom": "Fox",      "dossier": "Fox",   "couleurs": ((225, 120,  90), (255, 170, 140))},
    {"nom": "Raton",    "dossier": "Raton", "couleurs": ((140, 150, 170), (200, 210, 225))},
    {"nom": "Lion",     "dossier": "Fox",   "couleurs": ((230, 180,  60), (255, 220, 120))},
    {"nom": "Penguin",  "dossier": "Fox",   "couleurs": ((60,   80, 120), (120, 140, 180))},
    {"nom": "Parrot",   "dossier": "Fox",   "couleurs": ((80,  200, 100), (140, 230, 150))},
    {"nom": "Shark",    "dossier": "Fox",   "couleurs": ((60,  150, 230), (120, 190, 255))},
]
PERSO_J1_INDEX = 0
PERSO_J2_INDEX = 1

pygame.display.set_caption("Zoo Escape - Menu Principal")

RESOLUTIONS = [(800, 600), (1024, 768), (1280, 720), (1366, 768), (1600, 900)]

def appliquer_volumes(config):
    volume_musique = max(0.0, min(1.0, config.get("volume_musique", 0.5)))
    volume_sons = max(0.0, min(1.0, config.get("volume_sons", 0.7)))
    pygame.mixer.music.set_volume(volume_musique)
    for index in range(pygame.mixer.get_num_channels()):
        pygame.mixer.Channel(index).set_volume(volume_sons)
    jeu.configurer_audio(volume_sons)

def mettre_a_jour_config(config):
    CONFIG.update(config)
    sauvegarder_config(CONFIG)

# ── Composants UI ──────────────────────────────────────────────────────────────

class Slider:
    """
    Barre de défilement horizontale pour régler un volume (0-100).
    Le curseur (knob) peut être glissé à la souris.
    La valeur est un entier [min_val, max_val] affiché en % au-dessus du slider.
    """
    def __init__(self, x, y, largeur, min_val, max_val, valeur, label):
        self.x = x
        self.y = y
        self.largeur = largeur
        self.hauteur = 8
        self.min_val = min_val
        self.max_val = max_val
        self.valeur = valeur
        self.label = label
        self.drag = False

    def _ratio(self):
        return (self.valeur - self.min_val) / (self.max_val - self.min_val) if self.max_val > self.min_val else 0

    def _knob_x(self):
        return self.x + int(self.largeur * self._ratio())

    def dessiner(self, ecran, police):
        pygame.draw.rect(ecran, (72, 82, 98), (self.x, self.y, self.largeur, self.hauteur), border_radius=6)
        pygame.draw.rect(ecran, GRIS, (self.x, self.y, self.largeur, self.hauteur), border_radius=6)
        pygame.draw.rect(ecran, ACCENT, (self.x, self.y, max(1, self._knob_x() - self.x), self.hauteur), border_radius=6)
        pygame.draw.circle(ecran, BLANC, (self._knob_x(), self.y + self.hauteur // 2), 11)
        pygame.draw.circle(ecran, NOIR, (self._knob_x(), self.y + self.hauteur // 2), 11, 2)

        txt = police.render(f"{self.label}: {self.valeur}%", True, BLANC)
        txt_rect = txt.get_rect(center=(self.x + self.largeur // 2, self.y - 26))
        ecran.blit(txt, txt_rect)

    def gerer_evenement(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            knob_rect = pygame.Rect(self._knob_x() - 13, self.y - 8, 26, 24)
            if knob_rect.collidepoint(event.pos):
                self.drag = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.drag = False
        elif event.type == pygame.MOUSEMOTION and self.drag:
            self._set_from_mouse(event.pos[0])

    def _set_from_mouse(self, mouse_x):
        ratio = (mouse_x - self.x) / self.largeur
        ratio = max(0.0, min(1.0, ratio))
        self.valeur = int(round(self.min_val + ratio * (self.max_val - self.min_val)))

class Bouton:
    """Bouton plein (fond coloré + bordure blanche). Utilisé dans le sous-menu paramètres."""
    def __init__(self, x, y, largeur, hauteur, texte, couleur=None):
        self.rect = pygame.Rect(x, y, largeur, hauteur)
        self.texte = texte
        self.couleur = couleur or ACCENT
        self.est_survole = False
        self.police = pygame.font.Font(None, 36)

    def dessiner(self, ecran):
        halo = pygame.Surface((self.rect.width + 24, self.rect.height + 24), pygame.SRCALPHA)
        couleur = self.couleur if not self.est_survole else tuple(min(c + 50, 255) for c in self.couleur)
        if self.est_survole:
            pygame.draw.rect(halo, (*self.couleur, 55), halo.get_rect(), border_radius=16)
            ecran.blit(halo, (self.rect.x - 10, self.rect.y - 10))
        pygame.draw.rect(ecran, couleur, self.rect, border_radius=10)
        pygame.draw.rect(ecran, BLANC, self.rect, 2, border_radius=10)
        
        txt = self.police.render(self.texte, True, BLANC)
        txt_rect = txt.get_rect(center=self.rect.center)
        ecran.blit(txt, txt_rect)

    def verifier_survol(self, pos):
        self.est_survole = self.rect.collidepoint(pos)

    def est_clique(self, pos):
        return self.rect.collidepoint(pos)

class BoutonTransparent:
    """
    Bouton semi-transparent avec effet de survol lumineux.
    Utilisé pour les boutons du menu principal (JOUER, PARAMETRES, QUITTER).
    Au repos : fond noir semi-transparent + bordure colorée.
    Au survol : fond et texte mis en valeur, halo autour du bouton.
    """
    def __init__(self, x, y, largeur, hauteur, texte, action=None, couleur=None):
        self.rect = pygame.Rect(x, y, largeur, hauteur)
        self.texte = texte
        self.action = action
        self.est_survole = False
        self.police = pygame.font.Font(None, 40)
        self.couleur = couleur or JAUNE_LOGO  # Couleur du logo par défaut

    def dessiner(self, surface):
        surface_bouton = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        txt_rect = pygame.Rect(0, 0, self.rect.width, self.rect.height)
        halo = pygame.Surface((self.rect.width + 26, self.rect.height + 26), pygame.SRCALPHA)

        if self.est_survole:
            pygame.draw.rect(halo, (*self.couleur, 50), halo.get_rect(), border_radius=36)
            surface.blit(halo, (self.rect.x - 13, self.rect.y - 13))
            pygame.draw.rect(surface_bouton, (*self.couleur, 80), surface_bouton.get_rect(), border_radius=30)
            pygame.draw.rect(surface_bouton, self.couleur, surface_bouton.get_rect(), width=3, border_radius=30)
            txt_surface = self.police.render(self.texte, True, NOIR)
            glow = self.police.render(self.texte, True, self.couleur)
            glow.set_alpha(100)
            txt_surf_rect = txt_surface.get_rect(center=txt_rect.center)
            surface_bouton.blit(glow, (txt_surf_rect.x + 1, txt_surf_rect.y + 3))
            surface_bouton.blit(txt_surface, txt_surf_rect)
        else:
            pygame.draw.rect(surface_bouton, (0, 0, 0, 180), surface_bouton.get_rect(), border_radius=30)
            pygame.draw.rect(surface_bouton, self.couleur, surface_bouton.get_rect(), width=2, border_radius=30)
            txt_surface = self.police.render(self.texte, True, self.couleur)
            txt_surf_rect = txt_surface.get_rect(center=txt_rect.center)
            surface_bouton.blit(txt_surface, txt_surf_rect)

        surface.blit(surface_bouton, self.rect.topleft)

    def verifier_survol(self, position_souris):
        self.est_survole = self.rect.collidepoint(position_souris)

    def est_clique(self, position_souris):
        return self.rect.collidepoint(position_souris)

    def gerer_clic(self, position_souris):
        if self.rect.collidepoint(position_souris) and self.action:
            self.action()

# ── Sous-menu Paramètres ───────────────────────────────────────────────────────

class MenuParametres:
    """
    Gère l'affichage et l'interaction du sous-menu Paramètres.

    Contient :
      - Deux sliders (volume musique, volume effets sonores)
      - Deux boutons < > pour changer la résolution (parmi RESOLUTIONS)
      - Un bouton Retour qui valide et sauvegarde la config

    Les volumes sont appliqués en temps réel pendant le glissement.
    La résolution est appliquée immédiatement (recréation de la fenêtre dans afficher_menu).
    """
    def __init__(self, config):
        self.config = config
        self.resolution_index = config.get("resolution_index", 1)
        self.volume_musique = int(config.get("volume_musique", 0.5) * 100)
        self.volume_sons = int(config.get("volume_sons", 0.7) * 100)
        
        self.slider_musique = Slider(300, 180, 400, 0, 100, self.volume_musique, "Musique")
        self.slider_sons = Slider(300, 280, 400, 0, 100, self.volume_sons, "Effets Sonores")
        
        self.btn_res_prev = Bouton(300, 350, 60, 60, "<", JAUNE_LOGO)
        self.btn_res_next = Bouton(700, 350, 60, 60, ">", JAUNE_LOGO)
        self.btn_retour = Bouton(400, 480, 220, 60, "RETOUR", JAUNE_LOGO)
        
        self.police_titre = pygame.font.Font(None, 70)
        self.police = pygame.font.Font(None, 35)
        self.police_petit = pygame.font.Font(None, 28)

    def mettre_en_page(self, largeur, hauteur):
        largeur_slider = min(520, max(280, largeur - 360))
        x_slider = (largeur - largeur_slider) // 2
        titre_y = max(90, hauteur // 2 - 230)
        self.slider_musique.x = x_slider
        self.slider_musique.y = titre_y + 110
        self.slider_musique.largeur = largeur_slider
        self.slider_sons.x = x_slider
        self.slider_sons.y = self.slider_musique.y + 110
        self.slider_sons.largeur = largeur_slider

        y_resolution = self.slider_sons.y + 120
        self.btn_res_prev.rect.topleft = (largeur // 2 - 210, y_resolution + 30)
        self.btn_res_next.rect.topleft = (largeur // 2 + 150, y_resolution + 30)
        self.btn_retour.rect.size = (220, 60)
        self.btn_retour.rect.center = (largeur // 2, y_resolution + 145)
        return titre_y, y_resolution

    def dessiner_bloc(self, ecran, rect, alpha=120):
        bloc = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(bloc, (10, 15, 28, alpha), bloc.get_rect(), border_radius=24)
        pygame.draw.rect(bloc, (255, 255, 255, 60), bloc.get_rect(), 2, border_radius=24)
        ecran.blit(bloc, rect.topleft)

    def gerer_evenements(self, event):
        ancien_volume_musique = self.slider_musique.valeur
        ancien_volume_sons = self.slider_sons.valeur
        self.slider_musique.gerer_evenement(event)
        self.slider_sons.gerer_evenement(event)

        if (
            self.slider_musique.valeur != ancien_volume_musique
            or self.slider_sons.valeur != ancien_volume_sons
        ):
            config = self.get_config()
            appliquer_volumes(config)
            CONFIG.update(config)
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.btn_res_prev.est_clique(event.pos):
                self.resolution_index = (self.resolution_index - 1) % len(RESOLUTIONS)
                return "resolution_changed"
            elif self.btn_res_next.est_clique(event.pos):
                self.resolution_index = (self.resolution_index + 1) % len(RESOLUTIONS)
                return "resolution_changed"
            elif self.btn_retour.est_clique(event.pos):
                return "retour"
        return None

    def get_config(self):
        cfg = {
            "largeur": RESOLUTIONS[self.resolution_index][0],
            "hauteur": RESOLUTIONS[self.resolution_index][1],
            "volume_musique": self.slider_musique.valeur / 100,
            "volume_sons": self.slider_sons.valeur / 100,
            "resolution_index": self.resolution_index,
        }
        if LAYOUT_CLAVIER in ("azerty", "qwerty"):
            cfg["layout_clavier"] = LAYOUT_CLAVIER
        return cfg

    def dessiner(self, ecran, progression=1.0):
        largeur, hauteur = ecran.get_size()
        titre_y, y_resolution = self.mettre_en_page(largeur, hauteur)
        progression = max(0.0, min(1.0, progression))
        decalage_y = int((1.0 - progression) * 35)
        
        overlay = pygame.Surface((largeur, hauteur), pygame.SRCALPHA)
        overlay.fill((6, 10, 20, int(105 * progression)))
        ecran.blit(overlay, (0, 0))

        titre_rect = pygame.Rect(0, 0, min(520, largeur - 120), 88)
        titre_rect.center = (largeur // 2, titre_y + decalage_y)
        self.dessiner_bloc(ecran, titre_rect, int(135 * progression))

        musique_rect = pygame.Rect(self.slider_musique.x - 35, self.slider_musique.y - 55 + decalage_y, self.slider_musique.largeur + 70, 95)
        sons_rect = pygame.Rect(self.slider_sons.x - 35, self.slider_sons.y - 55 + decalage_y, self.slider_sons.largeur + 70, 95)
        resolution_rect = pygame.Rect(largeur // 2 - 270, y_resolution - 40 + decalage_y, 540, 165)
        self.dessiner_bloc(ecran, musique_rect, int(120 * progression))
        self.dessiner_bloc(ecran, sons_rect, int(120 * progression))
        self.dessiner_bloc(ecran, resolution_rect, int(120 * progression))
        
        titre = self.police_titre.render("PARAMETRES", True, BLANC)
        ecran.blit(titre, titre.get_rect(center=titre_rect.center))

        self.slider_musique.y += decalage_y
        self.slider_sons.y += decalage_y
        self.btn_res_prev.rect.y += decalage_y
        self.btn_res_next.rect.y += decalage_y
        self.btn_retour.rect.y += decalage_y
        
        self.slider_musique.dessiner(ecran, self.police_petit)
        self.slider_sons.dessiner(ecran, self.police_petit)
        
        txt_res = self.police.render("Resolution:", True, BLANC)
        txt_res_rect = txt_res.get_rect(center=(largeur // 2, y_resolution + decalage_y))
        ecran.blit(txt_res, txt_res_rect)
        
        self.btn_res_prev.verifier_survol(pygame.mouse.get_pos())
        self.btn_res_next.verifier_survol(pygame.mouse.get_pos())
        self.btn_retour.verifier_survol(pygame.mouse.get_pos())

        self.btn_res_prev.dessiner(ecran)
        self.btn_res_next.dessiner(ecran)
        
        rw, rh = RESOLUTIONS[self.resolution_index]
        txt_res_val = self.police.render(f"{rw} x {rh}", True, ACCENT)
        txt_res_val_rect = txt_res_val.get_rect(center=(largeur // 2, y_resolution + 60 + decalage_y))
        ecran.blit(txt_res_val, txt_res_val_rect)
        
        self.btn_retour.dessiner(ecran)

def mettre_en_page_boutons(boutons_menu, largeur, hauteur):
    largeur_btn = min(340, max(260, largeur // 3))
    hauteur_btn = 65
    centre_x = (largeur - largeur_btn) // 2
    base_y = max(hauteur // 2 + 40, 420)
    espace = 90
    for index, bouton in enumerate(boutons_menu):
        bouton.rect.update(centre_x, base_y + index * espace, largeur_btn, hauteur_btn)

# ── Écrans de jeu ──────────────────────────────────────────────────────────────

def afficher_selection_clavier(ecran, largeur, hauteur) -> str:
    """
    Écran de sélection du layout clavier : AZERTY ou QWERTY.
    Affiché au premier lancement (si layout_clavier absent de config.json).
    Retourne "azerty" ou "qwerty". Ne peut pas être annulé (ESC = azerty par défaut).
    """
    horloge = pygame.time.Clock()
    sel = 0   # 0 = AZERTY, 1 = QWERTY
    tick = 0

    OPTIONS = [
        {
            "id": "azerty", "label": "AZERTY",
            "couleur": (80, 180, 255),
            "touches": "Z  S  Q  D",
            "desc": "Clavier français / belge",
        },
        {
            "id": "qwerty", "label": "QWERTY",
            "couleur": (120, 230, 130),
            "touches": "W  S  A  D",
            "desc": "Keyboard US / UK / international",
        },
    ]

    card_w, card_h = 300, 280
    espacement = 60
    total_w = 2 * card_w + espacement
    x_start = (largeur - total_w) // 2
    y_cards  = hauteur // 2 - card_h // 2 - 10

    while True:
        horloge.tick(FPS)
        tick += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "azerty"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    if event.key == pygame.K_ESCAPE:
                        return "azerty"
                    return OPTIONS[sel]["id"]
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    sel = 1 - sel
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for idx, opt in enumerate(OPTIONS):
                    cx = x_start + idx * (card_w + espacement)
                    if cx <= mx <= cx + card_w and y_cards <= my <= y_cards + card_h:
                        if idx == sel:
                            return opt["id"]
                        sel = idx

        # ── Rendu ─────────────────────────────────────────────────────────────
        _fond_degrade(ecran, largeur, hauteur)

        f_titre = pygame.font.SysFont(None, 54, bold=True)
        ombre = f_titre.render("LANGUE DU CLAVIER", True, (0, 0, 0))
        titre_s = f_titre.render("LANGUE DU CLAVIER", True, JAUNE_LOGO)
        ecran.blit(ombre,   ombre.get_rect(center=(largeur // 2 + 3, 80)))
        ecran.blit(titre_s, titre_s.get_rect(center=(largeur // 2,   77)))

        f_sub = pygame.font.SysFont(None, 26)
        sub = f_sub.render("Choisissez la disposition de votre clavier", True, (160, 170, 190))
        ecran.blit(sub, sub.get_rect(center=(largeur // 2, 115)))

        for idx, opt in enumerate(OPTIONS):
            cx = x_start + idx * (card_w + espacement)
            est_sel = (idx == sel)
            col = opt["couleur"]
            bob = int(math.sin(tick * 0.07) * 6) if est_sel else 0
            cy  = y_cards - bob

            # Ombre
            sh = pygame.Surface((card_w + 8, card_h + 8), pygame.SRCALPHA)
            pygame.draw.rect(sh, (0, 0, 0, 90), (0, 0, card_w + 8, card_h + 8), border_radius=18)
            ecran.blit(sh, (cx - 4 + 6, cy - 4 + 10))

            # Fond carte
            sc = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            bg = (min(255, col[0]+30), min(255, col[1]+30), min(255, col[2]+30), 220) if est_sel else (20, 25, 40, 160)
            pygame.draw.rect(sc, bg, (0, 0, card_w, card_h), border_radius=16)
            ecran.blit(sc, (cx, cy))
            pygame.draw.rect(ecran, col if est_sel else (60, 70, 90),
                             (cx, cy, card_w, card_h), 3 if est_sel else 1, border_radius=16)

            # Bandeau haut
            bande = pygame.Surface((card_w - 4, 50), pygame.SRCALPHA)
            pygame.draw.rect(bande, (*col, 200), (0, 0, card_w - 4, 50), border_radius=12)
            ecran.blit(bande, (cx + 2, cy + 2))

            f_label = pygame.font.SysFont(None, 36, bold=True)
            ecran.blit(f_label.render(opt["label"], True, (15, 15, 25)),
                       f_label.render(opt["label"], True, (15, 15, 25)).get_rect(center=(cx + card_w // 2, cy + 28)))

            # Touches dessinées comme un mini-clavier
            _dessiner_mini_clavier(ecran, opt["id"], cx + card_w // 2, cy + 120, col if est_sel else (80, 90, 110))

            # Description
            f_desc = pygame.font.SysFont(None, 22)
            ecran.blit(f_desc.render(opt["desc"], True, BLANC if est_sel else (140, 150, 170)),
                       f_desc.render(opt["desc"], True, BLANC if est_sel else (140, 150, 170))
                       .get_rect(center=(cx + card_w // 2, cy + 190)))

            # Touches label
            f_t = pygame.font.SysFont(None, 28, bold=True)
            ecran.blit(f_t.render(opt["touches"], True, col if est_sel else (100, 110, 130)),
                       f_t.render(opt["touches"], True, col if est_sel else (100, 110, 130))
                       .get_rect(center=(cx + card_w // 2, cy + 218)))

            if est_sel:
                f_sel = pygame.font.SysFont(None, 22, bold=True)
                badge = f_sel.render(">> CHOISIR", True, (15, 15, 25))
                b_rect = badge.get_rect(center=(cx + card_w // 2, cy + card_h - 20))
                pygame.draw.rect(ecran, col, b_rect.inflate(16, 8), border_radius=8)
                ecran.blit(badge, b_rect)

        f_aide = pygame.font.SysFont(None, 24)
        aide = f_aide.render("← →  choisir     ENTRÉE / clic  confirmer", True, (120, 130, 150))
        ecran.blit(aide, aide.get_rect(center=(largeur // 2, hauteur - 20)))

        pygame.display.flip()


def _dessiner_mini_clavier(ecran, layout: str, cx: int, cy: int, couleur):
    """Dessine une représentation stylisée des touches ZQSD / WASD."""
    # layout "azerty" → Z au-dessus de QSD / "qwerty" → W au-dessus de ASD
    touches_haut = "Z" if layout == "azerty" else "W"
    touches_bas  = ("Q", "S", "D") if layout == "azerty" else ("A", "S", "D")
    taille = 28
    espace = 4

    def _touche(label, x, y, accent=False):
        rect = pygame.Rect(x - taille // 2, y - taille // 2, taille, taille)
        col_fond = couleur if accent else (40, 50, 65)
        pygame.draw.rect(ecran, col_fond, rect, border_radius=5)
        pygame.draw.rect(ecran, couleur, rect, 2, border_radius=5)
        f = pygame.font.SysFont(None, 22, bold=True)
        t = f.render(label, True, BLANC if accent else couleur)
        ecran.blit(t, t.get_rect(center=rect.center))

    step = taille + espace
    # Rangée du haut : touche unique centrée
    _touche(touches_haut, cx, cy - step, accent=True)
    # Rangée du bas : Q/A  S  D
    _touche(touches_bas[0], cx - step, cy, accent=True)
    _touche(touches_bas[1], cx,        cy)
    _touche(touches_bas[2], cx + step, cy, accent=True)


def afficher_selection_niveaux(ecran, largeur, hauteur, exclure_niveaux=None):
    """
    Affiche l'écran de sélection des niveaux sous forme de cartes animées.

    Retourne la config du niveau choisi (copie du dict + clé '_numero') ou None si annulé.
    exclure_niveaux : ensemble de numéros de niveaux à masquer (ex: {0} pour cacher la démo).

    Navigation :
      - Clavier : ← → pour changer de carte, ENTRÉE/ESPACE pour lancer
      - Souris   : clic sur une carte pour la sélectionner, double-clic pour lancer
      - ESC      : retour
    """
    horloge = pygame.time.Clock()
    niveau_selectionne = 0
    # Filtrage : on exclut les niveaux dans exclure_niveaux (ex: {0} = démo)
    exclure = exclure_niveaux or set()
    niveaux_list = [(num, cfg) for num, cfg in jeu.NIVEAUX.items() if num not in exclure]
    n_total = len(niveaux_list)
    tick = 0

    COULEURS_DIFF = [
        (100, 220, 255),   # 0 – test (bleu clair)
        (80,  240, 130),   # 1 – easy (vert)
        (255, 200,  60),   # 2 – medium (orange)
        (255,  80,  80),   # 3 – hard (rouge)
    ]
    LABELS_DIFF = ["TEST", "EASY", "MEDIUM", "HARD"]
    NB_ETOILES   = [0, 1, 2, 3]   # dessinées en cercles

    card_w, card_h = 200, 260
    espacement = 30
    total_w = n_total * card_w + (n_total - 1) * espacement
    x_start = (largeur - total_w) // 2
    y_cards = hauteur // 2 - card_h // 2 + 20

    while True:
        horloge.tick(FPS)
        tick += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_LEFT, K_MENU_GAUCHE):
                    niveau_selectionne = max(0, niveau_selectionne - 1)
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    niveau_selectionne = min(n_total - 1, niveau_selectionne + 1)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    num, cfg = niveaux_list[niveau_selectionne]
                    return dict(cfg, _numero=num)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for idx in range(n_total):
                    cx = x_start + idx * (card_w + espacement)
                    if cx <= mx <= cx + card_w and y_cards <= my <= y_cards + card_h:
                        if idx == niveau_selectionne:
                            num, cfg = niveaux_list[niveau_selectionne]
                            return dict(cfg, _numero=num)
                        niveau_selectionne = idx

        # ── Fond dégradé
        for y in range(hauteur):
            t = y / hauteur
            r = int(10 + 15 * t)
            g = int(10 + 18 * t)
            b = int(25 + 30 * t)
            pygame.draw.line(ecran, (r, g, b), (0, y), (largeur, y))

        # ── Titre
        f_titre = pygame.font.SysFont(None, 64, bold=True)
        ombre = f_titre.render("CHOISIR UN NIVEAU", True, (0, 0, 0))
        titre  = f_titre.render("CHOISIR UN NIVEAU", True, JAUNE_LOGO)
        ecran.blit(ombre, ombre.get_rect(center=(largeur // 2 + 3, 73)))
        ecran.blit(titre,  titre.get_rect(center=(largeur // 2,     70)))

        # ── Cartes
        for idx, (num, config) in enumerate(niveaux_list):
            cx = x_start + idx * (card_w + espacement)
            est_sel = (idx == niveau_selectionne)
            couleur = COULEURS_DIFF[min(idx, len(COULEURS_DIFF)-1)]
            bob = int(math.sin(tick * 0.07) * 6) if est_sel else 0
            cy = y_cards - bob

            # Ombre portée
            surf_ombre = pygame.Surface((card_w + 8, card_h + 8), pygame.SRCALPHA)
            pygame.draw.rect(surf_ombre, (0, 0, 0, 90), (0, 0, card_w + 8, card_h + 8), border_radius=18)
            ecran.blit(surf_ombre, (cx - 4 + 6, cy - 4 + 10))

            # Fond carte
            fond_alpha = 220 if est_sel else 160
            surf_card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            bg_col = (*[min(255, c + 20) for c in couleur[:3]], fond_alpha) if est_sel else (20, 25, 40, fond_alpha)
            pygame.draw.rect(surf_card, bg_col, (0, 0, card_w, card_h), border_radius=16)
            ecran.blit(surf_card, (cx, cy))

            # Bordure
            epaisseur = 3 if est_sel else 1
            bord_col = couleur if est_sel else (60, 70, 90)
            pygame.draw.rect(ecran, bord_col, (cx, cy, card_w, card_h), epaisseur, border_radius=16)

            # Bandeau couleur en haut
            bande = pygame.Surface((card_w - 4, 44), pygame.SRCALPHA)
            pygame.draw.rect(bande, (*couleur, 200), (0, 0, card_w - 4, 44), border_radius=12)
            ecran.blit(bande, (cx + 2, cy + 2))

            # Difficulté label
            label = LABELS_DIFF[min(idx, len(LABELS_DIFF)-1)]
            f_label = pygame.font.SysFont(None, 28, bold=True)
            txt_label = f_label.render(label, True, (20, 20, 30))
            ecran.blit(txt_label, txt_label.get_rect(center=(cx + card_w // 2, cy + 24)))

            # Numéro
            f_num = pygame.font.SysFont(None, 80, bold=True)
            txt_num = f_num.render(str(num), True, couleur if est_sel else (80, 90, 110))
            ecran.blit(txt_num, txt_num.get_rect(center=(cx + card_w // 2, cy + 100)))

            # Nom
            nom = config.get("nom", "?").split(" - ")[-1] if " - " in config.get("nom","") else config.get("nom","?")
            f_nom = pygame.font.SysFont(None, 26)
            txt_nom = f_nom.render(nom, True, BLANC if est_sel else (140, 150, 170))
            ecran.blit(txt_nom, txt_nom.get_rect(center=(cx + card_w // 2, cy + 155)))

            # Etoiles dessinées (cercles)
            nb_e = NB_ETOILES[min(idx, len(NB_ETOILES)-1)]
            etoile_col = JAUNE_LOGO if est_sel else (100, 110, 130)
            r_e = 7
            espacement_e = 20
            total_e_w = max(1, nb_e) * espacement_e - (espacement_e - 2 * r_e)
            ex0 = cx + card_w // 2 - total_e_w // 2 + r_e
            ey  = cy + 195
            if nb_e == 0:
                pygame.draw.circle(ecran, (60, 70, 90), (cx + card_w // 2, ey), r_e, 2)
            for ei in range(nb_e):
                pygame.draw.circle(ecran, etoile_col, (ex0 + ei * espacement_e, ey), r_e)
                pygame.draw.circle(ecran, (255,255,255,60), (ex0 + ei * espacement_e - 2, ey - 2), 3)

            # Badge ACTIF
            if est_sel:
                f_sel = pygame.font.SysFont(None, 22, bold=True)
                badge = f_sel.render(">> JOUER", True, (20, 20, 30))
                b_rect = badge.get_rect(center=(cx + card_w // 2, cy + card_h - 22))
                pygame.draw.rect(ecran, couleur, b_rect.inflate(16, 8), border_radius=8)
                ecran.blit(badge, b_rect)

        # ── Fleches de navigation (triangles dessinés)
        arr_col = (180, 180, 180)
        arr_y   = hauteur // 2
        if niveau_selectionne > 0:
            ax = x_start - 30
            pygame.draw.polygon(ecran, arr_col, [(ax, arr_y), (ax + 22, arr_y - 14), (ax + 22, arr_y + 14)])
        if niveau_selectionne < n_total - 1:
            ax = x_start + total_w + 12
            pygame.draw.polygon(ecran, arr_col, [(ax + 22, arr_y), (ax, arr_y - 14), (ax, arr_y + 14)])

        # ── Bandeau info solo/coop ─────────────────────────────────────────
        f_info = pygame.font.SysFont(None, 22)
        _k = "Z" if LAYOUT_CLAVIER == "azerty" else "W"
        info1 = f_info.render(f"J1 : {_k} / S  (sauter / glisser)    |    J2 : ↑ / ↓  ou  IA auto-pilot", True, (130, 200, 255))
        info2 = f_info.render("Mode SOLO possible : J2 est géré automatiquement par l'IA si vous ne l'activez pas.", True, (180, 180, 180))
        ecran.blit(info1, info1.get_rect(center=(largeur // 2, hauteur - 60)))
        ecran.blit(info2, info2.get_rect(center=(largeur // 2, hauteur - 40)))

        # ── Instructions navigation ────────────────────────────────────────
        f_aide = pygame.font.SysFont(None, 26)
        aide = f_aide.render("< >  naviguer     ENTREE / clic  lancer     ESC  retour", True, (120, 130, 150))
        ecran.blit(aide, aide.get_rect(center=(largeur // 2, hauteur - 16)))

        pygame.display.flip()

def _fond_degrade(ecran, largeur, hauteur):
    """Fond dégradé sombre partagé par tous les sous-écrans."""
    for y in range(hauteur):
        t = y / hauteur
        pygame.draw.line(ecran, (int(10 + 15 * t), int(10 + 18 * t), int(25 + 30 * t)),
                         (0, y), (largeur, y))


# ── Difficulté & Carte du monde ────────────────────────────────────────────────

_DIFF_OPTIONS = [
    {"id": "test",   "label": "TEST",   "couleur": (100, 220, 255), "desc": "Sans obstacles — démo", "stars": 0},
    {"id": "easy",   "label": "EASY",   "couleur": (80,  240, 130), "desc": "Tranquille, 5 vies",    "stars": 1},
    {"id": "medium", "label": "MEDIUM", "couleur": (255, 200,  60), "desc": "Équilibré, 3 vies",     "stars": 2},
    {"id": "hard",   "label": "HARD",   "couleur": (255,  80,  80), "desc": "Rapide, 1 vie !",       "stars": 3},
]

# Tous les nœuds de la carte (niveaux + bonus/unlock/attention), du bas vers le haut.
# type "level"  → lançable (num = clé NIVEAUX)
# type "bonus"  → navigable mais pas encore jouable (num = None)
_TOUS_NOEUDS_CARTE = [
    {"type": "level", "num": 1,    "nom": "Savanna",  "couleur": (230, 180,  60), "pos_map": (0.30, 0.845)},
    {"type": "bonus", "num": None, "nom": "Unlock !",  "couleur": (210, 150,  40), "pos_map": (0.43, 0.730)},
    {"type": "level", "num": 2,    "nom": "Arctic",   "couleur": (160, 220, 255), "pos_map": (0.37, 0.655)},
    # Bonus de l'Arctic (enclos shiba/fox, à droite du chemin)
    {"type": "bonus", "num": None, "nom": "Bonus ?",   "couleur": (180, 130, 220), "pos_map": (0.56, 0.605)},
    # Unlock entre Arctic et Jungle
    {"type": "bonus", "num": None, "nom": "Unlock !",  "couleur": (210, 150,  40), "pos_map": (0.50, 0.540)},
    {"type": "level", "num": 3,    "nom": "Jungle",   "couleur": (80,  200, 100), "pos_map": (0.32, 0.470)},
    # Bonus entre Jungle et Aquatic (deck en bois, shiba+cat)
    {"type": "bonus", "num": None, "nom": "Bonus ?",   "couleur": (180, 130, 220), "pos_map": (0.53, 0.395)},
    {"type": "level", "num": 4,    "nom": "Aquatic",  "couleur": (60,  150, 230), "pos_map": (0.37, 0.265)},
    # Personnage triangle attention (entre Aquatic et Boss)
    {"type": "bonus", "num": None, "nom": "⚠ Attention","couleur": (255, 210,  40), "pos_map": (0.36, 0.210)},
    {"type": "level", "num": 5,    "nom": "Directeur Magnus", "couleur": (220,  60,  80), "pos_map": (0.36, 0.075), "boss": True},
]

_VIES_PAR_DIFFICULTE = {"easy": 5, "medium": 3, "hard": 1}


def _appliquer_difficulte(config_base: dict, difficulte: str) -> dict:
    """
    Applique la difficulté sur une config de niveau.
    Seul le nombre de vies change ; vitesse, gap et longueur viennent
    uniquement du niveau lui-même et ne sont jamais modifiés.
    """
    cfg = dict(config_base)
    vies = _VIES_PAR_DIFFICULTE.get(difficulte)
    if vies is not None:
        cfg["vies"] = vies
    return cfg


def _dessiner_icone_difficulte(ecran, diff_id, cx, cy, couleur):
    """Icône dessinée pour chaque carte de difficulté."""
    if diff_id == "test":
        # Éprouvette
        pygame.draw.rect(ecran, couleur, (cx - 6, cy - 18, 12, 26), border_radius=4)
        pygame.draw.ellipse(ecran, couleur, (cx - 10, cy + 4, 20, 10))
        pygame.draw.line(ecran, couleur, (cx - 4, cy - 24), (cx + 4, cy - 24), 3)
    elif diff_id == "easy":
        # Visage souriant
        pygame.draw.circle(ecran, couleur, (cx, cy), 17, 2)
        pygame.draw.circle(ecran, couleur, (cx - 5, cy - 4), 3)
        pygame.draw.circle(ecran, couleur, (cx + 5, cy - 4), 3)
        pygame.draw.arc(ecran, couleur, (cx - 9, cy - 2, 18, 14), math.pi, 0, 2)
    elif diff_id == "medium":
        # Bouclier
        pts = [(cx, cy - 18), (cx + 13, cy - 8), (cx + 13, cy + 6),
               (cx, cy + 18), (cx - 13, cy + 6), (cx - 13, cy - 8)]
        pygame.draw.polygon(ecran, couleur, pts, 2)
        pygame.draw.line(ecran, couleur, (cx, cy - 14), (cx, cy + 12), 2)
        pygame.draw.line(ecran, couleur, (cx - 9, cy - 1), (cx + 9, cy - 1), 2)
    else:  # hard — crâne simplifié
        pygame.draw.circle(ecran, couleur, (cx, cy - 4), 14, 2)
        pygame.draw.rect(ecran, couleur, (cx - 10, cy + 6, 20, 8), border_radius=3)
        pygame.draw.line(ecran, couleur, (cx - 4, cy + 8), (cx - 4, cy + 16), 2)
        pygame.draw.line(ecran, couleur, (cx,     cy + 9), (cx,     cy + 16), 2)
        pygame.draw.line(ecran, couleur, (cx + 4, cy + 8), (cx + 4, cy + 16), 2)
        pygame.draw.circle(ecran, couleur, (cx - 5, cy - 5), 3)
        pygame.draw.circle(ecran, couleur, (cx + 5, cy - 5), 3)


def _dessiner_personnage_carte(ecran, x, y, couleur):
    """Petit personnage (fox style) affiché sur la carte du monde."""
    col_clair = tuple(min(255, c + 40) for c in couleur)
    # Corps arrondi
    pygame.draw.ellipse(ecran, couleur, (x - 6, y - 4, 12, 14))
    # Tête avec ombrage
    pygame.draw.circle(ecran, couleur, (x, y - 13), 7)
    pygame.draw.circle(ecran, col_clair, (x - 2, y - 15), 3)
    # Oreilles pointues
    pygame.draw.polygon(ecran, couleur, [(x - 6, y - 19), (x - 3, y - 13), (x - 8, y - 13)])
    pygame.draw.polygon(ecran, couleur, [(x + 6, y - 19), (x + 3, y - 13), (x + 8, y - 13)])
    # Intérieur des oreilles
    pygame.draw.polygon(ecran, col_clair, [(x - 5, y - 18), (x - 3, y - 14), (x - 7, y - 14)])
    pygame.draw.polygon(ecran, col_clair, [(x + 5, y - 18), (x + 3, y - 14), (x + 7, y - 14)])
    # Yeux brillants
    pygame.draw.circle(ecran, (240, 240, 240), (x - 2, y - 13), 2)
    pygame.draw.circle(ecran, (240, 240, 240), (x + 2, y - 13), 2)
    pygame.draw.circle(ecran, (20, 20, 30), (x - 2, y - 13), 1)
    pygame.draw.circle(ecran, (20, 20, 30), (x + 2, y - 13), 1)
    # Museau
    pygame.draw.ellipse(ecran, col_clair, (x - 3, y - 8, 6, 4))
    # Nez
    pygame.draw.polygon(ecran, (20, 20, 30), [(x - 1, y - 7), (x + 1, y - 7), (x, y - 5)])


def afficher_selection_difficulte(ecran, largeur, hauteur):
    """
    Écran de sélection de difficulté : TEST / EASY / MEDIUM / HARD.
    Retourne l'id de difficulté ("test"|"easy"|"medium"|"hard") ou None si annulé.
    """
    horloge = pygame.time.Clock()
    sel = 1  # défaut : easy
    tick = 0

    card_w, card_h = 190, 270
    espacement = 26
    total_w = len(_DIFF_OPTIONS) * card_w + (len(_DIFF_OPTIONS) - 1) * espacement
    x_start = (largeur - total_w) // 2
    y_cards = hauteur // 2 - card_h // 2 + 10

    while True:
        horloge.tick(FPS)
        tick += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_LEFT, K_MENU_GAUCHE):
                    sel = max(0, sel - 1)
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    sel = min(len(_DIFF_OPTIONS) - 1, sel + 1)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return _DIFF_OPTIONS[sel]["id"]
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for idx, opt in enumerate(_DIFF_OPTIONS):
                    cx = x_start + idx * (card_w + espacement)
                    if cx <= mx <= cx + card_w and y_cards <= my <= y_cards + card_h:
                        if idx == sel:
                            return opt["id"]
                        sel = idx

        _fond_degrade(ecran, largeur, hauteur)

        f_titre = pygame.font.SysFont(None, 60, bold=True)
        ombre = f_titre.render("DIFFICULTÉ", True, (0, 0, 0))
        titre_surf = f_titre.render("DIFFICULTÉ", True, JAUNE_LOGO)
        ecran.blit(ombre,      ombre.get_rect(center=(largeur // 2 + 3, 73)))
        ecran.blit(titre_surf, titre_surf.get_rect(center=(largeur // 2,     70)))

        for idx, opt in enumerate(_DIFF_OPTIONS):
            cx = x_start + idx * (card_w + espacement)
            est_sel = (idx == sel)
            couleur = opt["couleur"]
            bob = int(math.sin(tick * 0.07) * 6) if est_sel else 0
            cy = y_cards - bob

            # Ombre
            surf_ombre = pygame.Surface((card_w + 8, card_h + 8), pygame.SRCALPHA)
            pygame.draw.rect(surf_ombre, (0, 0, 0, 90), (0, 0, card_w + 8, card_h + 8), border_radius=18)
            ecran.blit(surf_ombre, (cx - 4 + 6, cy - 4 + 10))

            # Fond
            surf_card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            bg_col = (*[min(255, c + 20) for c in couleur], 220) if est_sel else (20, 25, 40, 160)
            pygame.draw.rect(surf_card, bg_col, (0, 0, card_w, card_h), border_radius=16)
            ecran.blit(surf_card, (cx, cy))

            # Bordure
            pygame.draw.rect(ecran, couleur if est_sel else (60, 70, 90),
                             (cx, cy, card_w, card_h), 3 if est_sel else 1, border_radius=16)

            # Bandeau couleur haut
            bande = pygame.Surface((card_w - 4, 44), pygame.SRCALPHA)
            pygame.draw.rect(bande, (*couleur, 200), (0, 0, card_w - 4, 44), border_radius=12)
            ecran.blit(bande, (cx + 2, cy + 2))

            # Label
            f_label = pygame.font.SysFont(None, 28, bold=True)
            txt = f_label.render(opt["label"], True, (20, 20, 30))
            ecran.blit(txt, txt.get_rect(center=(cx + card_w // 2, cy + 24)))

            # Icône
            _dessiner_icone_difficulte(ecran, opt["id"], cx + card_w // 2, cy + 108, couleur if est_sel else (80, 90, 110))

            # Description
            f_desc = pygame.font.SysFont(None, 22)
            txt_desc = f_desc.render(opt["desc"], True, BLANC if est_sel else (140, 150, 170))
            ecran.blit(txt_desc, txt_desc.get_rect(center=(cx + card_w // 2, cy + 175)))

            # Étoiles
            nb_e = opt["stars"]
            etoile_col = JAUNE_LOGO if est_sel else (100, 110, 130)
            r_e = 7
            ex0 = cx + card_w // 2 - (max(1, nb_e) * 18 - (18 - 2 * r_e)) // 2
            ey = cy + 205
            if nb_e == 0:
                pygame.draw.circle(ecran, (60, 70, 90), (cx + card_w // 2, ey), r_e, 2)
            for ei in range(nb_e):
                pygame.draw.circle(ecran, etoile_col, (ex0 + ei * 18, ey), r_e)

            # Badge sélection
            if est_sel:
                f_sel = pygame.font.SysFont(None, 22, bold=True)
                badge = f_sel.render(">> CHOISIR", True, (20, 20, 30))
                b_rect = badge.get_rect(center=(cx + card_w // 2, cy + card_h - 22))
                pygame.draw.rect(ecran, couleur, b_rect.inflate(16, 8), border_radius=8)
                ecran.blit(badge, b_rect)

        f_aide = pygame.font.SysFont(None, 26)
        aide = f_aide.render("< >  choisir     ENTRÉE / clic  confirmer     ESC  retour", True, (120, 130, 150))
        ecran.blit(aide, aide.get_rect(center=(largeur // 2, hauteur - 20)))

        pygame.display.flip()


def afficher_popup(ecran, largeur, hauteur, message: str, couleur_titre=(255, 215, 0)):
    """
    Affiche une fenêtre popup semi-transparente avec un message centré.
    Attend une touche ou un clic pour fermer.
    """
    horloge = pygame.time.Clock()
    f_titre = pygame.font.SysFont(None, 36, bold=True)
    f_corps = pygame.font.SysFont(None, 26)

    # Découpe le message en lignes pour tenir dans la popup
    mots = message.split()
    lignes = []
    ligne_courante = ""
    max_chars = 52
    for mot in mots:
        test = (ligne_courante + " " + mot).strip()
        if len(test) <= max_chars:
            ligne_courante = test
        else:
            if ligne_courante:
                lignes.append(ligne_courante)
            ligne_courante = mot
    if ligne_courante:
        lignes.append(ligne_courante)

    popup_w = min(largeur - 80, 620)
    popup_h = 60 + len(lignes) * 34 + 50
    popup_x = (largeur - popup_w) // 2
    popup_y = (hauteur - popup_h) // 2

    while True:
        horloge.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return

        # Fond semi-transparent
        overlay = pygame.Surface((largeur, hauteur), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        ecran.blit(overlay, (0, 0))

        # Boîte popup
        pygame.draw.rect(ecran, (18, 22, 40), (popup_x, popup_y, popup_w, popup_h), border_radius=16)
        pygame.draw.rect(ecran, couleur_titre, (popup_x, popup_y, popup_w, popup_h), 2, border_radius=16)

        # Texte
        y_txt = popup_y + 28
        for ligne in lignes:
            surf = f_corps.render(ligne, True, BLANC)
            ecran.blit(surf, surf.get_rect(center=(largeur // 2, y_txt)))
            y_txt += 34

        # Instruction fermeture
        aide = f_corps.render("[ Appuie sur une touche pour continuer ]", True, (130, 140, 160))
        ecran.blit(aide, aide.get_rect(center=(largeur // 2, popup_y + popup_h - 22)))

        pygame.display.flip()


def _perso_j2_auto(j1_index: int) -> int:
    """Retourne un index de personnage différent de J1 pour l'IA."""
    return (j1_index + 1) % len(PERSONNAGES)


def _afficher_j2_ia_info(ecran, largeur, hauteur, j2_index: int):
    """Écran de confirmation : J2 est piloté automatiquement par l'IA."""
    horloge = pygame.time.Clock()
    f_titre = pygame.font.SysFont(None, 48, bold=True)
    f_nom = pygame.font.SysFont(None, 36, bold=True)
    f_aide = pygame.font.SysFont(None, 24)
    perso = PERSONNAGES[j2_index]
    tick = 0

    while True:
        horloge.tick(FPS)
        tick += 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    return

        ecran.fill((10, 12, 28))
        titre = f_titre.render("Joueur 2 — IA automatique", True, (80, 160, 255))
        ecran.blit(titre, titre.get_rect(center=(largeur // 2, 80)))

        desc = f_aide.render("L'IA saute et esquive les obstacles toute seule", True, (140, 150, 170))
        ecran.blit(desc, desc.get_rect(center=(largeur // 2, 130)))

        bob = int(math.sin(tick * 0.12) * 5)
        cx, cy = largeur // 2, hauteur // 2 - bob
        col_body = perso["couleurs"][0]
        _dessiner_personnage_carte(ecran, cx - 12, cy, col_body)

        nom_surf = f_nom.render(perso["nom"], True, col_body)
        ecran.blit(nom_surf, nom_surf.get_rect(center=(largeur // 2, cy + 70)))

        badge = f_nom.render("IA", True, (0, 220, 255))
        badge_rect = badge.get_rect(center=(largeur // 2, cy + 110))
        pygame.draw.rect(ecran, (20, 40, 60), badge_rect.inflate(24, 12), border_radius=8)
        ecran.blit(badge, badge_rect)

        aide = f_aide.render("ENTRÉE  pour continuer", True, (110, 120, 140))
        ecran.blit(aide, aide.get_rect(center=(largeur // 2, hauteur - 40)))
        pygame.display.flip()


def afficher_selection_personnages(ecran, largeur, hauteur, nb_joueurs=2, j2_ia=False):
    """
    Écran de sélection de personnage.
    nb_joueurs=1 → seul J1 choisit (mode solo_j1) ; J2 garde son perso par défaut.
    nb_joueurs=2 → J1 puis J2 choisissent.
    j2_ia=True → J1 choisit, J2 est assigné automatiquement à l'IA (mode solo_ia).
    Retourne un dict avec couleurs, noms et dossiers sprite (personnage_j1/j2).
    Met à jour PERSO_J1_INDEX / PERSO_J2_INDEX globalement.
    """
    global PERSO_J1_INDEX, PERSO_J2_INDEX
    horloge = pygame.time.Clock()

    def _choisir(joueur_num: int, idx_depart: int) -> int:
        """Sous-boucle pour un seul joueur. Retourne l'index choisi ou None si Escape."""
        idx = idx_depart
        f_titre = pygame.font.SysFont(None, 52, bold=True)
        f_nom   = pygame.font.SysFont(None, 36, bold=True)
        f_aide  = pygame.font.SysFont(None, 24)
        tick = 0
        couleur_j = (80, 220, 130) if joueur_num == 1 else (80, 160, 255)
        
        # Calculer les positions des cartes pour la détection de clic
        nb = len(PERSONNAGES)
        card_w, card_h = 130, 160
        espacement = 20
        total_w = nb * card_w + (nb - 1) * espacement
        start_x = (largeur - total_w) // 2

        while True:
            horloge.tick(FPS)
            tick += 1
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return idx
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_LEFT, K_MENU_GAUCHE):
                        idx = (idx - 1) % len(PERSONNAGES)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        idx = (idx + 1) % len(PERSONNAGES)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return idx
                    elif event.key == pygame.K_ESCAPE:
                        return None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    cy_base = hauteur // 2 - card_h // 2
                    for i in range(nb):
                        cx = start_x + i * (card_w + espacement)
                        bob = int(math.sin(tick * 0.12) * 5) if i == idx else 0
                        cy = cy_base - bob
                        if cx <= mx <= cx + card_w and cy <= my <= cy + card_h:
                            if i == idx:
                                return idx
                            idx = i

            # Fond
            ecran.fill((10, 12, 28))

            # Titre
            titre = f_titre.render(f"Joueur {joueur_num} — Choisis ton animal !", True, couleur_j)
            ecran.blit(titre, titre.get_rect(center=(largeur // 2, 80)))

            # Cartes des personnages
            nb = len(PERSONNAGES)
            card_w, card_h = 130, 160
            espacement = 20
            total_w = nb * card_w + (nb - 1) * espacement
            start_x = (largeur - total_w) // 2

            for i, perso in enumerate(PERSONNAGES):
                cx = start_x + i * (card_w + espacement)
                cy = hauteur // 2 - card_h // 2
                est_sel = (i == idx)

                col_body = perso["couleurs"][0]
                col_high = perso["couleurs"][1]

                bob = int(math.sin(tick * 0.12) * 5) if est_sel else 0

                # Halo
                if est_sel:
                    halo = pygame.Surface((card_w + 30, card_h + 30), pygame.SRCALPHA)
                    pygame.draw.rect(halo, (*col_body, 60), (0, 0, card_w + 30, card_h + 30), border_radius=16)
                    ecran.blit(halo, (cx - 15, cy - 15 - bob))

                # Carte
                bg_col = (28, 34, 60) if est_sel else (18, 22, 40)
                border_col = col_body if est_sel else (50, 55, 80)
                pygame.draw.rect(ecran, bg_col, (cx, cy - bob, card_w, card_h), border_radius=12)
                pygame.draw.rect(ecran, border_col, (cx, cy - bob, card_w, card_h), 2, border_radius=12)

                # Mini personnage dessiné
                _dessiner_personnage_carte(ecran, cx + card_w // 2 - 12, cy + 40 - bob, col_body)

                # Pastille couleur
                pygame.draw.circle(ecran, col_high, (cx + card_w // 2, cy + 90 - bob), 8)

                # Nom
                nom_surf = f_nom.render(perso["nom"], True, col_body if est_sel else (180, 190, 210))
                ecran.blit(nom_surf, nom_surf.get_rect(center=(cx + card_w // 2, cy + card_h - 22 - bob)))

            # Aide
            aide = f_aide.render("← →  choisir     CLIC ou ENTRÉE  confirmer", True, (110, 120, 140))
            ecran.blit(aide, aide.get_rect(center=(largeur // 2, hauteur - 40)))

            pygame.display.flip()

    PERSO_J1_INDEX = _choisir(1, PERSO_J1_INDEX)
    if PERSO_J1_INDEX is None:
        return None
    if j2_ia:
        PERSO_J2_INDEX = _perso_j2_auto(PERSO_J1_INDEX)
        _afficher_j2_ia_info(ecran, largeur, hauteur, PERSO_J2_INDEX)
    elif nb_joueurs >= 2:
        PERSO_J2_INDEX = _choisir(2, PERSO_J2_INDEX)
        if PERSO_J2_INDEX is None:
            return None

    return {
        "couleurs_j1":    PERSONNAGES[PERSO_J1_INDEX]["couleurs"],
        "nom_j1":         PERSONNAGES[PERSO_J1_INDEX]["nom"],
        "personnage_j1":  PERSONNAGES[PERSO_J1_INDEX]["dossier"],
        "couleurs_j2":    PERSONNAGES[PERSO_J2_INDEX]["couleurs"],
        "nom_j2":         PERSONNAGES[PERSO_J2_INDEX]["nom"],
        "personnage_j2":  PERSONNAGES[PERSO_J2_INDEX]["dossier"],
    }


def afficher_carte_monde(ecran, largeur, hauteur, difficulte: str, nb_joueurs=2, j2_ia=False):
    """
    Carte du monde style Mario Bros — pleine largeur, défilement vertical.

    La carte est mise à l'échelle pour occuper toute la largeur de l'écran.
    Elle est plus haute que l'écran : la caméra suit automatiquement le nœud
    sélectionné. Navigation : ↑/↓ (ou Z/S) entre les niveaux.
    """
    horloge = pygame.time.Clock()
    tick = 0

    # ── Chargement et mise à l'échelle pleine largeur ────────────────────────
    chemin_carte = os.path.join(os.path.dirname(__file__), "..", "docs", "Map-overall.png")
    try:
        carte_img = pygame.image.load(chemin_carte).convert_alpha()
    except Exception as e:
        print(f"[CARTE] Erreur chargement Map-overall.png : {e}")
        return None

    img_w, img_h = carte_img.get_size()
    scale   = largeur / img_w          # remplit toute la largeur
    map_w   = largeur
    map_h   = int(img_h * scale)       # hauteur totale de la carte (> hauteur écran)
    carte_scaled = pygame.transform.smoothscale(carte_img, (map_w, map_h))

    # ── Positions absolues des nœuds dans la carte (coordonnées carte, pas écran)
    noeuds = [
        {**z, "abs_x": int(z["pos_map"][0] * map_w),
               "abs_y": int(z["pos_map"][1] * map_h)}
        for z in _TOUS_NOEUDS_CARTE
    ]

    sel       = 0      # 0 = premier nœud (Savanna, bas)
    # Caméra : camera_y = pixels du haut de la carte visibles
    # (0 = sommet carte visible ; map_h-hauteur = bas carte visible)
    camera_y  = float(max(0, noeuds[sel]["abs_y"] - hauteur // 2))
    SCROLL_LERP = 0.10   # lissage de la caméra

    # Personnages : positions absolues sur la carte
    char_x = float(noeuds[sel]["abs_x"])
    char_y = float(noeuds[sel]["abs_y"])
    CHAR_SPEED = 9.0

    diff_couleurs = {o["id"]: o["couleur"] for o in _DIFF_OPTIONS}
    diff_col = diff_couleurs.get(difficulte, BLANC)

    # Sélection de personnage courante (initialisée avec les globaux)
    _perso_selection: dict = {
        "couleurs_j1":   PERSONNAGES[PERSO_J1_INDEX]["couleurs"],
        "nom_j1":        PERSONNAGES[PERSO_J1_INDEX]["nom"],
        "personnage_j1": PERSONNAGES[PERSO_J1_INDEX]["dossier"],
        "couleurs_j2":   PERSONNAGES[PERSO_J2_INDEX]["couleurs"],
        "nom_j2":        PERSONNAGES[PERSO_J2_INDEX]["nom"],
        "personnage_j2": PERSONNAGES[PERSO_J2_INDEX]["dossier"],
    }

    # ── Surfaces des barres d'interface (recréées une seule fois) ────────────
    BAR_TOP_H   = 52   # barre titre en haut
    BAR_BOT_H   = 72   # barre infos en bas
    surf_bar = pygame.Surface((largeur, max(BAR_TOP_H, BAR_BOT_H)), pygame.SRCALPHA)

    while True:
        horloge.tick(FPS)
        tick += 1

        # ── Caméra : suit le nœud sélectionné ────────────────────────────────
        cam_target = float(noeuds[sel]["abs_y"]) - hauteur / 2
        cam_target = max(0.0, min(float(map_h - hauteur), cam_target))
        camera_y  += (cam_target - camera_y) * SCROLL_LERP

        # ── Personnages : glissent vers le nœud cible ─────────────────────────
        tx, ty = float(noeuds[sel]["abs_x"]), float(noeuds[sel]["abs_y"])
        dx, dy = tx - char_x, ty - char_y
        dist = math.hypot(dx, dy)
        if dist > CHAR_SPEED:
            char_x += dx / dist * CHAR_SPEED
            char_y += dy / dist * CHAR_SPEED
        else:
            char_x, char_y = tx, ty

        # ── Événements ────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                # ↑ / touche haut J1 → nœud suivant (vers Boss)
                if event.key in (pygame.K_UP, K_J1_HAUT):
                    sel = min(len(noeuds) - 1, sel + 1)
                # ↓ / S → nœud précédent (vers Savanna)
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    sel = max(0, sel - 1)
                # P : sélection de personnage
                if event.key == pygame.K_p:
                    perso_info = afficher_selection_personnages(
                        ecran, largeur, hauteur, nb_joueurs=nb_joueurs, j2_ia=j2_ia,
                    )
                    _perso_selection.update(perso_info)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    n = noeuds[sel]
                    if n["type"] == "level":
                        cfg = _appliquer_difficulte(dict(jeu.NIVEAUX[n["num"]]), difficulte)
                        cfg["_numero"] = n["num"]
                        cfg.update(_perso_selection)
                        return cfg
                    elif "Unlock" in n["nom"]:
                        afficher_popup(ecran, largeur, hauteur,
                                       "Nouveau ami libéré ! Appuie sur P pour choisir ton animal !",
                                       couleur_titre=(210, 150, 40))
                    elif "Attention" in n["nom"]:
                        afficher_popup(ecran, largeur, hauteur,
                                       "Attention ! Le Directeur Magnus vous attend dans son arène. "
                                       "Esquivez ses attaques ensemble — chaque vague sans dégât "
                                       "l'affaiblit. Vainquez-le pour vous échapper du zoo !",
                                       couleur_titre=(255, 80, 80))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for i, n in enumerate(noeuds):
                    sx = n["abs_x"]
                    sy = int(n["abs_y"] - camera_y)
                    if math.hypot(mx - sx, my - sy) < 30:
                        if i == sel and n["type"] == "level":
                            cfg = _appliquer_difficulte(dict(jeu.NIVEAUX[n["num"]]), difficulte)
                            cfg["_numero"] = n["num"]
                            cfg.update(_perso_selection)
                            return cfg
                        sel = i
                        break

            # Molette souris : scroll libre (optionnel)
            if event.type == pygame.MOUSEWHEEL:
                camera_y = max(0.0, min(float(map_h - hauteur), camera_y - event.y * 40))

        # ── Rendu ─────────────────────────────────────────────────────────────
        cam_int = int(camera_y)

        # 1. Carte (décalée par la caméra)
        ecran.blit(carte_scaled, (0, -cam_int))

        # 2. Nœuds (niveaux + bonus)
        f_num  = pygame.font.SysFont(None, 28, bold=True)
        f_nom  = pygame.font.SysFont(None, 24, bold=True)
        for i, n in enumerate(noeuds):
            est_sel  = (i == sel)
            est_bonus = (n["type"] == "bonus")
            px  = n["abs_x"]
            py  = n["abs_y"] - cam_int
            col = n["couleur"]
            # Bonus nodes are smaller diamonds; level nodes are circles
            r   = (22 if est_sel else 17) if not est_bonus else (18 if est_sel else 14)
            bob = int(math.sin(tick * 0.10) * 5) if est_sel else 0

            if not (-r - 20 < py < hauteur + r + 20):
                continue

            # Halo pulsant (nœud sélectionné)
            if est_sel:
                halo_r = r + 10 + int(math.sin(tick * 0.15) * 5)
                halo = pygame.Surface((halo_r * 2 + 4, halo_r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(halo, (*col, 55), (halo_r + 2, halo_r + 2), halo_r)
                ecran.blit(halo, (px - halo_r - 2, py - bob - halo_r - 2))

            if est_bonus:
                # Forme losange pour les nœuds bonus/unlock
                pts = [(px, py - bob - r), (px + r, py - bob),
                       (px, py - bob + r), (px - r, py - bob)]
                pygame.draw.polygon(ecran, (0, 0, 0), [(x+3, y+3) for x, y in pts])  # ombre
                pygame.draw.polygon(ecran, col, pts)
                pygame.draw.polygon(ecran, BLANC, pts, 2)
                # Icône ? ou ! au centre
                f_ic = pygame.font.SysFont(None, 22, bold=True)
                ic = "?" if "?" in n["nom"] else "!"
                ic_surf = f_ic.render(ic, True, (20, 20, 30))
                ecran.blit(ic_surf, ic_surf.get_rect(center=(px, py - bob)))
            else:
                pygame.draw.circle(ecran, (0, 0, 0),  (px + 3, py - bob + 4), r)
                pygame.draw.circle(ecran, col,         (px,     py - bob),     r)
                pygame.draw.circle(ecran, BLANC,       (px,     py - bob),     r, 2)
                if n.get("boss"):
                    f_boss = pygame.font.SysFont(None, 26, bold=True)
                    skull = f_boss.render("☠", True, (255, 230, 230))
                    ecran.blit(skull, skull.get_rect(center=(px, py - bob)))
                else:
                    num_surf = f_num.render(str(n["num"]), True, (15, 15, 25))
                    ecran.blit(num_surf, num_surf.get_rect(center=(px, py - bob)))

            # Nom à droite du nœud
            nom_col  = col if est_sel else (210, 215, 225)
            nom_surf = f_nom.render(n["nom"], True, nom_col)
            nm_rect  = nom_surf.get_rect(midleft=(px + r + 8, py - bob))
            bg_nm    = pygame.Surface((nm_rect.width + 10, nm_rect.height + 4), pygame.SRCALPHA)
            bg_nm.fill((0, 0, 0, 120))
            ecran.blit(bg_nm,    (nm_rect.x - 5, nm_rect.y - 2))
            ecran.blit(nom_surf, nm_rect)

        # 3. Personnages animés
        bob_char = int(math.sin(tick * 0.20) * 3)
        cx_scr = int(char_x)
        cy_scr = int(char_y) - cam_int
        _dessiner_personnage_carte(ecran, cx_scr - 16, cy_scr - bob_char,     _perso_selection["couleurs_j1"][0])
        _dessiner_personnage_carte(ecran, cx_scr + 5,  cy_scr - bob_char + 2, _perso_selection["couleurs_j2"][0])

        # 4. Barre titre (haut)
        bar_top = pygame.Surface((largeur, BAR_TOP_H), pygame.SRCALPHA)
        bar_top.fill((8, 10, 22, 195))
        ecran.blit(bar_top, (0, 0))

        f_titre = pygame.font.SysFont(None, 40, bold=True)
        titre_surf = f_titre.render("CHOISIR UN NIVEAU", True, JAUNE_LOGO)
        ecran.blit(titre_surf, titre_surf.get_rect(midleft=(16, BAR_TOP_H // 2)))

        f_badge = pygame.font.SysFont(None, 26, bold=True)
        badge_txt = f_badge.render(difficulte.upper(), True, (20, 20, 30))
        b_rect = badge_txt.get_rect(midright=(largeur - 16, BAR_TOP_H // 2))
        pygame.draw.rect(ecran, diff_col, b_rect.inflate(20, 10), border_radius=8)
        ecran.blit(badge_txt, b_rect)

        # 5. Barre infos (bas)
        noeud_sel = noeuds[sel]
        bar_bot = pygame.Surface((largeur, BAR_BOT_H), pygame.SRCALPHA)
        bar_bot.fill((8, 10, 22, 195))
        ecran.blit(bar_bot, (0, hauteur - BAR_BOT_H))

        f_zone = pygame.font.SysFont(None, 34, bold=True)
        f_stat = pygame.font.SysFont(None, 22)

        zone_surf = f_zone.render(noeud_sel["nom"], True, noeud_sel["couleur"])
        ecran.blit(zone_surf, zone_surf.get_rect(midleft=(16, hauteur - BAR_BOT_H + 18)))

        if noeud_sel["type"] == "level":
            cfg_preview = _appliquer_difficulte(dict(jeu.NIVEAUX[noeud_sel["num"]]), difficulte)
            stats = [
                f"Lvl {noeud_sel['num']}",
                f"Longueur : {cfg_preview.get('longueur', '?')} m",
                f"Vitesse : {cfg_preview.get('vitesse', '?'):.1f}",
                f"Vies : {cfg_preview.get('vies', '?')}",
            ]
            if cfg_preview.get("mode_boss"):
                stats.append("Mini-boss")
            stat_x = 200
            for s in stats:
                s_surf = f_stat.render(s, True, (190, 200, 220))
                ecran.blit(s_surf, s_surf.get_rect(midleft=(stat_x, hauteur - BAR_BOT_H + 18)))
                stat_x += s_surf.get_width() + 22
        else:
            msg = f_stat.render("Bientôt disponible…", True, (160, 140, 100))
            ecran.blit(msg, msg.get_rect(midleft=(200, hauteur - BAR_BOT_H + 18)))

        haut_key = "Z" if LAYOUT_CLAVIER == "azerty" else "W"
        aide_txt = f"↑/{haut_key}  ↓/S  naviguer   ENTRÉE/clic lancer   P changer perso   ESC retour"
        aide_surf = f_stat.render(aide_txt, True, (110, 120, 140))
        ecran.blit(aide_surf, aide_surf.get_rect(midleft=(16, hauteur - BAR_BOT_H + 48)))

        # Indicateur de scroll (mini-map verticale à droite)
        scroll_track_h = hauteur - BAR_TOP_H - BAR_BOT_H - 20
        scroll_track_y = BAR_TOP_H + 10
        scroll_track_x = largeur - 10
        if map_h > hauteur:
            pygame.draw.line(ecran, (60, 70, 90), (scroll_track_x, scroll_track_y),
                             (scroll_track_x, scroll_track_y + scroll_track_h), 3)
            thumb_y = scroll_track_y + int((camera_y / (map_h - hauteur)) * scroll_track_h)
            pygame.draw.circle(ecran, (180, 190, 210), (scroll_track_x, thumb_y), 5)

        pygame.display.flip()


def afficher_selection_mode(ecran, largeur, hauteur):
    """
    Écran de sélection du mode de jeu : SOLO J1 / SOLO + IA / LOCAL / RÉSEAU.

    Retourne une chaîne parmi : "solo_j1", "solo_ia", "local", "reseau"
    Retourne None si le joueur appuie sur ESC.

    SOLO J1  : J1 seul, pas de J2 (piste du bas vide).
    SOLO + IA: J1 + J2 géré par l'IA.
    LOCAL    : 2 joueurs même clavier (J1=Z/S, J2=↑/↓), IA désactivée.
    RÉSEAU   : 2 PCs connectés via TCP, chacun contrôle son joueur.
    """
    horloge = pygame.time.Clock()
    modes = [
        {
            "id": "solo_j1",
            "titre": "SOLO J1",
            "desc1": "1 joueur seul",
            "desc2": "Piste J2 vide",
            "couleur": (180, 120, 255),  # violet
        },
        {
            "id": "solo_ia",
            "titre": "SOLO + IA",
            "desc1": "1 joueur au clavier",
            "desc2": "J2 piloté par l'IA",
            "couleur": (80, 220, 130),   # vert
        },
        {
            "id": "local",
            "titre": "LOCAL",
            "desc1": "2 joueurs, 1 PC",
            "desc2": None,  # rempli dynamiquement selon le layout clavier
            "couleur": (100, 180, 255),  # bleu
        },
        {
            "id": "reseau",
            "titre": "RÉSEAU",
            "desc1": "2 PCs connectés",
            "desc2": "via Wi-Fi / LAN",
            "couleur": (255, 180, 60),   # orange
        },
    ]
    sel = 0
    tick = 0

    card_w, card_h = 170, 240
    espacement = 22
    total_w = len(modes) * card_w + (len(modes) - 1) * espacement
    x_start = (largeur - total_w) // 2
    y_cards  = hauteur // 2 - card_h // 2

    while True:
        horloge.tick(FPS)
        tick += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_LEFT, K_MENU_GAUCHE):
                    sel = (sel - 1) % len(modes)
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    sel = (sel + 1) % len(modes)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return modes[sel]["id"]
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for idx in range(len(modes)):
                    cx = x_start + idx * (card_w + espacement)
                    if cx <= mx <= cx + card_w and y_cards <= my <= y_cards + card_h:
                        if idx == sel:
                            return modes[sel]["id"]
                        sel = idx

        _fond_degrade(ecran, largeur, hauteur)

        # Titre
        f_titre = pygame.font.SysFont(None, 64, bold=True)
        ombre = f_titre.render("MODE DE JEU", True, (0, 0, 0))
        titre  = f_titre.render("MODE DE JEU", True, JAUNE_LOGO)
        ecran.blit(ombre, ombre.get_rect(center=(largeur // 2 + 3, 73)))
        ecran.blit(titre,  titre.get_rect(center=(largeur // 2,     70)))

        for idx, mode in enumerate(modes):
            cx  = x_start + idx * (card_w + espacement)
            est_sel = (idx == sel)
            col = mode["couleur"]
            bob = int(math.sin(tick * 0.07) * 6) if est_sel else 0
            cy  = y_cards - bob

            # Ombre
            surf_ombre = pygame.Surface((card_w + 8, card_h + 8), pygame.SRCALPHA)
            pygame.draw.rect(surf_ombre, (0, 0, 0, 90), (0, 0, card_w + 8, card_h + 8), border_radius=18)
            ecran.blit(surf_ombre, (cx - 4 + 6, cy - 4 + 10))

            # Fond carte
            surf_card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            bg = (*[min(255, c + 20) for c in col], 220) if est_sel else (20, 25, 40, 160)
            pygame.draw.rect(surf_card, bg, (0, 0, card_w, card_h), border_radius=16)
            ecran.blit(surf_card, (cx, cy))

            # Bordure
            pygame.draw.rect(ecran, col if est_sel else (60, 70, 90),
                             (cx, cy, card_w, card_h), 3 if est_sel else 1, border_radius=16)

            # Bandeau couleur haut
            bande = pygame.Surface((card_w - 4, 44), pygame.SRCALPHA)
            pygame.draw.rect(bande, (*col, 200), (0, 0, card_w - 4, 44), border_radius=12)
            ecran.blit(bande, (cx + 2, cy + 2))

            # Titre mode
            f_label = pygame.font.SysFont(None, 30, bold=True)
            ecran.blit(f_label.render(mode["titre"], True, (20, 20, 30)),
                       f_label.render(mode["titre"], True, (20, 20, 30))
                       .get_rect(center=(cx + card_w // 2, cy + 24)))

            # Icône dessinée
            _dessiner_icone_mode(ecran, mode["id"], cx + card_w // 2, cy + 105, col if est_sel else (80, 90, 110))

            # Description
            f_desc = pygame.font.SysFont(None, 24)
            col_txt = BLANC if est_sel else (140, 150, 170)
            desc2 = mode["desc2"]
            if desc2 is None and mode["id"] == "local":
                k_haut = "W" if LAYOUT_CLAVIER == "qwerty" else "Z"
                desc2 = f"J1: {k_haut}/S   J2: IA ou ↑/↓"
            desc2 = desc2 or ""
            ecran.blit(f_desc.render(mode["desc1"], True, col_txt),
                       f_desc.render(mode["desc1"], True, col_txt)
                       .get_rect(center=(cx + card_w // 2, cy + 158)))
            if desc2:
                ecran.blit(f_desc.render(desc2, True, col_txt),
                           f_desc.render(desc2, True, col_txt)
                           .get_rect(center=(cx + card_w // 2, cy + 180)))

            # Badge JOUER
            if est_sel:
                f_sel = pygame.font.SysFont(None, 22, bold=True)
                badge = f_sel.render(">> CHOISIR", True, (20, 20, 30))
                b_rect = badge.get_rect(center=(cx + card_w // 2, cy + card_h - 22))
                pygame.draw.rect(ecran, col, b_rect.inflate(16, 8), border_radius=8)
                ecran.blit(badge, b_rect)

        # Navigation
        f_aide = pygame.font.SysFont(None, 26)
        aide = f_aide.render("< >  naviguer     ENTREE  confirmer     ESC  retour", True, (120, 130, 150))
        ecran.blit(aide, aide.get_rect(center=(largeur // 2, hauteur - 20)))

        pygame.display.flip()


def _dessiner_icone_mode(ecran, mode_id, cx, cy, couleur):
    """Dessine une icône simple pour chaque mode (formes géométriques pygame)."""
    if mode_id == "solo_j1":
        # Un seul personnage centré + piste basse vide (tirets)
        pygame.draw.circle(ecran, couleur, (cx, cy - 20), 11)
        pygame.draw.rect(ecran, couleur, (cx - 9, cy - 9, 18, 24), border_radius=3)
        # Ligne basse pointillée = piste vide
        for dx in range(-22, 24, 10):
            pygame.draw.line(ecran, couleur, (cx + dx, cy + 20), (cx + dx + 6, cy + 20), 2)
    elif mode_id == "solo_ia":
        # Personnage + petit robot à côté
        pygame.draw.circle(ecran, couleur, (cx - 18, cy - 14), 10)
        pygame.draw.rect(ecran, couleur, (cx - 24, cy - 4, 12, 22), border_radius=3)
        # Robot (J2 IA)
        pygame.draw.rect(ecran, couleur, (cx + 8, cy - 12, 18, 26), border_radius=4)
        pygame.draw.circle(ecran, couleur, (cx + 17, cy - 18), 8)
        # Antenne
        pygame.draw.line(ecran, couleur, (cx + 17, cy - 26), (cx + 17, cy - 32), 2)
        pygame.draw.circle(ecran, couleur, (cx + 17, cy - 33), 3)
        # Yeux robot
        pygame.draw.rect(ecran, (0, 200, 255), (cx + 10, cy - 9, 4, 4))
        pygame.draw.rect(ecran, (0, 200, 255), (cx + 18, cy - 9, 4, 4))
    elif mode_id == "local":
        # Deux personnages côte à côte
        for dx in (-18, 18):
            pygame.draw.circle(ecran, couleur, (cx + dx, cy - 14), 10)
            pygame.draw.rect(ecran, couleur, (cx + dx - 8, cy - 4, 16, 22), border_radius=3)
    else:  # reseau
        # Antenne Wi-Fi stylisée (arcs + point central)
        for r in (24, 16, 8):
            pygame.draw.arc(ecran, couleur,
                            (cx - r, cy - r + 8, r * 2, r * 2), math.pi * 0.2, math.pi * 0.8, 2)
        pygame.draw.circle(ecran, couleur, (cx, cy + 12), 4)


def afficher_ecran_reseau(ecran, largeur, hauteur):
    """
    Écran de configuration réseau.

    Affiche deux boutons : HÉBERGER et REJOINDRE.
      - HÉBERGER : lance le serveur en sous-processus et attend la connexion sur localhost.
      - REJOINDRE : scanne le LAN via UDP beacon et affiche la liste des parties disponibles.

    Retourne (client, player_id, processus_serveur) si la connexion réussit.
    processus_serveur est non-None uniquement si ce PC a lancé le serveur (Héberger).
    Retourne None si annulé.
    """
    import time as _time

    horloge = pygame.time.Clock()
    # "menu" | "hote_attente" | "rejoindre_scan"
    ecran_actif = "menu"
    message_erreur = ""
    erreur_timer = 0
    processus_serveur = None

    # -- Rejoindre : résultats du scan
    jeux_trouves: list = []
    scan_en_cours = False
    scan_thread = None
    dernier_scan = 0.0
    DELAI_RESCAN = 3.0  # relance un scan toutes les 3 s

    sel_choix = 0  # clavier : 0=Héberger, 1=Rejoindre

    btn_hote           = Bouton(largeur // 2 - 220, hauteur // 2 - 40,  200, 60, "HÉBERGER",   (80, 220, 130))
    btn_rejoindre      = Bouton(largeur // 2 + 20,  hauteur // 2 - 40,  200, 60, "REJOINDRE",  (100, 180, 255))
    btn_retour_menu    = Bouton(largeur // 2 - 80,  hauteur // 2 + 200, 160, 50, "RETOUR",     GRIS)
    btn_retour_scan    = Bouton(largeur // 2 - 80,  hauteur - 55,       160, 44, "RETOUR",     GRIS)
    btn_rafraichir     = Bouton(largeur // 2 - 80,  hauteur - 105,      160, 44, "RAFRAÎCHIR", (80, 160, 220))

    def _lancer_scan():
        nonlocal jeux_trouves, scan_en_cours, dernier_scan, scan_thread
        scan_en_cours = True
        dernier_scan = _time.monotonic()
        def _worker():
            nonlocal jeux_trouves, scan_en_cours
            resultats = reseau.scanner_jeux_lan(timeout=2.0)
            jeux_trouves = resultats
            scan_en_cours = False
        scan_thread = __import__('threading').Thread(target=_worker, daemon=True)
        scan_thread.start()

    def _lancer_serveur():
        nonlocal processus_serveur, message_erreur, erreur_timer
        chemin_serveur = os.path.join(
            os.path.dirname(__file__), "..", "server", "zoo_escape_server.py"
        )
        try:
            processus_serveur = subprocess.Popen(
                [sys.executable, chemin_serveur],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
            )
        except Exception as e:
            message_erreur = f"Erreur lancement serveur : {e}"
            erreur_timer = 240
            return False
        return True

    while True:
        horloge.tick(FPS)
        pos = pygame.mouse.get_pos()
        if erreur_timer > 0:
            erreur_timer -= 1

        # Auto-rescan sur l'écran rejoindre
        if ecran_actif == "rejoindre_scan" and not scan_en_cours:
            if _time.monotonic() - dernier_scan >= DELAI_RESCAN:
                _lancer_scan()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if processus_serveur:
                    processus_serveur.terminate()
                return None

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if ecran_actif != "menu":
                        if processus_serveur:
                            processus_serveur.terminate()
                            processus_serveur = None
                        ecran_actif = "menu"
                        jeux_trouves = []
                    else:
                        return None

                elif ecran_actif == "menu":
                    if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        sel_choix = 1 - sel_choix
                    elif event.key == pygame.K_RETURN:
                        if sel_choix == 0:
                            if _lancer_serveur():
                                _time.sleep(0.8)
                                result = _tenter_connexion("127.0.0.1")
                                if result:
                                    return (*result, processus_serveur)
                                message_erreur = "Serveur non démarré — réessaie"
                                erreur_timer = 180
                                processus_serveur.terminate()
                                processus_serveur = None
                            # stay on menu so user sees error
                        else:
                            ecran_actif = "rejoindre_scan"
                            _lancer_scan()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if ecran_actif == "menu":
                    if btn_hote.est_clique(pos):
                        if _lancer_serveur():
                            _time.sleep(0.8)
                            result = _tenter_connexion("127.0.0.1")
                            if result:
                                return (*result, processus_serveur)
                            message_erreur = "Serveur non démarré — réessaie"
                            erreur_timer = 180
                            processus_serveur.terminate()
                            processus_serveur = None
                    elif btn_rejoindre.est_clique(pos):
                        ecran_actif = "rejoindre_scan"
                        _lancer_scan()
                    elif btn_retour_menu.est_clique(pos):
                        return None

                elif ecran_actif == "rejoindre_scan":
                    if btn_rafraichir.est_clique(pos) and not scan_en_cours:
                        _lancer_scan()
                    elif btn_retour_scan.est_clique(pos):
                        ecran_actif = "menu"
                        jeux_trouves = []
                    else:
                        # Vérifier clic sur une entrée de la liste
                        for i, jeu_info in enumerate(jeux_trouves):
                            ligne_rect = pygame.Rect(
                                largeur // 2 - 220, 160 + i * 68, 440, 56
                            )
                            if ligne_rect.collidepoint(pos):
                                result = _tenter_connexion(jeu_info['ip'])
                                if result:
                                    return (*result, None)
                                message_erreur = f"Impossible de rejoindre {jeu_info['nom']}"
                                erreur_timer = 180

        # ── Rendu ─────────────────────────────────────────────────────────────
        _fond_degrade(ecran, largeur, hauteur)

        f_titre = pygame.font.SysFont(None, 56, bold=True)
        ombre = f_titre.render("MODE RÉSEAU", True, (0, 0, 0))
        titre  = f_titre.render("MODE RÉSEAU", True, JAUNE_LOGO)
        ecran.blit(ombre, ombre.get_rect(center=(largeur // 2 + 3, 73)))
        ecran.blit(titre,  titre.get_rect(center=(largeur // 2,     70)))

        if ecran_actif == "menu":
            f_info = pygame.font.SysFont(None, 28)
            ecran.blit(f_info.render("Qui lance la partie ?", True, (180, 180, 200)),
                       f_info.render("Qui lance la partie ?", True, (180, 180, 200))
                       .get_rect(center=(largeur // 2, hauteur // 2 - 85)))

            btn_hote.verifier_survol(pos)
            btn_rejoindre.verifier_survol(pos)
            btn_hote.est_survole      = btn_hote.est_survole      or (sel_choix == 0)
            btn_rejoindre.est_survole = btn_rejoindre.est_survole or (sel_choix == 1)
            btn_hote.dessiner(ecran)
            btn_rejoindre.dessiner(ecran)

            f_sub = pygame.font.SysFont(None, 22)
            ecran.blit(f_sub.render("Lance le serveur sur ce PC", True, (120, 200, 130)),
                       f_sub.render("Lance le serveur sur ce PC", True, (120, 200, 130))
                       .get_rect(center=(largeur // 2 - 120, hauteur // 2 + 35)))
            ecran.blit(f_sub.render("Cherche une partie sur le réseau", True, (120, 160, 255)),
                       f_sub.render("Cherche une partie sur le réseau", True, (120, 160, 255))
                       .get_rect(center=(largeur // 2 + 120, hauteur // 2 + 35)))

            btn_retour_menu.verifier_survol(pos)
            btn_retour_menu.dessiner(ecran)

        elif ecran_actif == "rejoindre_scan":
            f_titre2 = pygame.font.SysFont(None, 34, bold=True)
            ecran.blit(f_titre2.render("Parties disponibles sur le réseau", True, (180, 200, 255)),
                       f_titre2.render("Parties disponibles sur le réseau", True, (180, 200, 255))
                       .get_rect(center=(largeur // 2, 125)))

            f_item = pygame.font.SysFont(None, 30)
            f_sub2 = pygame.font.SysFont(None, 22)

            if scan_en_cours and not jeux_trouves:
                # Spinner animé
                points = "." * ((pygame.time.get_ticks() // 400) % 4)
                txt = f_item.render(f"Scan en cours{points}", True, (160, 160, 180))
                ecran.blit(txt, txt.get_rect(center=(largeur // 2, hauteur // 2)))
            elif not jeux_trouves:
                txt = f_item.render("Aucune partie trouvée", True, (160, 80, 80))
                ecran.blit(txt, txt.get_rect(center=(largeur // 2, hauteur // 2 - 20)))
                hint = f_sub2.render("Assure-toi que l'hôte a lancé une partie sur le même réseau Wi-Fi",
                                     True, (120, 120, 140))
                ecran.blit(hint, hint.get_rect(center=(largeur // 2, hauteur // 2 + 18)))
            else:
                for i, jeu_info in enumerate(jeux_trouves):
                    ligne_rect = pygame.Rect(largeur // 2 - 220, 160 + i * 68, 440, 56)
                    survole = ligne_rect.collidepoint(pos)
                    couleur_fond = (50, 100, 80) if survole else (25, 40, 60)
                    couleur_bord = (80, 220, 130) if survole else (60, 80, 120)
                    pygame.draw.rect(ecran, couleur_fond, ligne_rect, border_radius=10)
                    pygame.draw.rect(ecran, couleur_bord, ligne_rect, 2, border_radius=10)

                    nom_surf = f_item.render(jeu_info['nom'], True, BLANC if survole else (200, 220, 255))
                    ip_surf  = f_sub2.render(jeu_info['ip'], True, (140, 160, 200))
                    ecran.blit(nom_surf, nom_surf.get_rect(midleft=(ligne_rect.x + 16, ligne_rect.centery - 8)))
                    ecran.blit(ip_surf,  ip_surf.get_rect(midleft=(ligne_rect.x + 16, ligne_rect.centery + 14)))

                    join_surf = f_sub2.render("REJOINDRE →", True, (120, 220, 130) if survole else (80, 140, 100))
                    ecran.blit(join_surf, join_surf.get_rect(midright=(ligne_rect.right - 14, ligne_rect.centery)))

                if scan_en_cours:
                    dot = f_sub2.render("↻ actualisation…", True, (100, 140, 200))
                    ecran.blit(dot, dot.get_rect(center=(largeur // 2, 160 + len(jeux_trouves) * 68 + 20)))

            btn_rafraichir.verifier_survol(pos)
            btn_rafraichir.dessiner(ecran)

            btn_retour_scan.verifier_survol(pos)
            btn_retour_scan.dessiner(ecran)

        # Message d'erreur
        if erreur_timer > 0:
            alpha = min(255, erreur_timer * 4)
            f_err = pygame.font.SysFont(None, 28)
            surf_err = f_err.render(message_erreur, True, (255, 100, 100))
            surf_err.set_alpha(alpha)
            ecran.blit(surf_err, surf_err.get_rect(center=(largeur // 2, hauteur - 130)))

        f_aide = pygame.font.SysFont(None, 24)
        ecran.blit(f_aide.render("ESC  retour", True, (120, 130, 150)),
                   f_aide.render("ESC  retour", True, (120, 130, 150))
                   .get_rect(center=(largeur // 2, hauteur - 10)))

        pygame.display.flip()


def _tenter_connexion(ip: str):
    """
    Tente de se connecter au serveur à l'IP donnée.
    Retourne (client, player_id) si succès, None sinon.
    """
    client = reseau.ClientReseau(ip)
    if client.connecter(timeout=4.0):
        return (client, client.player_id)
    return None


def afficher_attente_connexion(ecran, largeur, hauteur, client):
    """
    Écran d'attente affiché après connexion, jusqu'au signal game_start du serveur.

    Pendant l'attente on affiche : player_id, un spinner animé, et le message
    "En attente de l'autre joueur...".
    Retourne True quand la partie peut démarrer, False si annulée (ESC / fermeture).
    """
    horloge = pygame.time.Clock()
    tick = 0

    while True:
        horloge.tick(FPS)
        tick += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client.fermer()
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                client.fermer()
                return False

        if client.game_start_recu:
            return True
        if not client.connecte:
            return False

        _fond_degrade(ecran, largeur, hauteur)

        f_titre = pygame.font.SysFont(None, 52, bold=True)
        ombre = f_titre.render("EN ATTENTE...", True, (0, 0, 0))
        titre  = f_titre.render("EN ATTENTE...", True, JAUNE_LOGO)
        ecran.blit(ombre, ombre.get_rect(center=(largeur // 2 + 2, hauteur // 2 - 90 + 2)))
        ecran.blit(titre,  titre.get_rect(center=(largeur // 2,     hauteur // 2 - 90)))

        # Spinner animé
        angle_base = tick * 6
        cx, cy = largeur // 2, hauteur // 2
        for i in range(8):
            angle = math.radians(angle_base + i * 45)
            alpha = int(255 * (i + 1) / 8)
            r = 4 + i // 3
            x = int(cx + math.cos(angle) * 35)
            y = int(cy + math.sin(angle) * 35)
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 215, 0, alpha), (r, r), r)
            ecran.blit(surf, (x - r, y - r))

        f_info = pygame.font.SysFont(None, 30)
        nom_j = "J1 (piste du haut)" if client.player_id == 0 else "J2 (piste du bas)"
        ecran.blit(f_info.render(f"Tu es le  {nom_j}", True, (180, 200, 255)),
                   f_info.render(f"Tu es le  {nom_j}", True, (180, 200, 255))
                   .get_rect(center=(largeur // 2, hauteur // 2 + 65)))
        ecran.blit(f_info.render("En attente de l'autre joueur...", True, (160, 160, 160)),
                   f_info.render("En attente de l'autre joueur...", True, (160, 160, 160))
                   .get_rect(center=(largeur // 2, hauteur // 2 + 95)))

        f_aide = pygame.font.SysFont(None, 24)
        ecran.blit(f_aide.render("ESC  annuler", True, (120, 130, 150)),
                   f_aide.render("ESC  annuler", True, (120, 130, 150))
                   .get_rect(center=(largeur // 2, hauteur - 20)))

        pygame.display.flip()


def lancer_partie(dossier_courant, menu_params):
    """
    Orchestre le lancement d'une partie :
      1. Sélection du mode (Solo / Local / Réseau)
      2. Setup réseau si nécessaire (connexion + attente game_start)
      3. Sélection de la difficulté (Test → niveau 0 direct, sinon carte du monde)
      4. Lancement du jeu via jeu.lancer_jeu()
      5. Restauration de la fenêtre menu
    """
    global ecran
    config_jeu = menu_params.get_config()
    w, h = config_jeu["largeur"], config_jeu["hauteur"]
    jeu.LARGEUR = w
    jeu.HAUTEUR = h
    jeu.FPS = 144
    appliquer_volumes(config_jeu)

    def _retour():
        """Remet l'écran à la taille du menu avant de quitter."""
        global ecran
        ecran = pygame.display.set_mode((w, h))

    # ── Étape 1 : sélection du mode ──────────────────────────────────────────
    mode = afficher_selection_mode(ecran, w, h)
    if mode is None:
        _retour(); return

    # ── Étape 1b : sélection des personnages ─────────────────────────────────
    j2_ia = (mode == "solo_ia")
    nb_joueurs = 1 if mode in ("solo_j1", "solo_ia") else 2
    perso_info = afficher_selection_personnages(
        ecran, w, h, nb_joueurs=nb_joueurs, j2_ia=j2_ia,
    )
    if perso_info is None:
        _retour(); return

    # ── Étape 2 : setup réseau ───────────────────────────────────────────────
    client = None
    player_id = 0
    seed = None

    processus_serveur = None
    if mode == "reseau":
        result = afficher_ecran_reseau(ecran, w, h)
        if result is None:
            _retour(); return
        client, player_id, processus_serveur = result
        if not afficher_attente_connexion(ecran, w, h, client):
            if client:
                client.fermer()
            if processus_serveur:
                processus_serveur.terminate()
            _retour(); return
        seed = client.seed

    # ── Étape 3 : difficulté puis niveau ─────────────────────────────────────
    difficulte = afficher_selection_difficulte(ecran, w, h)
    if difficulte is None:
        if client: client.fermer()
        _retour(); return

    if difficulte == "test":
        config_niveau = dict(jeu.NIVEAUX[0], _numero=0)
    else:
        config_niveau = afficher_carte_monde(
            ecran, w, h, difficulte, nb_joueurs=nb_joueurs, j2_ia=j2_ia,
        )
        if config_niveau is None:
            if client: client.fermer()
            _retour(); return

    # ── Force les options selon le mode ──────────────────────────────────────
    config_niveau = dict(config_niveau)
    # IA J2 : solo+IA toujours ; en local elle aide tant que personne n'utilise ↑/↓
    config_niveau["ai_j2"]        = mode in ("solo_ia", "local")
    config_niveau["j2_force_ia"]  = j2_ia
    config_niveau["solo_j1"]      = (mode == "solo_j1")
    config_niveau["controles_j1"] = (K_J1_HAUT, pygame.K_s)
    # Personnages : priorité à la sélection faite sur la carte (si elle est là), sinon sélection initiale
    if "couleurs_j1" not in config_niveau:
        config_niveau.update(perso_info)

    # ── Étape 4 : lancement du jeu ───────────────────────────────────────────
    def get_nouveau_niveau():
        diff = afficher_selection_difficulte(ecran, w, h)
        if diff is None:
            return None
        if diff == "test":
            return dict(jeu.NIVEAUX[0], _numero=0)
        return afficher_carte_monde(
            ecran, w, h, diff, nb_joueurs=nb_joueurs, j2_ia=j2_ia,
        )

    try:
        jeu.lancer_jeu(ecran, config_niveau, client_reseau=client,
                       player_id=player_id, seed=seed,
                       get_nouveau_niveau=get_nouveau_niveau)
    finally:
        if client:
            client.fermer()
        if processus_serveur and processus_serveur.poll() is None:
            processus_serveur.terminate()
            try:
                processus_serveur.wait(timeout=2)
            except subprocess.TimeoutExpired:
                processus_serveur.kill()

    # ── Étape 5 : restauration du menu ───────────────────────────────────────
    _retour()
    appliquer_volumes(config_jeu)
    mettre_a_jour_config(config_jeu)

def quitter_jeu():
    pygame.quit()
    sys.exit()

def charger_musique(dossier_courant):
    chemin_musique = os.path.join(dossier_courant, "assets", "milktruck 110bpm.mp3")
    try:
        if os.path.exists(chemin_musique):
            pygame.mixer.music.load(chemin_musique)
            appliquer_volumes(CONFIG)
            pygame.mixer.music.play(-1)
            return True
    except Exception as e:
        print(f"Erreur chargement musique: {e}")
    return False

# ── Point d'entrée du menu ─────────────────────────────────────────────────────

def afficher_menu():
    """
    Boucle principale du menu.

    États possibles :
      mode_parametres = False → affichage du menu principal (logo + 3 boutons)
      mode_parametres = True  → affichage du sous-menu Paramètres (superposé)

    Le fond du menu est une vidéo (background.mp4) lue via OpenCV (cv2).
    Si la vidéo est absente, un fond uni foncé est utilisé à la place.
    Le logo (logo.png) oscille verticalement avec un effet ease-in-out.
    """
    global ecran
    horloge = pygame.time.Clock()
    dossier_courant = os.path.dirname(__file__)
    
    charger_musique(dossier_courant)
    
    chemin_video = os.path.join(dossier_courant, "assets", "background.mp4")
    import cv2  # import tardif : évite le conflit SDL avec pygame sur macOS
    cap = cv2.VideoCapture(chemin_video)
    video_marche = cap.isOpened()
    
    if not video_marche:
        print(f"ATTENTION : Impossible de lire la vidéo au chemin : {chemin_video}")
        print("Vérifie que le fichier s'appelle bien background.mp4")

    image_logo = None
    try:
        chemin_logo = os.path.join(dossier_courant, "assets", "logo.png")
        image_logo = pygame.image.load(chemin_logo).convert_alpha()
    except:
        image_logo = None

    # Sélection du layout clavier au premier lancement uniquement
    layout_sauve = CONFIG.get("layout_clavier")
    if layout_sauve in ("azerty", "qwerty"):
        _appliquer_layout(layout_sauve)
    else:
        layout = afficher_selection_clavier(ecran, LARGEUR, HAUTEUR)
        _appliquer_layout(layout)

    menu_params = MenuParametres(CONFIG)

    boutons_menu = [
        BoutonTransparent(0, 0, 400, 70, "JOUER", None),
        BoutonTransparent(0, 0, 400, 70, "PARAMETRES", None),
        BoutonTransparent(0, 0, 400, 70, "QUITTER", quitter_jeu)
    ]
    
    police_titre = pygame.font.Font(None, 110)
    police_sous_titre = pygame.font.Font(None, 36)

    en_cours = True
    compteur_video = 0
    ralentissement = 2
    derniere_surface_video = None
    mode_parametres = False
    progression_parametres = 0.0
    
    while en_cours:
        largeur_courante, hauteur_courante = ecran.get_size()
        # Recalcule les positions des boutons si la résolution a changé
        mettre_en_page_boutons(boutons_menu, largeur_courante, hauteur_courante)
        position_souris = pygame.mouse.get_pos()
        # Fermeture instantanée des paramètres (pas d'animation de transition)
        progression_parametres = 1.0 if mode_parametres else 0.0

        for evenement in pygame.event.get():
            if evenement.type == pygame.QUIT:
                quitter_jeu()

            # ── Événements selon l'état du menu ──────────────────────────────
            if mode_parametres:
                action = menu_params.gerer_evenements(evenement)
                if action == "retour":
                    mode_parametres = False
                    mettre_a_jour_config(menu_params.get_config())
                elif action == "resolution_changed":
                    config = menu_params.get_config()
                    LARGEUR_NEW = config["largeur"]
                    HAUTEUR_NEW = config["hauteur"]
                    if (LARGEUR_NEW, HAUTEUR_NEW) != (LARGEUR, HAUTEUR):
                        globals()["LARGEUR"] = LARGEUR_NEW
                        globals()["HAUTEUR"] = HAUTEUR_NEW
                        ecran = pygame.display.set_mode((LARGEUR_NEW, HAUTEUR_NEW))
                    appliquer_volumes(config)
                    CONFIG.update(config)
            else:
                if evenement.type == pygame.MOUSEMOTION:
                    for bouton in boutons_menu:
                        bouton.verifier_survol(evenement.pos)
                        
                if evenement.type == pygame.MOUSEBUTTONDOWN and evenement.button == 1:
                    if boutons_menu[0].est_clique(evenement.pos):
                        lancer_partie(dossier_courant, menu_params)
                    elif boutons_menu[1].est_clique(evenement.pos):
                        mode_parametres = True
                    else:
                        boutons_menu[2].gerer_clic(position_souris)

        # ── Rendu du fond vidéo ───────────────────────────────────────────────
        # La vidéo tourne à FPS/ralentissement images par seconde pour éviter
        # qu'elle défile trop vite. On garde la dernière frame si OpenCV n'a
        # pas encore la suivante (évite un écran noir entre deux frames).
        # La boucle vidéo est gérée automatiquement (retour à la frame 0 à la fin).
        if video_marche:
            if compteur_video % ralentissement == 0:
                ret, frame = cap.read()
                if not ret:
                    # Fin de la vidéo → on repart au début (loop)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()

                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = cv2.resize(frame, (largeur_courante, hauteur_courante))
                    derniere_surface_video = pygame.image.frombuffer(frame.tobytes(), frame.shape[1::-1], "RGB")

            if derniere_surface_video:
                ecran.blit(derniere_surface_video, (0, 0))

            compteur_video += 1
        else:
            # Pas de vidéo : fond uni foncé
            ecran.fill((15, 20, 30))

        voile = pygame.Surface((largeur_courante, hauteur_courante), pygame.SRCALPHA)
        voile.fill((0, 0, 0, 110 if not mode_parametres else 70))
        ecran.blit(voile, (0, 0))

        if not mode_parametres:
            temps_ms = pygame.time.get_ticks()
            cycle = (temps_ms % 4000) / 4000.0
            eased = 3 * cycle**2 - 2 * cycle**3
            oscillation_smooth = math.sin(eased * math.pi * 2)
            oscillation = int(oscillation_smooth * 6)

            if image_logo:
                rect_logo = image_logo.get_rect(center=(largeur_courante // 2, max(180, hauteur_courante // 3) + oscillation))
                ecran.blit(image_logo, rect_logo)
            else:
                titre = police_titre.render("ZOO ESCAPE", True, BLANC)
                ombre = police_titre.render("ZOO ESCAPE", True, NOIR)
                rect_titre = titre.get_rect(center=(largeur_courante // 2, max(150, hauteur_courante // 3 - 40) + oscillation))
                ecran.blit(ombre, rect_titre.move(4, 6))
                ecran.blit(titre, rect_titre)

            sous_titre = police_sous_titre.render("L'evasion ultime en cooperation.", True, (220, 220, 220))
            rect_sous_titre = sous_titre.get_rect(center=(largeur_courante // 2, max(240, hauteur_courante // 2 - 30)))
            ecran.blit(sous_titre, rect_sous_titre)

            for bouton in boutons_menu:
                bouton.dessiner(ecran)
        if mode_parametres or progression_parametres > 0.03:
            menu_params.dessiner(ecran, progression_parametres)

        pygame.display.flip()
        horloge.tick(FPS)

if __name__ == "__main__":
    afficher_menu()
