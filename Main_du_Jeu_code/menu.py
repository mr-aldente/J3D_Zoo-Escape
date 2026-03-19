import pygame
import sys
import os
import cv2 
import json
import math
import jeu

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

class Slider:
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

class MenuParametres:
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

def afficher_selection_niveaux(ecran, largeur, hauteur):
    """Écran de sélection des niveaux — design carte"""
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

        # ── Instructions
        f_aide = pygame.font.SysFont(None, 26)
        aide = f_aide.render("< >  naviguer     ENTREE / clic  lancer     ESC  retour", True, (120, 130, 150))
        ecran.blit(aide, aide.get_rect(center=(largeur // 2, hauteur - 34)))

        pygame.display.flip()

def lancer_partie(dossier_courant, menu_params):
    global ecran
    config_jeu = menu_params.get_config()
    jeu.LARGEUR = config_jeu["largeur"]
    jeu.HAUTEUR = config_jeu["hauteur"]
    jeu.FPS = 144
    appliquer_volumes(config_jeu)
    
    # Afficher l'écran de sélection de niveaux
    config_niveau = afficher_selection_niveaux(ecran, config_jeu["largeur"], config_jeu["hauteur"])
    
    if config_niveau is not None:
        jeu.lancer_jeu(ecran, config_niveau)
    
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

def afficher_menu():
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
        mettre_en_page_boutons(boutons_menu, largeur_courante, hauteur_courante)
        position_souris = pygame.mouse.get_pos()
        # Fermeture instantanée des paramètres (pas d'animation)
        progression_parametres = 1.0 if mode_parametres else 0.0
        
        for evenement in pygame.event.get():
            if evenement.type == pygame.QUIT:
                quitter_jeu()
            
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

        if video_marche:
            if compteur_video % ralentissement == 0:
                ret, frame = cap.read()
                if not ret:
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
