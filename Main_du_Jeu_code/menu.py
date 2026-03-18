import json
import sys
from pathlib import Path

import pygame

import jeu

pygame.init()
pygame.mixer.init()

ASSETS_DIR = Path(__file__).parent / "assets"
CONFIG_FILE = Path(__file__).parent / "config.json"


def charger_config():
    valeurs_defaut = {
        "largeur": 1024,
        "hauteur": 768,
        "fps": 60,
        "volume_musique": 0.5,
        "volume_sons": 0.7,
        "vsync": False,
    }
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            valeurs_defaut.update(data)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return valeurs_defaut


def sauvegarder_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur sauvegarde config: {e}")


CONFIG = charger_config()
LARGEUR = int(CONFIG["largeur"])
HAUTEUR = int(CONFIG["hauteur"])
FPS = 144
VOLUME_MUSIQUE = float(CONFIG["volume_musique"])
VOLUME_SONS = float(CONFIG["volume_sons"])
VSYNC = bool(CONFIG["vsync"])

BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
VIOLET = (138, 43, 226)
ORANGE = (255, 140, 0)
JAUNE = (255, 215, 0)
BLEU_CLAIR = (135, 206, 235)
ROSE_ARCADE = (255, 20, 147)
CYAN_ARCADE = (0, 255, 255)
LIME = (50, 205, 50)
GRIS_CLAIR = (205, 205, 205)

RESOLUTIONS = [(800, 600), (1024, 768), (1280, 720), (1366, 768), (1600, 900)]


class Bouton:
    def __init__(self, x, y, largeur, hauteur, texte, couleur_fond):
        self.rect = pygame.Rect(x, y, largeur, hauteur)
        self.texte = texte
        self.couleur_fond = couleur_fond
        self.survole = False
        self.scale = 1.0

    def dessiner(self, ecran, police):
        if self.survole:
            self.scale = min(self.scale + 0.05, 1.12)
        else:
            self.scale = max(self.scale - 0.05, 1.0)

        rect_dessine = self.rect.copy()
        if self.scale > 1.0:
            inflation = int((self.scale - 1.0) * 45)
            rect_dessine.inflate_ip(inflation, inflation)

        pygame.draw.rect(ecran, NOIR, rect_dessine, border_radius=14, width=6)
        rect_interieur = rect_dessine.inflate(-14, -14)
        pygame.draw.rect(ecran, self.couleur_fond, rect_interieur, border_radius=10)

        highlight = rect_interieur.copy()
        highlight.height = highlight.height // 3
        highlight_color = tuple(min(c + 65, 255) for c in self.couleur_fond)
        pygame.draw.rect(ecran, highlight_color, highlight, border_radius=8)

        texte_ombre = police.render(self.texte, True, NOIR)
        texte_surface = police.render(self.texte, True, BLANC)
        ombre_rect = texte_ombre.get_rect(center=(rect_dessine.centerx + 3, rect_dessine.centery + 3))
        texte_rect = texte_surface.get_rect(center=rect_dessine.center)
        ecran.blit(texte_ombre, ombre_rect)
        ecran.blit(texte_surface, texte_rect)

    def verifier_survol(self, pos):
        self.survole = self.rect.collidepoint(pos)

    def est_clique(self, pos):
        return self.rect.collidepoint(pos)


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
        return (self.valeur - self.min_val) / (self.max_val - self.min_val)

    def _knob_x(self):
        return self.x + int(self.largeur * self._ratio())

    def dessiner(self, ecran, police):
        pygame.draw.rect(ecran, GRIS_CLAIR, (self.x, self.y, self.largeur, self.hauteur), border_radius=6)
        pygame.draw.rect(ecran, CYAN_ARCADE, (self.x, self.y, max(1, self._knob_x() - self.x), self.hauteur), border_radius=6)
        pygame.draw.circle(ecran, BLANC, (self._knob_x(), self.y + self.hauteur // 2), 11)
        pygame.draw.circle(ecran, NOIR, (self._knob_x(), self.y + self.hauteur // 2), 11, 2)

        txt = police.render(f"{self.label}: {self.valeur}", True, BLANC)
        ecran.blit(txt, (self.x, self.y - 34))

    def gerer_evenement(self, event):
        valeur_avant = self.valeur
        knob_rect = pygame.Rect(self._knob_x() - 13, self.y - 8, 26, 24)
        bar_rect = pygame.Rect(self.x, self.y - 8, self.largeur, 24)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if knob_rect.collidepoint(event.pos) or bar_rect.collidepoint(event.pos):
                self.drag = True
                self._set_from_mouse(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP:
            self.drag = False
        elif event.type == pygame.MOUSEMOTION and self.drag:
            self._set_from_mouse(event.pos[0])

        return self.valeur != valeur_avant

    def _set_from_mouse(self, mouse_x):
        ratio = (mouse_x - self.x) / self.largeur
        ratio = max(0.0, min(1.0, ratio))
        self.valeur = int(round(self.min_val + ratio * (self.max_val - self.min_val)))


class Toggle:
    def __init__(self, x, y, label, actif=False):
        self.rect = pygame.Rect(x, y, 120, 42)
        self.label = label
        self.actif = actif

    def dessiner(self, ecran, police):
        fond = LIME if self.actif else ORANGE
        pygame.draw.rect(ecran, fond, self.rect, border_radius=21)
        pygame.draw.rect(ecran, NOIR, self.rect, width=2, border_radius=21)

        knob_x = self.rect.x + (self.rect.width - 24 if self.actif else 0)
        pygame.draw.circle(ecran, BLANC, (knob_x + 12, self.rect.centery), 11)
        pygame.draw.circle(ecran, NOIR, (knob_x + 12, self.rect.centery), 11, 2)

        txt = police.render(f"{self.label}: {'ON' if self.actif else 'OFF'}", True, BLANC)
        ecran.blit(txt, (self.rect.x - 220, self.rect.y + 5))

    def gerer_evenement(self, event):
        valeur_avant = self.actif
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.actif = not self.actif
        return self.actif != valeur_avant


class MenuOptions:
    def __init__(self, config):
        self.config = config
        self.resolution_index = self._trouver_resolution_index(config["largeur"], config["hauteur"])

        self.police_titre = pygame.font.Font(None, 90)
        self.police = pygame.font.Font(None, 38)
        self.police_bouton = pygame.font.Font(None, 50)

        self.slider_volume_music = Slider(250, 290, 520, 0, 100, int(config["volume_musique"] * 100), "Musique")
        self.slider_volume_sfx = Slider(250, 390, 520, 0, 100, int(config["volume_sons"] * 100), "Effets")
        self.toggle_vsync = Toggle(650, 470, "VSync", bool(config["vsync"]))

        self.btn_res_prev = Bouton(250, 150, 70, 52, "<", JAUNE)
        self.btn_res_next = Bouton(700, 150, 70, 52, ">", JAUNE)
        self.btn_back = Bouton(420, 620, 180, 70, "RETOUR", ROSE_ARCADE)

    def _trouver_resolution_index(self, w, h):
        for i, (rw, rh) in enumerate(RESOLUTIONS):
            if rw == w and rh == h:
                return i
        return 1

    def get_config(self):
        w, h = RESOLUTIONS[self.resolution_index]
        return {
            "largeur": w,
            "hauteur": h,
            "fps": 144,
            "volume_musique": self.slider_volume_music.valeur / 100,
            "volume_sons": self.slider_volume_sfx.valeur / 100,
            "vsync": self.toggle_vsync.actif,
        }

    def gerer_evenements(self, event):
        changement = False
        changement = self.slider_volume_music.gerer_evenement(event) or changement
        changement = self.slider_volume_sfx.gerer_evenement(event) or changement
        changement = self.toggle_vsync.gerer_evenement(event) or changement

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.btn_res_prev.est_clique(event.pos):
                self.resolution_index = (self.resolution_index - 1) % len(RESOLUTIONS)
                return "resolution_changed"
            elif self.btn_res_next.est_clique(event.pos):
                self.resolution_index = (self.resolution_index + 1) % len(RESOLUTIONS)
                return "resolution_changed"
            elif self.btn_back.est_clique(event.pos):
                return "retour"

        if changement:
            return "changed"

        return None

    def dessiner(self, ecran):
        w, h = ecran.get_size()
        overlay = pygame.Surface((w, h))
        overlay.set_alpha(220)
        overlay.fill((15, 15, 25))
        ecran.blit(overlay, (0, 0))

        titre = self.police_titre.render("OPTIONS", True, BLANC)
        ecran.blit(titre, titre.get_rect(center=(w // 2, 70)))

        txt_res = self.police.render("Résolution", True, BLANC)
        ecran.blit(txt_res, (250, 110))
        self.btn_res_prev.dessiner(ecran, self.police_bouton)
        self.btn_res_next.dessiner(ecran, self.police_bouton)

        rw, rh = RESOLUTIONS[self.resolution_index]
        txt_res_val = self.police.render(f"{rw} x {rh}", True, CYAN_ARCADE)
        ecran.blit(txt_res_val, (430, 160))

        self.slider_volume_music.dessiner(ecran, self.police)
        self.slider_volume_sfx.dessiner(ecran, self.police)
        self.toggle_vsync.dessiner(ecran, self.police)

        self.btn_back.dessiner(ecran, self.police_bouton)

        txt_auto = self.police.render("Sauvegarde automatique active", True, CYAN_ARCADE)
        ecran.blit(txt_auto, (250, 575))


class MenuPrincipal:
    def __init__(self):
        self.config = {
            "largeur": LARGEUR,
            "hauteur": HAUTEUR,
            "fps": FPS,
            "volume_musique": VOLUME_MUSIQUE,
            "volume_sons": VOLUME_SONS,
            "vsync": VSYNC,
        }

        self.ecran = pygame.display.set_mode((self.config["largeur"], self.config["hauteur"]))
        pygame.display.set_caption("Zoo Escape")
        self.horloge = pygame.time.Clock()

        self.image_fond = self._charger_image_fond()
        self._charger_musique()

        self.police_titre = pygame.font.Font(None, 120)
        self.police_bouton = pygame.font.Font(None, 55)
        self.police_credits = pygame.font.Font(None, 35)

        self.mode_options = False
        self.menu_options = MenuOptions(self.config)

        self._creer_boutons_principaux()

    def _creer_boutons_principaux(self):
        largeur, hauteur = self.ecran.get_size()
        largeur_bouton = 280
        hauteur_bouton = 80
        y_centre = hauteur - 150
        espacement = 30
        largeur_totale = largeur_bouton * 3 + espacement * 2
        x_debut = (largeur - largeur_totale) // 2

        self.bouton_jouer = Bouton(x_debut, y_centre, largeur_bouton, hauteur_bouton, "JOUER", LIME)
        self.bouton_options = Bouton(x_debut + largeur_bouton + espacement, y_centre, largeur_bouton, hauteur_bouton, "OPTIONS", JAUNE)
        self.bouton_quitter = Bouton(x_debut + (largeur_bouton + espacement) * 2, y_centre, largeur_bouton, hauteur_bouton, "QUITTER", ORANGE)
        self.boutons = [self.bouton_jouer, self.bouton_options, self.bouton_quitter]

    def _charger_image_fond(self):
        nom_fichier = ASSETS_DIR / "zoo_escape_bg.png"
        try:
            image = pygame.image.load(str(nom_fichier))
            return pygame.transform.scale(image, self.ecran.get_size())
        except Exception:
            fond = pygame.Surface(self.ecran.get_size())
            largeur, hauteur = self.ecran.get_size()
            for y in range(hauteur):
                ratio = y / max(1, hauteur)
                r = int(20 + 40 * ratio)
                g = int(20 + 100 * ratio)
                b = int(50 + 120 * ratio)
                pygame.draw.line(fond, (r, g, b), (0, y), (largeur, y))
            return fond

    def _charger_musique(self):
        nom_fichier = ASSETS_DIR / "milktruck 110bpm.mp3"
        try:
            pygame.mixer.music.load(str(nom_fichier))
            pygame.mixer.music.set_volume(self.config["volume_musique"])
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    def _appliquer_config(self, new_config, reinitialiser_affichage=True):
        global LARGEUR, HAUTEUR, FPS, VOLUME_MUSIQUE, VOLUME_SONS, VSYNC

        self.config.update(new_config)
        LARGEUR = int(self.config["largeur"])
        HAUTEUR = int(self.config["hauteur"])
        FPS = int(self.config["fps"])
        VOLUME_MUSIQUE = float(self.config["volume_musique"])
        VOLUME_SONS = float(self.config["volume_sons"])
        VSYNC = bool(self.config["vsync"])

        if reinitialiser_affichage:
            self.ecran = pygame.display.set_mode((LARGEUR, HAUTEUR))
            self.image_fond = self._charger_image_fond()
            self._creer_boutons_principaux()
        pygame.mixer.music.set_volume(VOLUME_MUSIQUE)
        sauvegarder_config(self.config)

    def _dessiner_titre(self):
        largeur, _ = self.ecran.get_size()
        titre_ombre = self.police_titre.render("ZOO ESCAPE", True, NOIR)
        self.ecran.blit(titre_ombre, titre_ombre.get_rect(center=(largeur // 2 + 6, 106)))

        titre_bordure = self.police_titre.render("ZOO ESCAPE", True, VIOLET)
        self.ecran.blit(titre_bordure, titre_bordure.get_rect(center=(largeur // 2 + 3, 103)))

        titre_orange = self.police_titre.render("ZOO ESCAPE", True, ORANGE)
        self.ecran.blit(titre_orange, titre_orange.get_rect(center=(largeur // 2, 100)))

        titre_jaune = self.police_titre.render("ZOO ESCAPE", True, JAUNE)
        titre_jaune.set_alpha(150)
        self.ecran.blit(titre_jaune, titre_jaune.get_rect(center=(largeur // 2 - 2, 98)))

    def executer(self):
        en_cours = True
        while en_cours:
            self.horloge.tick(max(30, self.config["fps"]))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    en_cours = False
                    continue

                if self.mode_options:
                    action = self.menu_options.gerer_evenements(event)
                    if action == "changed":
                        self._appliquer_config(self.menu_options.get_config(), reinitialiser_affichage=False)
                    elif action == "resolution_changed":
                        self._appliquer_config(self.menu_options.get_config(), reinitialiser_affichage=True)
                    elif action == "retour":
                        self.mode_options = False
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.bouton_jouer.est_clique(event.pos):
                        jeu.LARGEUR = self.config["largeur"]
                        jeu.HAUTEUR = self.config["hauteur"]
                        jeu.FPS = 144
                        jeu.lancer_jeu(self.ecran)
                    elif self.bouton_options.est_clique(event.pos):
                        self.mode_options = True
                    elif self.bouton_quitter.est_clique(event.pos):
                        en_cours = False

            pos = pygame.mouse.get_pos()
            for b in self.boutons:
                b.verifier_survol(pos)
            self.menu_options.btn_back.verifier_survol(pos)
            self.menu_options.btn_res_prev.verifier_survol(pos)
            self.menu_options.btn_res_next.verifier_survol(pos)

            self.ecran.blit(self.image_fond, (0, 0))

            largeur, hauteur = self.ecran.get_size()
            overlay = pygame.Surface((largeur, hauteur))
            overlay.set_alpha(70)
            overlay.fill(NOIR)
            self.ecran.blit(overlay, (0, 0))

            self._dessiner_titre()

            for bouton in self.boutons:
                bouton.dessiner(self.ecran, self.police_bouton)

            credits = self.police_credits.render("Protocol Coop - 2026", True, BLANC)
            credits_ombre = self.police_credits.render("Protocol Coop - 2026", True, NOIR)
            self.ecran.blit(credits_ombre, (largeur // 2 - 138, hauteur - 28))
            self.ecran.blit(credits, (largeur // 2 - 140, hauteur - 30))

            if self.mode_options:
                self.menu_options.dessiner(self.ecran)

            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    menu = MenuPrincipal()
    menu.executer()