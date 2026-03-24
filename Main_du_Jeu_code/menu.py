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
import cv2
import json
import math
import subprocess
import socket as _socket
import jeu
import client_reseau as reseau
cd
pygame.init()
pygame.mixer.init()

LARGEUR = 1024
HAUTEUR = 768
FPS = 60

BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
ACCENT = (56, 189, 248)
VERT = (80, 240, 130)
ORANGE = (255, 140, 0)
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
        "resolution_index": 1
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
        return {
            "largeur": RESOLUTIONS[self.resolution_index][0],
            "hauteur": RESOLUTIONS[self.resolution_index][1],
            "volume_musique": self.slider_musique.valeur / 100,
            "volume_sons": self.slider_sons.valeur / 100,
            "resolution_index": self.resolution_index
        }

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

def afficher_selection_niveaux(ecran, largeur, hauteur):
    """
    Affiche l'écran de sélection des niveaux sous forme de cartes animées.

    Retourne la config du niveau choisi (dict depuis jeu.NIVEAUX) ou None si annulé.

    Navigation :
      - Clavier : ← → pour changer de carte, ENTRÉE/ESPACE pour lancer
      - Souris   : clic sur une carte pour la sélectionner, double-clic pour lancer
      - ESC      : retour au menu principal
    """
    horloge = pygame.time.Clock()
    niveau_selectionne = 0
    niveaux_list = list(jeu.NIVEAUX.items())
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
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    niveau_selectionne = max(0, niveau_selectionne - 1)
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    niveau_selectionne = min(n_total - 1, niveau_selectionne + 1)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return jeu.NIVEAUX[niveau_selectionne]
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for idx in range(n_total):
                    cx = x_start + idx * (card_w + espacement)
                    if cx <= mx <= cx + card_w and y_cards <= my <= y_cards + card_h:
                        if idx == niveau_selectionne:
                            return jeu.NIVEAUX[niveau_selectionne]
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
        info1 = f_info.render("J1 : Z / S  (sauter / glisser)    |    J2 : ↑ / ↓  ou  IA auto-pilot", True, (130, 200, 255))
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


def afficher_selection_mode(ecran, largeur, hauteur):
    """
    Écran de sélection du mode de jeu : SOLO / LOCAL / RÉSEAU.

    Retourne une chaîne parmi : "solo", "local", "reseau"
    Retourne None si le joueur appuie sur ESC.

    SOLO  : J2 est géré par l'IA, un seul joueur au clavier.
    LOCAL : 2 joueurs sur le même clavier (J1=Z/S, J2=↑/↓), IA désactivée.
    RÉSEAU: 2 PCs connectés via TCP, chacun contrôle son joueur.
    """
    horloge = pygame.time.Clock()
    modes = [
        {
            "id": "solo",
            "titre": "SOLO",
            "desc1": "1 joueur au clavier",
            "desc2": "J2 géré par l'IA",
            "couleur": (80, 220, 130),   # vert
        },
        {
            "id": "local",
            "titre": "LOCAL",
            "desc1": "2 joueurs, 1 PC",
            "desc2": "J1: Z/S   J2: ↑/↓",
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

    card_w, card_h = 200, 240
    espacement = 40
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
                if event.key in (pygame.K_LEFT, pygame.K_a):
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
            ecran.blit(f_desc.render(mode["desc1"], True, col_txt),
                       f_desc.render(mode["desc1"], True, col_txt)
                       .get_rect(center=(cx + card_w // 2, cy + 158)))
            ecran.blit(f_desc.render(mode["desc2"], True, col_txt),
                       f_desc.render(mode["desc2"], True, col_txt)
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
    if mode_id == "solo":
        # Personnage + petit robot à côté
        pygame.draw.circle(ecran, couleur, (cx - 18, cy - 14), 10)
        pygame.draw.rect(ecran, couleur, (cx - 24, cy - 4, 12, 22), border_radius=3)
        # Robot (J2 IA)
        pygame.draw.rect(ecran, (*couleur[:3], 160) if len(couleur) == 3 else couleur,
                         (cx + 8, cy - 12, 18, 26), border_radius=4)
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
      - REJOINDRE : affiche un champ de saisie pour entrer l'IP de l'hôte.

    Retourne (client, player_id) si la connexion réussit, ou None si annulé.
      client    : instance de ClientReseau connectée
      player_id : 0 (J1) ou 1 (J2) attribué par le serveur
    """
    horloge = pygame.time.Clock()
    choix = None   # "hote" | "client"
    ip_saisie = ""
    en_saisie_ip = False
    message_erreur = ""
    erreur_timer = 0
    processus_serveur = None

    btn_hote     = Bouton(largeur // 2 - 220, hauteur // 2 - 40, 200, 60, "HÉBERGER",    (80, 220, 130))
    btn_rejoindre = Bouton(largeur // 2 + 20,  hauteur // 2 - 40, 200, 60, "REJOINDRE",   (100, 180, 255))
    btn_retour   = Bouton(largeur // 2 - 80,  hauteur // 2 + 140, 160, 50, "RETOUR",      GRIS)
    btn_connecter = Bouton(largeur // 2 - 80,  hauteur // 2 + 60,  160, 50, "CONNECTER",  (80, 220, 130))

    while True:
        horloge.tick(FPS)
        pos = pygame.mouse.get_pos()
        if erreur_timer > 0:
            erreur_timer -= 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if processus_serveur:
                    processus_serveur.terminate()
                return None

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if en_saisie_ip:
                        en_saisie_ip = False
                        choix = None
                    else:
                        if processus_serveur:
                            processus_serveur.terminate()
                        return None

                elif en_saisie_ip:
                    if event.key == pygame.K_BACKSPACE:
                        ip_saisie = ip_saisie[:-1]
                    elif event.key == pygame.K_RETURN:
                        result = _tenter_connexion(ip_saisie)
                        if result:
                            return result
                        message_erreur = f"Impossible de se connecter à {ip_saisie}"
                        erreur_timer = 180
                    elif event.unicode and len(ip_saisie) < 15:
                        # N'accepte que chiffres et points (adresse IPv4)
                        if event.unicode in "0123456789.":
                            ip_saisie += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not choix:
                    if btn_hote.est_clique(pos):
                        choix = "hote"
                        # Lance le serveur en arrière-plan
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
                            choix = None
                            continue
                        # Connexion automatique à localhost (l'hôte = J1)
                        import time; time.sleep(0.8)  # laisse le serveur démarrer
                        result = _tenter_connexion("127.0.0.1")
                        if result:
                            return result
                        message_erreur = "Serveur non démarré — réessaie"
                        erreur_timer = 180
                        processus_serveur.terminate()
                        choix = None

                    elif btn_rejoindre.est_clique(pos):
                        choix = "client"
                        en_saisie_ip = True

                elif choix == "client" and en_saisie_ip:
                    if btn_connecter.est_clique(pos):
                        result = _tenter_connexion(ip_saisie)
                        if result:
                            return result
                        message_erreur = f"Impossible de se connecter à {ip_saisie}"
                        erreur_timer = 180

                if btn_retour.est_clique(pos):
                    if processus_serveur:
                        processus_serveur.terminate()
                    return None

        # ── Rendu ────────────────────────────────────────────────────────────
        _fond_degrade(ecran, largeur, hauteur)

        f_titre = pygame.font.SysFont(None, 56, bold=True)
        ombre = f_titre.render("MODE RÉSEAU", True, (0, 0, 0))
        titre  = f_titre.render("MODE RÉSEAU", True, JAUNE_LOGO)
        ecran.blit(ombre, ombre.get_rect(center=(largeur // 2 + 3, 73)))
        ecran.blit(titre,  titre.get_rect(center=(largeur // 2,     70)))

        if not choix:
            # Choix Héberger / Rejoindre
            f_info = pygame.font.SysFont(None, 28)
            ecran.blit(f_info.render("Qui lance la partie ?", True, (180, 180, 200)),
                       f_info.render("Qui lance la partie ?", True, (180, 180, 200))
                       .get_rect(center=(largeur // 2, hauteur // 2 - 85)))

            btn_hote.verifier_survol(pos)
            btn_rejoindre.verifier_survol(pos)
            btn_hote.dessiner(ecran)
            btn_rejoindre.dessiner(ecran)

            f_sub = pygame.font.SysFont(None, 22)
            ecran.blit(f_sub.render("Lance le serveur sur ce PC", True, (120, 200, 130)),
                       f_sub.render("Lance le serveur sur ce PC", True, (120, 200, 130))
                       .get_rect(center=(largeur // 2 - 120, hauteur // 2 + 35)))
            ecran.blit(f_sub.render("Entre l'IP de l'hôte", True, (120, 160, 255)),
                       f_sub.render("Entre l'IP de l'hôte", True, (120, 160, 255))
                       .get_rect(center=(largeur // 2 + 120, hauteur // 2 + 35)))

            # Affiche l'IP locale pour aider
            try:
                ip_locale = _socket.gethostbyname(_socket.gethostname())
            except Exception:
                ip_locale = "?"
            ecran.blit(f_info.render(f"Ton IP locale : {ip_locale}", True, (100, 200, 255)),
                       f_info.render(f"Ton IP locale : {ip_locale}", True, (100, 200, 255))
                       .get_rect(center=(largeur // 2, hauteur // 2 + 70)))

        elif choix == "client" and en_saisie_ip:
            # Saisie IP
            f_label = pygame.font.SysFont(None, 32)
            ecran.blit(f_label.render("IP de l'hôte :", True, BLANC),
                       f_label.render("IP de l'hôte :", True, BLANC)
                       .get_rect(center=(largeur // 2, hauteur // 2 - 80)))

            # Champ de saisie
            champ_rect = pygame.Rect(largeur // 2 - 140, hauteur // 2 - 52, 280, 48)
            pygame.draw.rect(ecran, (20, 25, 40), champ_rect, border_radius=8)
            pygame.draw.rect(ecran, (100, 180, 255), champ_rect, 2, border_radius=8)
            f_ip = pygame.font.SysFont(None, 40)
            curseur = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
            ecran.blit(f_ip.render(ip_saisie + curseur, True, BLANC),
                       f_ip.render(ip_saisie + curseur, True, BLANC)
                       .get_rect(center=champ_rect.center))

            ecran.blit(f_label.render("(chiffres et points uniquement)", True, (120, 130, 150)),
                       f_label.render("(chiffres et points uniquement)", True, (120, 130, 150))
                       .get_rect(center=(largeur // 2, hauteur // 2 + 20)))

            btn_connecter.verifier_survol(pos)
            btn_connecter.dessiner(ecran)

        # Message d'erreur
        if erreur_timer > 0:
            alpha = min(255, erreur_timer * 4)
            f_err = pygame.font.SysFont(None, 28)
            surf_err = f_err.render(message_erreur, True, (255, 100, 100))
            surf_err.set_alpha(alpha)
            ecran.blit(surf_err, surf_err.get_rect(center=(largeur // 2, hauteur // 2 + 110)))

        btn_retour.verifier_survol(pos)
        btn_retour.dessiner(ecran)

        f_aide = pygame.font.SysFont(None, 24)
        ecran.blit(f_aide.render("ESC  retour", True, (120, 130, 150)),
                   f_aide.render("ESC  retour", True, (120, 130, 150))
                   .get_rect(center=(largeur // 2, hauteur - 20)))

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
      3. Sélection du niveau
      4. Lancement du jeu via jeu.lancer_jeu() ou boucle réseau
      5. Restauration de la fenêtre menu
    """
    global ecran
    config_jeu = menu_params.get_config()
    jeu.LARGEUR = config_jeu["largeur"]
    jeu.HAUTEUR = config_jeu["hauteur"]
    jeu.FPS = 144
    appliquer_volumes(config_jeu)

    # ── Étape 1 : sélection du mode ──────────────────────────────────────────
    mode = afficher_selection_mode(ecran, config_jeu["largeur"], config_jeu["hauteur"])
    if mode is None:
        ecran = pygame.display.set_mode((config_jeu["largeur"], config_jeu["hauteur"]))
        return

    # ── Étape 2 : préparation selon le mode ──────────────────────────────────
    client = None
    player_id = 0
    seed = None

    if mode == "solo":
        # Force l'IA pour J2 dans tous les niveaux
        pass  # ai_j2 sera forcé lors de la création de JeuDeuxJoueurs

    elif mode == "reseau":
        result = afficher_ecran_reseau(ecran, config_jeu["largeur"], config_jeu["hauteur"])
        if result is None:
            ecran = pygame.display.set_mode((config_jeu["largeur"], config_jeu["hauteur"]))
            return
        client, player_id = result
        # Attente que les deux joueurs soient connectés
        if not afficher_attente_connexion(ecran, config_jeu["largeur"], config_jeu["hauteur"], client):
            ecran = pygame.display.set_mode((config_jeu["largeur"], config_jeu["hauteur"]))
            return
        seed = client.seed  # seed partagé reçu dans game_start

    # ── Étape 3 : sélection du niveau ────────────────────────────────────────
    # En mode réseau, seul le joueur J1 (player_id=0) choisit le niveau ;
    # J2 affiche l'écran mais son choix est ignoré (même seed → même config).
    config_niveau = afficher_selection_niveaux(ecran, config_jeu["largeur"], config_jeu["hauteur"])
    if config_niveau is None:
        if client:
            client.fermer()
        ecran = pygame.display.set_mode((config_jeu["largeur"], config_jeu["hauteur"]))
        return

    # ── Force ai_j2 selon le mode ────────────────────────────────────────────
    config_niveau = dict(config_niveau)          # copie pour ne pas modifier NIVEAUX
    config_niveau["ai_j2"] = (mode == "solo")    # True seulement en solo

    # ── Étape 4 : lancement du jeu ───────────────────────────────────────────
    jeu.lancer_jeu(ecran, config_niveau, client_reseau=client,
                   player_id=player_id, seed=seed)

    if client:
        client.fermer()

    # ── Étape 5 : restauration du menu ───────────────────────────────────────
    ecran = pygame.display.set_mode((config_jeu["largeur"], config_jeu["hauteur"]))
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
