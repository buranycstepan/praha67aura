import pygame
import random
import math
import sys
import glob  # Zabudovaná knihovna pro automatické vyhledávání souborů ve složce
import json  # PŘIDÁNO: pro ukládání/načítání naučených AI mozků na disk


# ==========================================
# 1. KONFIGURACE A KONSTANTY
# ==========================================
SCREEN_WIDTH = 1920   
SCREEN_HEIGHT = 1080  
FPS = 60

UI_WIDTH = 280   
CHUNK_SIZE_W = SCREEN_WIDTH - UI_WIDTH  
CHUNK_SIZE_H = SCREEN_HEIGHT

GAME_CENTER_X = CHUNK_SIZE_W // 2
GAME_CENTER_Y = CHUNK_SIZE_H // 2

COLOR_BG = (225, 220, 210)       
COLOR_TEXT = (20, 30, 40)
COLOR_DANGER = (255, 30, 90)
COLOR_ACCENT = (0, 150, 255)
COLOR_GOLD = (218, 165, 32)
COLOR_RIVER = (140, 175, 210)    
COLOR_PARK = (120, 165, 110) 

GRID_X = [150, 500, 850, 1200, 1550]
GRID_Y = [150, 450, 750, 1050]
ROAD_THICKNESS = 65

pygame.init() 

pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

# --- DYNAMICKÝ SYSTÉM PRO NAČÍTÁNÍ NAKONEC AŽ 29 TEXTUR ---
AI_CAR_TEXTURES = []

# Vyhledá ve složce projektu všechny soubory odpovídající masce auto_ai*.png
ai_texture_paths = glob.glob("auto_ai*.png")

for path in ai_texture_paths:
    try:
        img_src = pygame.image.load(path).convert_alpha()
        # Tvůj původní pixel-art je svislý (20px šířka, 36px délka)
        img_src = pygame.transform.scale(img_src, (20, 36))
        # Otočení o 270 stupňů doprava, aby předek s červenými světly správně jel dopředu
        img_ready = pygame.transform.rotate(img_src, 270)
        AI_CAR_TEXTURES.append(img_ready)
    except Exception as e:
        print(f"Chyba při načítání textury {path}: {e}")

# Pokud ve složce nemáš zatím žádné auto_ai textury, načte se alespoň ta základní bez čísla
if not AI_CAR_TEXTURES:
    try:
        img_src = pygame.image.load("auto_ai.png").convert_alpha()
        img_src = pygame.transform.scale(img_src, (20, 36))
        img_ready = pygame.transform.rotate(img_src, 270)
        AI_CAR_TEXTURES.append(img_ready)
    except Exception:
        pass

# Načtení textury silnice
try:
    TEXTURE_ROAD_SRC = pygame.image.load("silnice.png").convert_alpha()
    TEXTURE_ROAD = pygame.transform.scale(TEXTURE_ROAD_SRC, (ROAD_THICKNESS, ROAD_THICKNESS))
    HAS_ROAD_TEX = True
except Exception:
    HAS_ROAD_TEX = False

# ==========================================
# PŘIDÁNO: OBRÁZEK NA POZADÍ HLAVNÍHO MENU
# Hledá se ve složce projektu soubor menu_pozadi.* (png/jpg) - pokud tam žádný takový
# soubor není, hlavní menu se vykreslí postaru (jen tmavá barva na pozadí), takže hra
# pojede dál v pořádku i bez obrázku.
# ==========================================
MENU_BG_CANDIDATES = glob.glob("menu_pozadi.*") + glob.glob("menu_bg.*")
MENU_BG_IMAGE = None
if MENU_BG_CANDIDATES:
    try:
        bg_src = pygame.image.load(MENU_BG_CANDIDATES[0]).convert()
        # Obrázek se přeškáluje tak, aby vyplnil celou obrazovku ("cover" - poměr stran
        # se zachová, přesah se odřízne), aby nebyl nikde deformovaný ani s prázdnými pruhy.
        src_w, src_h = bg_src.get_size()
        scale = max(SCREEN_WIDTH / src_w, SCREEN_HEIGHT / src_h)
        new_w, new_h = int(src_w * scale), int(src_h * scale)
        bg_scaled = pygame.transform.smoothscale(bg_src, (new_w, new_h))
        crop_x = (new_w - SCREEN_WIDTH) // 2
        crop_y = (new_h - SCREEN_HEIGHT) // 2
        MENU_BG_IMAGE = bg_scaled.subsurface(pygame.Rect(crop_x, crop_y, SCREEN_WIDTH, SCREEN_HEIGHT)).copy()
    except Exception as e:
        print(f"Nepodařilo se načíst obrázek pozadí menu: {e}")

# ==========================================
# PŘIDÁNO: HUDBA HRAJÍCÍ V MENU (hlavní menu, garáž, obchod)
# Hledá se ve složce projektu soubor menu_hudba.* nebo menu_music.* (mp3/ogg/wav) -
# pokud tam žádný takový soubor není, hra jede dál úplně normálně bez hudby.
# ==========================================
MENU_MUSIC_CANDIDATES = glob.glob("menu_hudba.*") + glob.glob("menu_music.*")
HAS_MENU_MUSIC = False
if MENU_MUSIC_CANDIDATES:
    try:
        pygame.mixer.music.load(MENU_MUSIC_CANDIDATES[0])
        pygame.mixer.music.set_volume(0.5)
        HAS_MENU_MUSIC = True
    except Exception as e:
        print(f"Nepodařilo se načíst hudbu do menu: {e}")

AI_CAR_BRANDS = [
    {"name": "Škoda Enyaq-X", "color": (0, 180, 220)},
    {"name": "Praga Neo", "color": (220, 80, 0)},
    {"name": "Tatra Volt", "color": (30, 180, 90)},
    {"name": "Bohemia Cyber", "color": (210, 0, 100)}
]

# ==========================================
# 1b. PŘIDÁNO: NEURONOVÁ SÍŤ + GENETICKÝ ALGORITMUS PRO AI AUTA
# Toto nahrazuje "tvrdé" pronásledování hráče skutečně se učícím chováním.
# ==========================================
AI_POP_SIZE = 12          # kolik "mozků" (genomů) je v populaci
AI_INPUT_SIZE = 6         # kolik senzorických vstupů síť dostává
AI_HIDDEN_SIZE = 8        # velikost skryté vrstvy
AI_OUTPUT_SIZE = 2        # výstupy: [zatáčení, násobič rychlosti]
AI_GENERATION_FRAMES = FPS * 10   # UPRAVENO: zkráceno z 20s na 10s - AI se vyhodnocuje a učí (eviluje) rychleji
AI_MUTATION_RATE = 0.15
AI_MUTATION_AMOUNT = 0.6

# UPRAVENO: rozdělené odměny/tresty podle zadání -
# náraz do hráče = hodně bodů, jízda k hráči = středně bodů,
# jízda od hráče = hodně bodů se odebere, náraz do okraje silnice = středně bodů se odebere.
AI_CRASH_INTO_PLAYER_REWARD = 300.0   # velká odměna za dostižení/náraz do hráče
AI_APPROACH_REWARD_SCALE = 1.5        # střední odměna za přibližování se k hráči
AI_RETREAT_PENALTY_SCALE = 10.0       # UPRAVENO: ještě větší trest za vzdalování se od hráče
AI_OFFROAD_HIT_PENALTY = -1.0         # střední trest za náraz do okraje/mimo silnici

# PŘIDÁNO: pokud auto dlouho jen kouká/krouží na jednom místě (opakuje stejný pohyb,
# jezdí v kruhu apod.), pravidelně kontrolujeme, jestli se za posledních pár sekund
# reálně posunulo dál, nebo jestli se pořád vrací zhruba na stejné místo.
AI_STUCK_SAMPLE_INTERVAL = FPS          # jak často (ve snímcích) se ukládá poloha do historie - zde 1x za sekundu
AI_STUCK_HISTORY_LEN = 5                # kolik posledních vzorků (sekund) se sleduje - zde 5 sekund
AI_STUCK_DISTANCE_THRESHOLD = 90.0      # pokud se za sledované okno posunulo méně než tolik jednotek, je to "zaseknuté"
AI_STUCK_PENALTY = -8.0                 # trest udělený pokaždé, když je auto vyhodnoceno jako zaseknuté/kroužící

# PŘIDÁNO: verze odměnové funkce. Pokaždé, když změníš vzorec fitness (jako teď),
# zvyš toto číslo o 1 - uložená stará AI paměť (natrénovaná na jiné odměny)
# se pak automaticky zahodí a hra začne trénovat znovu od nuly na aktuální pravidla,
# místo aby si auta táhla staré (a teď už špatné) návyky.
AI_FITNESS_VERSION = 3


def ai_weight_count():
    return (AI_INPUT_SIZE + 1) * AI_HIDDEN_SIZE + (AI_HIDDEN_SIZE + 1) * AI_OUTPUT_SIZE


def ai_random_weights():
    n = ai_weight_count()
    return [random.uniform(-1, 1) for _ in range(n)]


def ai_think(weights, inputs):
    # Dopředný průchod: input -> hidden (tanh) -> output (tanh)
    idx = 0
    hidden = [0.0] * AI_HIDDEN_SIZE
    for h in range(AI_HIDDEN_SIZE):
        s = weights[idx]; idx += 1
        for i in range(AI_INPUT_SIZE):
            s += inputs[i] * weights[idx]; idx += 1
        hidden[h] = math.tanh(s)

    out = [0.0] * AI_OUTPUT_SIZE
    for o in range(AI_OUTPUT_SIZE):
        s = weights[idx]; idx += 1
        for h in range(AI_HIDDEN_SIZE):
            s += hidden[h] * weights[idx]; idx += 1
        out[o] = math.tanh(s)
    return out


def ai_crossover(wa, wb):
    return [wa[i] if random.random() < 0.5 else wb[i] for i in range(len(wa))]


def ai_mutate(weights):
    child = list(weights)
    for i in range(len(child)):
        if random.random() < AI_MUTATION_RATE:
            child[i] += random.uniform(-1, 1) * AI_MUTATION_AMOUNT
    return child


class AIPopulation:
    """Drží 'genomy' (váhy sítí) pro všechna ta a stará se o jejich evoluci."""

    def __init__(self, size):
        self.size = size
        self.genomes = [ai_random_weights() for _ in range(size)]
        self.fitness = [0.0] * size
        self.generation = 1
        self.best_fitness_ever = 0.0

    def get_weights(self, slot):
        return self.genomes[slot % self.size]

    def add_fitness(self, slot, amount):
        self.fitness[slot % self.size] += amount

    def evolve(self):
        ranked = sorted(range(self.size), key=lambda i: self.fitness[i], reverse=True)
        if self.fitness[ranked[0]] > self.best_fitness_ever:
            self.best_fitness_ever = self.fitness[ranked[0]]

        elite = ranked[:2]
        pool = ranked[:max(4, self.size // 2)]

        new_genomes = [list(self.genomes[i]) for i in elite]  # elitismus - nejlepší 2 beze změny
        while len(new_genomes) < self.size:
            parent_a = self.genomes[random.choice(pool)]
            parent_b = self.genomes[random.choice(pool)]
            child = ai_mutate(ai_crossover(parent_a, parent_b))
            new_genomes.append(child)

        self.genomes = new_genomes
        self.fitness = [0.0] * self.size
        self.generation += 1


AI_POPULATION = AIPopulation(AI_POP_SIZE)

# ==========================================
# 1c. PŘIDÁNO: PERSISTENTNÍ PAMĚŤ AI - ULOŽENÍ/NAČTENÍ NAUČENÝCH MOZKŮ NA DISK
# Bez tohohle by AI po zavření hry zapomněla úplně všechno a příští spuštění
# by začínalo znovu od náhodných vah (generace 1).
# ==========================================
AI_SAVE_PATH = "ai_brains.json"


def save_ai_population(population, path=AI_SAVE_PATH):
    data = {
        "fitness_version": AI_FITNESS_VERSION,  # PŘIDÁNO
        "generation": population.generation,
        "best_fitness_ever": population.best_fitness_ever,
        "genomes": population.genomes,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Nepodařilo se uložit AI mozky: {e}")


def load_ai_population(population, path=AI_SAVE_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return  # zatím žádná uložená paměť neexistuje - v pořádku, poběží se s náhodnou populací
    except Exception as e:
        print(f"Nepodařilo se načíst AI mozky: {e}")
        return

    # PŘIDÁNO: pokud se od uložení změnila odměnová funkce (jiné AI_FITNESS_VERSION),
    # stará naučená paměť by auta učila špatné (zastaralé) chování - proto ji zahodíme
    # a necháme populaci natrénovat znovu od nuly na aktuální pravidla.
    saved_version = data.get("fitness_version")
    if saved_version != AI_FITNESS_VERSION:
        print(f"Odměnová funkce AI se změnila (uloženo v{saved_version}, aktuálně v{AI_FITNESS_VERSION}) - "
              f"zahazuji starou AI paměť a začínám trénovat znovu.")
        return

    saved_genomes = data.get("genomes", [])
    if len(saved_genomes) == population.size and all(len(g) == ai_weight_count() for g in saved_genomes):
        population.genomes = saved_genomes
        population.generation = data.get("generation", population.generation)
        population.best_fitness_ever = data.get("best_fitness_ever", population.best_fitness_ever)
        print(f"Načtena naučená AI paměť (generace {population.generation}, "
              f"nejlepší fitness {int(population.best_fitness_ever)}).")
    else:
        print("Uložená AI paměť neodpovídá aktuální konfiguraci sítě, používám novou populaci.")


load_ai_population(AI_POPULATION)  # PŘIDÁNO: při startu hry rovnou zkusit načíst, co se AI naučila minule


# ==========================================
# 1c-2. PŘIDÁNO: PERSISTENTNÍ NEJVYŠŠÍ SKÓRE - ULOŽENÍ/NAČTENÍ Z VEDLEJŠÍHO .TXT SOUBORU
# Bez tohohle by se nejvyšší skóre po zavření hry ztratilo.
# ==========================================
HIGH_SCORE_PATH = "nejvyssi_skore.txt"


def load_high_score(path=HIGH_SCORE_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return 0  # soubor zatím neexistuje nebo je poškozený - začínáme od nuly


def save_high_score(value, path=HIGH_SCORE_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(int(value)))
    except Exception as e:
        print(f"Nepodařilo se uložit nejvyšší skóre: {e}")


# ==========================================
# 1d. PŘIDÁNO: SCHOPNOSTI HRÁČE (DASH, POKLÁDÁNÍ BODCŮ), AKCELERACE
# ==========================================
PLAYER_ACCEL = 0.45                     # jak rychle hráč zrychluje/brzdí (jednotky rychlosti za snímek)
PLAYER_DASH_SPEED = 16.0                # rychlost pohybu během dashe
PLAYER_DASH_DURATION_FRAMES = 5         # UPRAVENO: zkráceno z 10 na 5 snímků - dash má kratší dojezd
PLAYER_DASH_COOLDOWN_FRAMES = FPS * 3   # UPRAVENO: sníženo z 5s na 3s - dash lze použít jednou za 3 sekundy

AI_ACCEL = 0.35                          # jak rychle AI auta zrychlují/brzdí
AI_FULL_SPEED_CRASH_RATIO = 0.85         # od jaké rychlosti (podíl max. rychlosti auta) se náraz počítá jako "na plnou rychlost"
AI_WALL_CRASH_FREEZE_FRAMES = FPS * 2    # zamrznutí AI auta na 2s po nárazu do zdi na plnou rychlost

SPIKE_RADIUS = 30                        # poloměr bodcové pasti
SPIKE_FREEZE_FRAMES = FPS * 2            # UPRAVENO: zamrznutí AI auta na 2s po najetí na bodce (bodec se pak z mapy odstraní)
SPIKE_PLACE_COOLDOWN_FRAMES = FPS * 3    # PŘIDÁNO: jak často smí hráč pokládat nové bodce (klávesa F)


# ==========================================
# 1e. PŘIDÁNO: OBCHOD S AUTY (GARÁŽ) A PERZISTENTNÍ MINCE ZA SKÓRE
# ==========================================
PLAYER_BASE_SPEED = 6.0  # základní rychlost hráče, kterou pak násobí "speed_mult" vybraného auta

# PŘIDÁNO: katalog rozšířen na 10 aut - ceny dál rostou stejným tempem jako předtím
# (každé další auto zdraží o dalších +150 mincí navíc oproti předchozímu skoku),
# jen se řada teď táhne až k desátému autu.
CAR_CATALOG = [
    {"name": "Škoda Standard",  "price": 0,    "color": (0, 120, 255),   "speed_mult": 1.00, "dash_cd_mult": 1.00, "category": "normal"},
    {"name": "Tatra Sport",     "price": 150,  "color": (220, 40, 40),   "speed_mult": 1.10, "dash_cd_mult": 0.90, "category": "normal"},
    {"name": "Praga Turbo",     "price": 450,  "color": (255, 170, 0),   "speed_mult": 1.20, "dash_cd_mult": 0.80, "category": "normal"},
    {"name": "Bohemia Rallye",  "price": 900,  "color": (30, 200, 120),  "speed_mult": 1.30, "dash_cd_mult": 0.70, "category": "normal"},
    {"name": "Wartburg Blesk",  "price": 1500, "color": (150, 60, 200),  "speed_mult": 1.38, "dash_cd_mult": 0.62, "category": "normal"},
    {"name": "Aero Delta",      "price": 2250, "color": (0, 200, 180),   "speed_mult": 1.46, "dash_cd_mult": 0.55, "category": "normal"},
    {"name": "Jawa Racer",      "price": 3150, "color": (230, 200, 20),  "speed_mult": 1.54, "dash_cd_mult": 0.48, "category": "normal"},
    {"name": "Tatra Phantom",   "price": 4200, "color": (180, 20, 50),   "speed_mult": 1.62, "dash_cd_mult": 0.42, "category": "normal"},
    {"name": "Praga Apex",      "price": 5400, "color": (200, 200, 210), "speed_mult": 1.72, "dash_cd_mult": 0.35, "category": "normal"},
    {"name": "Bohemia Titan",   "price": 6750, "color": (140, 30, 200),  "speed_mult": 1.85, "dash_cd_mult": 0.28, "category": "normal"},
    # PŘIDÁNO: kategorie "TĚŽKÁ VOZIDLA" - Autobus, Loď a Tank. Všechna jsou pomalejší
    # než běžná auta (nižší speed_mult), ale platí pro ně pravidlo "lives" > 1, takže
    # vydrží víc než jeden náraz AI auta, než skutečně přijde game over. Ceny jdou
    # cenově vzestupně: Autobus (nejlevnější) -> Loď -> Tank (nejdražší a nejodolnější).
    {"name": "Karosa Autobus",  "price": 2600, "color": (255, 195, 0),   "speed_mult": 0.65, "dash_cd_mult": 1.20, "lives": 2, "category": "tezka"},
    {"name": "Vltavská Loď",    "price": 3800, "color": (60, 140, 200),  "speed_mult": 0.55, "dash_cd_mult": 1.35, "lives": 2, "category": "tezka", "is_boat": True},
    {"name": "Obrněný Tank",    "price": 5000, "color": (80, 100, 60),   "speed_mult": 0.45, "dash_cd_mult": 1.50, "lives": 3, "category": "tezka"},
    # PŘIDÁNO: kategorie "SPECIÁLNÍ" - netradiční vozidla s unikátními pravidly (viz "special"):
    # Gumová kachna je extrémně rychlá, ale JAKÝKOLIV náraz do zdi ji okamžitě zničí.
    # Kouzelný Deštník při dashi na chvíli vzlétne do vzduchu a je po tu dobu nezranitelný
    # vůči AI autům a přeletí i přes budovy/řeku. Festival Car vydrží dva nájezdy AI aut
    # (ty se od něj jen odrazí) a game over nastává až na třetí nájezd.
    {"name": "Gumová Kachna",   "price": 3500, "color": (255, 210, 0),   "speed_mult": 2.00, "dash_cd_mult": 1.00, "category": "special", "special": "duck"},
    {"name": "Kouzelný Deštník","price": 4500, "color": (150, 40, 200),  "speed_mult": 1.00, "dash_cd_mult": 0.50, "category": "special", "special": "umbrella"},
    {"name": "Festival Car",    "price": 4000, "color": (255, 80, 180),  "speed_mult": 0.90, "dash_cd_mult": 1.00, "lives": 3, "category": "special", "special": "festival"},
]

PLAYER_DATA_PATH = "hrac_progress.json"


def load_player_data(path=PLAYER_DATA_PATH):
    """PŘIDÁNO: načte uložené mince a koupená/vybraná auta hráče z disku."""
    data = {"coins": 0, "owned": [0], "selected": 0}
    try:
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        data["coins"] = int(loaded.get("coins", 0))
        owned = loaded.get("owned", [0])
        data["owned"] = owned if 0 in owned else [0] + owned  # základní auto je vždy k dispozici
        data["selected"] = int(loaded.get("selected", 0))
    except FileNotFoundError:
        pass  # zatím žádný uložený postup - v pořádku, začíná se od nuly se základním autem
    except Exception as e:
        print(f"Nepodařilo se načíst uložený postup hráče: {e}")
    return data


def save_player_data(data, path=PLAYER_DATA_PATH):
    """PŘIDÁNO: uloží aktuální mince a koupená/vybraná auta hráče na disk."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Nepodařilo se uložit postup hráče: {e}")


# PŘIDÁNO: hra se postupně ztěžuje podle dosaženého skóre v aktuálním běhu -
# za každých 100 bodů skóre se AI auta zrychlí o 0.1 a smí jich najednou jezdit o jedno víc.
SCORE_PER_DIFFICULTY_TIER = 100
AI_SPEED_PER_TIER = 0.1
AI_SPAWN_CAP_BASE = 14
AI_BASE_SPEED = 6.0


def difficulty_tier_for_score(displayed_score):
    return displayed_score // SCORE_PER_DIFFICULTY_TIER


def get_shop_visible_indices(mode, player_data):
    """PŘIDÁNO: vrátí seznam indexů katalogu, které se mají zobrazit v dané obrazovce -
    v obchodě úplně všechny, v garáži jen ty, které hráč už vlastní. Pořadí je zachováno
    podle CAR_CATALOG, takže běžná auta jsou vždy před těžkými vozidly."""
    if mode == "garage":
        return [i for i in range(len(CAR_CATALOG)) if i in player_data["owned"]]
    return list(range(len(CAR_CATALOG)))


# PŘIDÁNO: hranice oblasti obsahu (karet aut) v garáži/obchodě - nad ní zůstává pevný
# titulek a stav mincí, pod ní pevná tlačítka HRÁT/ZPĚT. Jen obsah mezi těmito hranicemi
# se posouvá při scrollování kolečkem myši.
SHOP_CONTENT_TOP = 140
SHOP_CONTENT_BOTTOM = SCREEN_HEIGHT - 110


def compute_shop_layout(visible_indices):
    """UPRAVENO: rozložení karet aut v garáži/obchodě - auta se teď dělí do sekcí podle
    kategorie ("normal" / "tezka" / "special"), každá sekce má svůj nadpis a karty pod ním jsou
    rozložené do mřížky o 6 sloupcích. Vrací slovník {index_v_katalogu: Rect}, seznam
    nadpisů sekcí (text, x, y), Rect tlačítka HRÁT a celkovou výšku obsahu (pro scrollování)."""
    card_w, card_h = 210, 230
    gap_x, gap_y = 14, 14
    start_x = 50
    start_y = SHOP_CONTENT_TOP
    columns = 6
    header_height = 32
    section_gap = 36

    # Rozdělení viditelných indexů do souvislých skupin podle kategorie (pořadí zachováno)
    groups = []
    for idx in visible_indices:
        cat = CAR_CATALOG[idx].get("category", "normal")
        if groups and groups[-1][0] == cat:
            groups[-1][1].append(idx)
        else:
            groups.append((cat, [idx]))

    rects_by_index = {}
    headers = []
    cur_y = start_y
    for group_i, (cat, cat_indices) in enumerate(groups):
        if group_i > 0:
            cur_y += section_gap
        # UPRAVENO: přidán nadpis pro novou kategorii "SPECIÁLNÍ"
        if cat == "tezka":
            label = "TĚŽKÁ VOZIDLA"
        elif cat == "special":
            label = "SPECIÁLNÍ"
        else:
            label = "BĚŽNÁ AUTA"
        headers.append((label, start_x, cur_y))
        cur_y += header_height
        for i, idx in enumerate(cat_indices):
            col = i % columns
            row = i // columns
            x = start_x + col * (card_w + gap_x)
            y = cur_y + row * (card_h + gap_y)
            rects_by_index[idx] = pygame.Rect(x, y, card_w, card_h)
        rows_used = math.ceil(len(cat_indices) / columns)
        cur_y += rows_used * (card_h + gap_y) - gap_y

    content_bottom = cur_y  # PŘIDÁNO: celková výška obsahu, potřebná pro výpočet max. scrollu
    play_rect = pygame.Rect(SCREEN_WIDTH - 260, SCREEN_HEIGHT - 90, 200, 60)
    return rects_by_index, headers, play_rect, content_bottom


def compute_shop_max_scroll(mode, player_data):
    """PŘIDÁNO: spočítá, o kolik pixelů maximálně lze obsah dané obrazovky (garáž/obchod)
    posunout scrollováním, podle toho, kolik karet se do ní vejde."""
    visible_indices = get_shop_visible_indices(mode, player_data)
    _rects, _headers, _play_rect, content_bottom = compute_shop_layout(visible_indices)
    visible_height = SHOP_CONTENT_BOTTOM - SHOP_CONTENT_TOP
    return max(0, (content_bottom - SHOP_CONTENT_TOP) - visible_height + 20)


def draw_shop_menu(screen, font_title, font_main, font_small, player_data, mouse_pos,
                    mode="shop", back_rect=None, scroll_y=0):
    """UPRAVENO: vykreslí obrazovku Garáž nebo Obchod. V režimu "shop" (obchod) se
    zobrazují všechna auta z katalogu (i ta ještě nekoupená), v režimu "garage" (garáž)
    se zobrazují jen auta, která hráč už vlastní, a slouží k výběru aktuálního auta.
    UPRAVENO: auta se teď navíc dělí do sekcí "BĚŽNÁ AUTA", "TĚŽKÁ VOZIDLA" a "SPECIÁLNÍ"
    s vlastními nadpisy. Tlačítko HRÁT se kreslí jen v garáži (mode == "garage"), v obchodě místo
    něj zůstane jen tlačítko návratu do menu.
    PŘIDÁNO: karty aut se teď kreslí v ohraničené (ořezané) oblasti mezi SHOP_CONTENT_TOP a
    SHOP_CONTENT_BOTTOM a lze jimi scrollovat (scroll_y) kolečkem myši, takže se do garáže/obchodu
    vejde i mnohem víc aut, než kolik se najednou zobrazí na obrazovce."""
    screen.fill((25, 28, 32))
    if mode == "garage":
        title_text = "Deadly Traffic - GARÁŽ"
        subtitle_text = "Vyber si auto, se kterým pojedeš:"
    else:
        title_text = "Deadly Traffic - OBCHOD"
        subtitle_text = "Kup si nová auta za mince nasbírané ze skóre:"

    visible_indices = get_shop_visible_indices(mode, player_data)
    card_rects, headers, play_rect, content_bottom = compute_shop_layout(visible_indices)

    screen.blit(font_title.render(title_text, True, COLOR_GOLD), (60, 50))
    screen.blit(font_main.render(f"Mince: {player_data['coins']}", True, COLOR_GOLD), (60, 100))
    screen.blit(font_main.render(subtitle_text, True, (200, 200, 200)), (60, 120))

    # PŘIDÁNO: veškerý posouvatelný obsah (nadpisy sekcí + karty aut) se kreslí uvnitř
    # ořezané oblasti, aby při scrollování nepřejížděl přes titulek ani přes tlačítka dole.
    content_clip = pygame.Rect(0, SHOP_CONTENT_TOP, SCREEN_WIDTH, SHOP_CONTENT_BOTTOM - SHOP_CONTENT_TOP)
    screen.set_clip(content_clip)

    for label, hx, hy in headers:
        screen.blit(font_title.render(label, True, COLOR_GOLD), (hx, hy - scroll_y))

    for idx in visible_indices:
        car = CAR_CATALOG[idx]
        rect = card_rects[idx].move(0, -scroll_y)
        if rect.bottom < SHOP_CONTENT_TOP or rect.top > SHOP_CONTENT_BOTTOM:
            continue  # PŘIDÁNO: karta je mimo viditelnou oblast - netřeba ji kreslit
        owned = idx in player_data["owned"]
        selected = idx == player_data["selected"]

        if selected and mode == "garage":
            border_color = COLOR_GOLD
        elif rect.collidepoint(mouse_pos):
            border_color = (120, 200, 255)
        else:
            border_color = (80, 85, 90)

        pygame.draw.rect(screen, (40, 44, 50), rect, border_radius=10)
        pygame.draw.rect(screen, border_color, rect, 3, border_radius=10)

        car_preview = build_pixel_car_surface(car["color"], scale=5)
        preview_rect = car_preview.get_rect(center=(rect.centerx, rect.top + 60))
        screen.blit(car_preview, preview_rect.topleft)

        screen.blit(font_small.render(car["name"], True, (255, 255, 255)), (rect.x + 12, rect.top + 118))
        screen.blit(font_small.render(f"Rychlost: x{car['speed_mult']:.2f}", True, (190, 190, 190)),
                    (rect.x + 12, rect.top + 140))
        cd_or_lives_y = rect.top + 158
        screen.blit(font_small.render(f"Cooldown dashe: x{car['dash_cd_mult']:.2f}", True, (190, 190, 190)),
                    (rect.x + 12, cd_or_lives_y))

        # UPRAVENO: dynamické řazení dalších řádků (životy / řeka / popis speciální schopnosti),
        # aby se u Festival Caru (má lives i special zároveň) text nepřekrýval.
        info_y = rect.top + 176
        if car.get("lives", 1) > 1:
            screen.blit(font_small.render(f"Životy: {car['lives']}", True, (255, 210, 140)),
                        (rect.x + 12, info_y))
            info_y += 18

        if car.get("is_boat"):
            # PŘIDÁNO: jediné vozidlo, které smí jezdit po řece
            screen.blit(font_small.render("Jediná umí jezdit po řece!", True, (140, 200, 255)),
                        (rect.x + 12, info_y))
            info_y += 18

        special = car.get("special")
        if special == "duck":
            screen.blit(font_small.render("Umírá na náraz do zdi!", True, (255, 140, 140)),
                        (rect.x + 12, info_y))
            info_y += 18
        elif special == "umbrella":
            screen.blit(font_small.render("Dash = let vzduchem", True, (200, 170, 255)),
                        (rect.x + 12, info_y))
            info_y += 18
        elif special == "festival":
            screen.blit(font_small.render("Vydrží 2 nájezdy AI", True, (255, 210, 150)),
                        (rect.x + 12, info_y))
            info_y += 18

        if mode == "garage":
            if selected:
                status_text, status_color = "VYBRÁNO", (120, 255, 150)
            else:
                status_text, status_color = "Klikni pro výběr", (150, 220, 255)
        else:
            if owned:
                status_text, status_color = "Vlastníš", (150, 220, 255)
            elif player_data["coins"] >= car["price"]:
                status_text, status_color = f"Koupit za {car['price']} mincí", (255, 220, 120)
            else:
                status_text, status_color = f"Chybí mince (cena {car['price']})", (255, 120, 120)

        status_y = max(rect.top + 205, info_y)
        screen.blit(font_small.render(status_text, True, status_color), (rect.x + 12, status_y))

    screen.set_clip(None)  # PŘIDÁNO: konec ořezané oblasti - dál se kreslí přes celou obrazovku

    # PŘIDÁNO: jednoduchý posuvník napravo od obsahu, viditelný jen když je co scrollovat
    max_scroll = max(0, (content_bottom - SHOP_CONTENT_TOP) - (SHOP_CONTENT_BOTTOM - SHOP_CONTENT_TOP) + 20)
    if max_scroll > 0:
        track_h = SHOP_CONTENT_BOTTOM - SHOP_CONTENT_TOP
        track_rect = pygame.Rect(SCREEN_WIDTH - 24, SHOP_CONTENT_TOP, 10, track_h)
        pygame.draw.rect(screen, (50, 54, 60), track_rect, border_radius=5)
        thumb_h = max(30, int(track_h * track_h / (track_h + max_scroll)))
        thumb_y = SHOP_CONTENT_TOP + int((track_h - thumb_h) * (scroll_y / max_scroll))
        thumb_rect = pygame.Rect(SCREEN_WIDTH - 24, thumb_y, 10, thumb_h)
        pygame.draw.rect(screen, COLOR_GOLD, thumb_rect, border_radius=5)
        screen.blit(font_small.render("Scroluj kolečkem myši", True, (150, 150, 150)),
                    (SCREEN_WIDTH - 260, SHOP_CONTENT_TOP - 22))

    if mode == "garage":
        play_color = (0, 170, 90) if play_rect.collidepoint(mouse_pos) else (0, 130, 70)
        pygame.draw.rect(screen, play_color, play_rect, border_radius=8)
        pygame.draw.rect(screen, (150, 255, 200), play_rect, 2, border_radius=8)
        play_txt = font_title.render("HRÁT", True, (255, 255, 255))
        screen.blit(play_txt, (play_rect.centerx - play_txt.get_width() // 2,
                                play_rect.centery - play_txt.get_height() // 2))

    if back_rect is not None:
        back_color = (90, 95, 100) if back_rect.collidepoint(mouse_pos) else (60, 64, 68)
        pygame.draw.rect(screen, back_color, back_rect, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), back_rect, 2, border_radius=8)
        back_txt = font_main.render("ZPĚT DO MENU", True, (255, 255, 255))
        screen.blit(back_txt, (back_rect.centerx - back_txt.get_width() // 2,
                                back_rect.centery - back_txt.get_height() // 2))


def compute_main_menu_layout():
    """UPRAVENO: rozložení čtyř tlačítek hlavního menu - Hrát, Garáž, Obchod, Ukončit hru.
    Tlačítka jsou umístěná tak, aby seděla přesně na tlačítka, která už jsou vykreslená
    přímo v obrázku pozadí menu (menu_pozadi.png) - takže vizuálně splynou s obrázkem."""
    # PŘIDÁNO: hodnoty přesně změřené podle tlačítek nakreslených v obrázku menu_pozadi.png
    # (po přeškálování "cover" na 1920x1080) - viz komentář u MENU_BG_IMAGE výše.
    btn_w, btn_h = 195, 90
    gap = 20
    center_x = 857
    start_y = 503
    play_rect = pygame.Rect(center_x - btn_w // 2, start_y, btn_w, btn_h)
    garage_rect = pygame.Rect(center_x - btn_w // 2, start_y + (btn_h + gap), btn_w, btn_h)
    shop_rect = pygame.Rect(center_x - btn_w // 2, start_y + 2 * (btn_h + gap), btn_w, btn_h)
    exit_rect = pygame.Rect(center_x - btn_w // 2, start_y + 3 * (btn_h + gap), btn_w, btn_h)
    return play_rect, garage_rect, shop_rect, exit_rect


def draw_main_menu(screen, font_title, font_main, player_data, mouse_pos, play_rect, garage_rect, shop_rect, exit_rect):
    """UPRAVENO: hlavní úvodní menu hry se čtyřmi volbami - Hrát / Garáž / Obchod / Ukončit hru.
    PŘIDÁNO: pokud je k dispozici obrázek pozadí (menu_pozadi.png), vykreslí se jako pozadí
    celé obrazovky menu a tlačítka se nad ním zobrazí jen jako neviditelné/lehce zvýrazněné
    klikací zóny (obrázek už má svoje vlastní vykreslené HRÁT/GARÁŽ/OBCHOD/UKONČIT tlačítka -
    tahle logická tlačítka se s nimi jen přesně překrývají). Bez obrázku se použije původní
    tmavé pozadí s klasicky vykreslenými barevnými tlačítky, aby hra fungovala i bez obrázku."""
    if MENU_BG_IMAGE is not None:
        screen.blit(MENU_BG_IMAGE, (0, 0))
    else:
        screen.fill((22, 24, 28))
        title_txt = font_title.render("Deadly Traffic", True, COLOR_GOLD)
        screen.blit(title_txt, (SCREEN_WIDTH // 2 - title_txt.get_width() // 2, 120))

    # PŘIDÁNO: mince a vybrané auto se zobrazují na volném pruhu mezi logem a tlačítky
    # (kolem x=857, stejný střed jako tlačítka), s tmavým polopropustným podkladem
    # pro čitelnost přes pestrý obrázek pozadí.
    menu_text_center_x = 857
    coins_txt = font_main.render(f"Mince: {player_data['coins']}", True, COLOR_GOLD)
    coins_bg = pygame.Surface((coins_txt.get_width() + 20, coins_txt.get_height() + 10), pygame.SRCALPHA)
    coins_bg.fill((0, 0, 0, 150))
    screen.blit(coins_bg, (menu_text_center_x - coins_bg.get_width() // 2, 415))
    screen.blit(coins_txt, (menu_text_center_x - coins_txt.get_width() // 2, 420))

    selected_car = CAR_CATALOG[player_data["selected"]]
    car_txt = font_main.render(f"Aktuální auto: {selected_car['name']}", True, (230, 230, 230))
    car_bg = pygame.Surface((car_txt.get_width() + 20, car_txt.get_height() + 10), pygame.SRCALPHA)
    car_bg.fill((0, 0, 0, 150))
    screen.blit(car_bg, (menu_text_center_x - car_bg.get_width() // 2, 450))
    screen.blit(car_txt, (menu_text_center_x - car_txt.get_width() // 2, 455))

    buttons = [(play_rect, "HRÁT", (0, 130, 70), (0, 170, 90)),
               (garage_rect, "GARÁŽ", (60, 70, 130), (80, 95, 170)),
               (shop_rect, "OBCHOD", (130, 95, 30), (170, 125, 40)),
               (exit_rect, "UKONČIT HRU", (130, 25, 40), (180, 40, 60))]

    for rect, label, base_color, hover_color in buttons:
        if MENU_BG_IMAGE is not None:
            # PŘIDÁNO: obrázek už má tlačítko nakreslené - tady se jen zvýrazní okraj
            # při přejetí myší (hover), aby bylo jasné, že se na tlačítko dá kliknout.
            if rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, COLOR_GOLD, rect, 4, border_radius=14)
        else:
            color = hover_color if rect.collidepoint(mouse_pos) else base_color
            pygame.draw.rect(screen, color, rect, border_radius=10)
            pygame.draw.rect(screen, (230, 230, 230), rect, 2, border_radius=10)
            label_txt = font_title.render(label, True, (255, 255, 255))
            screen.blit(label_txt, (rect.centerx - label_txt.get_width() // 2,
                                     rect.centery - label_txt.get_height() // 2))

def approach_value(current, target, step):
    """PŘIDÁNO: pomocná funkce pro plynulou akceleraci/deceleraci směrem k cílové hodnotě
    (používá ji jak hráč, tak AI auta)."""
    if current < target:
        return min(target, current + step)
    if current > target:
        return max(target, current - step)
    return current


COLOR_ASPHALT = (58, 60, 64)          # PŘIDÁNO: barva asfaltu místo bílé plochy
COLOR_ASPHALT_BORDER = (34, 35, 38)   # PŘIDÁNO: tmavší okraj/obrubník silnice
COLOR_LANE_PAINT = (230, 220, 185)    # PŘIDÁNO: barva nastříkaných pruhů (nažloutlá bílá)


def draw_road_segment(surface, x1, y1, x2, y2, thickness):
    """PŘIDÁNO: nakreslí úsek silnice s asfaltovou texturou a nastříkanými pruhy -
    plné krajové čáry po obou stranách vozovky a přerušovaná středová čára."""
    pygame.draw.line(surface, COLOR_ASPHALT_BORDER, (x1, y1), (x2, y2), thickness + 8)
    pygame.draw.line(surface, COLOR_ASPHALT, (x1, y1), (x2, y2), thickness)

    horizontal = abs(x2 - x1) >= abs(y2 - y1)
    edge_offset = thickness * 0.36
    dash_len, gap_len = 22, 16

    if horizontal:
        y = y1
        pygame.draw.line(surface, COLOR_LANE_PAINT, (x1, y - edge_offset), (x2, y - edge_offset), 2)
        pygame.draw.line(surface, COLOR_LANE_PAINT, (x1, y + edge_offset), (x2, y + edge_offset), 2)
        x = x1
        while x < x2:
            dash_end = min(x + dash_len, x2)
            pygame.draw.line(surface, COLOR_LANE_PAINT, (x, y), (dash_end, y), 3)
            x += dash_len + gap_len
    else:
        x = x1
        pygame.draw.line(surface, COLOR_LANE_PAINT, (x - edge_offset, y1), (x - edge_offset, y2), 2)
        pygame.draw.line(surface, COLOR_LANE_PAINT, (x + edge_offset, y1), (x + edge_offset, y2), 2)
        y = y1
        while y < y2:
            dash_end = min(y + dash_len, y2)
            pygame.draw.line(surface, COLOR_LANE_PAINT, (x, y), (x, dash_end), 3)
            y += dash_len + gap_len


def draw_roundabout(surface, cx, cy, outer_radius, inner_radius):
    """PŘIDÁNO: kruhový objezd ve STEJNÉM designu jako rovné silnice (tmavý obrubník +
    asfaltová jízdní plocha + nastříkané pruhy), aby vizuálně plynule navazoval na
    silnice, které do něj vjíždí, místo aby to byla jen holá bílá kruhová plocha."""
    # tmavý obrubník - stejný princip jako "thickness + 8" u rovných silnic (o 4px širší po obvodu)
    pygame.draw.circle(surface, COLOR_ASPHALT_BORDER, (cx, cy), outer_radius + 4)
    # asfaltová jízdní plocha objezdu
    pygame.draw.circle(surface, COLOR_ASPHALT, (cx, cy), outer_radius)

    # vnitřní ostrůvek uprostřed objezdu - zelený se stromy, stejný styl jako parky ve městě
    pygame.draw.circle(surface, COLOR_PARK, (cx, cy), inner_radius)
    pygame.draw.circle(surface, COLOR_ASPHALT_BORDER, (cx, cy), inner_radius, 3)
    random.seed(f"roundabout_{cx}_{cy}")
    for _ in range(5):
        ang = random.uniform(0, math.tau)
        rad = random.uniform(6, max(7, inner_radius - 8))
        tx = cx + math.cos(ang) * rad
        ty = cy + math.sin(ang) * rad
        pygame.draw.circle(surface, (90, 140, 80), (int(tx), int(ty)), random.randint(5, 9))
    random.seed()

    # přerušovaná pruhová čára uprostřed jízdního pruhu (mezi ostrůvkem a vnějším okrajem),
    # stejná barva jako COLOR_LANE_PAINT na rovných silnicích
    lane_radius = (outer_radius + inner_radius) / 2
    dash_count = max(8, int(lane_radius / 12))
    for i in range(dash_count):
        if i % 2 == 0:
            continue
        a1 = (i / dash_count) * math.tau
        a2 = ((i + 0.55) / dash_count) * math.tau
        p1 = (cx + math.cos(a1) * lane_radius, cy + math.sin(a1) * lane_radius)
        p2 = (cx + math.cos(a2) * lane_radius, cy + math.sin(a2) * lane_radius)
        pygame.draw.line(surface, COLOR_LANE_PAINT, p1, p2, 3)

    # krajové čáry jízdní plochy - vnější a vnitřní, stejně jako edge_offset čáry u rovných silnic
    pygame.draw.circle(surface, COLOR_LANE_PAINT, (cx, cy), outer_radius, 2)
    pygame.draw.circle(surface, COLOR_LANE_PAINT, (cx, cy), inner_radius, 2)


def draw_spike_trap(surface, cx, cy):
    """Vykreslí bodcovou past (tmavý kotouč + červené hroty) na dané lokální/obrazovkové souřadnici."""
    pygame.draw.circle(surface, (35, 35, 38), (int(cx), int(cy)), SPIKE_RADIUS)
    for i in range(8):
        ang = i * (math.pi / 4)
        tip_x = cx + math.cos(ang) * SPIKE_RADIUS
        tip_y = cy + math.sin(ang) * SPIKE_RADIUS
        base1_x = cx + math.cos(ang - 0.25) * (SPIKE_RADIUS * 0.4)
        base1_y = cy + math.sin(ang - 0.25) * (SPIKE_RADIUS * 0.4)
        base2_x = cx + math.cos(ang + 0.25) * (SPIKE_RADIUS * 0.4)
        base2_y = cy + math.sin(ang + 0.25) * (SPIKE_RADIUS * 0.4)
        pygame.draw.polygon(surface, (205, 25, 25), [(tip_x, tip_y), (base1_x, base1_y), (base2_x, base2_y)])


def build_pixel_car_surface(body_color, scale=4):
    """PŘIDÁNO: vytvoří jednoduchou pixel-art texturu autíčka hráče (pohled shora,
    přední částí nahoru), namalovanou přímo v kódu blok po bloku - takže není potřeba
    žádný externí obrázkový soubor."""
    pixel_rows = [
        "..RRRR..",
        ".RRRRRR.",
        "RRWWWWRR",
        "RRWWWWRR",
        "RBBBBBBR",
        "RBBBBBBR",
        "RBBBBBBR",
        "RRWWWWRR",
        ".RRRRRR.",
        "..RRRR..",
    ]
    color_map = {
        'R': body_color,
        'W': (210, 235, 250),   # sklo
        'B': (25, 25, 30),      # karoserie/interiér
    }
    cols = len(pixel_rows[0])
    rows = len(pixel_rows)
    surf = pygame.Surface((cols * scale, rows * scale), pygame.SRCALPHA)
    for ry, row in enumerate(pixel_rows):
        for rx, ch in enumerate(row):
            if ch == '.':
                continue
            pygame.draw.rect(surf, color_map.get(ch, body_color), (rx * scale, ry * scale, scale, scale))
    # tenký tmavý obrys pro lepší čitelnost
    pygame.draw.rect(surf, (10, 10, 10), surf.get_rect(), 1)
    return surf


class PragueChunk:
    def __init__(self, chunk_x, chunk_y):
        self.chunk_x = chunk_x
        self.chunk_y = chunk_y
        
        random.seed(f"{chunk_x}_{chunk_y}")
        self.surface = pygame.Surface((CHUNK_SIZE_W, CHUNK_SIZE_H))
        self.surface.fill(COLOR_BG) 
        
        if chunk_x == -1:
            river_points = []
            for y in range(-20, CHUNK_SIZE_H + 40, 20):
                x = (CHUNK_SIZE_W // 2) + math.sin((chunk_y * CHUNK_SIZE_H + y) * 0.004) * 100
                river_points.append((x, y))
            pygame.draw.lines(self.surface, COLOR_RIVER, False, river_points, 200)

        for rx in GRID_X:
            # UPRAVENO: silnice teď mají barvu asfaltu a nastříkané pruhy místo bílé plochy
            draw_road_segment(self.surface, rx, -20, rx, CHUNK_SIZE_H + 20, ROAD_THICKNESS)
            if HAS_ROAD_TEX:
                for ty in range(0, CHUNK_SIZE_H, ROAD_THICKNESS):
                    self.surface.blit(TEXTURE_ROAD, (rx - ROAD_THICKNESS // 2, ty))
            
        for ry in GRID_Y:
            # UPRAVENO: silnice teď mají barvu asfaltu a nastříkané pruhy místo bílé plochy
            draw_road_segment(self.surface, -20, ry, CHUNK_SIZE_W + 20, ry, ROAD_THICKNESS)
            if HAS_ROAD_TEX:
                for tx in range(0, CHUNK_SIZE_W, ROAD_THICKNESS):
                    self.surface.blit(TEXTURE_ROAD, (tx, ry - ROAD_THICKNESS // 2))

        for i in range(len(GRID_X) - 1):
            for j in range(len(GRID_Y) - 1):
                # PŘIDÁNO: ve sloupci s řekou (chunk_x == -1) se nekreslí vůbec žádné budovy,
                # parky ani dlážděná výplň - řeka tak zůstane celá volná a nic do ní nezasahuje,
                # takže po ní může (spolu se silnicemi) plynule projet i loď.
                if chunk_x == -1:
                    continue

                start_x = GRID_X[i] + (ROAD_THICKNESS // 2) + 15
                end_x = GRID_X[i+1] - (ROAD_THICKNESS // 2) - 15
                start_y = GRID_Y[j] + (ROAD_THICKNESS // 2) + 15
                end_y = GRID_Y[j+1] - (ROAD_THICKNESS // 2) - 15

                skip_decor = False
                if chunk_x == 0 and chunk_y == 0 and i == 1 and j == 1:
                    skip_decor = True
                if chunk_x == 0 and chunk_y == -1:
                    skip_decor = True
                # UPRAVENO: kruhový objezd je teď vystředěný přesně na křižovatku GRID_X[1]/GRID_Y[1],
                # takže zasahuje do všech čtyř okolních bloků (i=0 nebo 1, j=0 nebo 1) - v žádném
                # z nich se proto nesmí kreslit budovy, jinak by "trčely" přes kruh.
                if (chunk_x + chunk_y) % 2 == 0 and i in (0, 1) and j in (0, 1):
                    skip_decor = True

                if skip_decor:
                    # UPRAVENO: dřív tu zůstala úplně prázdná plocha (jen barva pozadí COLOR_BG),
                    # takže to okolo silnic a objezdu vypadalo jako díra a silnice/objezd v ní
                    # jakoby "visely" bez návaznosti. Teď se tam alespoň vykreslí jednoduchá
                    # dlážděná plocha ve stejném stylu jako zbytek města, aby vše plynule navazovalo.
                    fill_rect = pygame.Rect(start_x, start_y, end_x - start_x, end_y - start_y)
                    pygame.draw.rect(self.surface, (205, 200, 190), fill_rect)
                    pygame.draw.rect(self.surface, (180, 175, 165), fill_rect, 3)
                    continue

                # UPRAVENO: parky teď tvoří jen menšinu bloků (1 ze 6 místo dřívějšího 1 ze 3),
                # takže na mapě přibylo víc bloků se zástavbou - a tím i celkově víc budov.
                if (i * j + chunk_x + chunk_y) % 6 == 0:
                    park_rect = pygame.Rect(start_x, start_y, end_x - start_x, end_y - start_y)
                    pygame.draw.rect(self.surface, COLOR_PARK, park_rect, border_radius=8)
                    for _ in range(5):
                        tx = random.randint(start_x + 10, end_x - 10)
                        ty = random.randint(start_y + 10, end_y - 10)
                        pygame.draw.circle(self.surface, (90, 140, 80), (tx, ty), random.randint(6, 12))
                else:
                    # UPRAVENO: budovy jsou teď menší a hustěji naskládané (krok 65 -> 48,
                    # velikost 45-55 -> 32-42) a mnohem méně se přeskakují (šance na "díru"
                    # klesla z 15 % na 6 %) - výsledkem je citelně víc budov po celé mapě,
                    # aniž by kterákoliv z nich zasahovala do silnic nebo řeky, protože se
                    # pořád kreslí jen uvnitř stejné bezpečné oblasti [start_x, end_x] x
                    # [start_y, end_y], která už má od silnic patřičnou rezervu.
                    building_step = 48
                    max_building_size = 42
                    for bx in range(start_x, end_x - max_building_size, building_step):
                        for by in range(start_y, end_y - max_building_size, building_step):
                            if random.random() > 0.06:
                                size = random.randint(32, max_building_size)
                                pygame.draw.rect(self.surface, (195, 190, 182), (bx + 3, by + 3, size, size))
                                pygame.draw.rect(self.surface, (235, 220, 205), (bx, by, size, size))

        if (chunk_x + chunk_y) % 2 == 0:
            # UPRAVENO: kruhový objezd se teď kreslí AŽ PO budovách (ne před nimi), takže je
            # jeho textura vždy navrch a žádná textura budovy skrz něj nemůže "prosvítat" ani
            # ho překrýt na okraji - objezd tak vždy zůstane čistě viditelný a plynule navazující
            # na silnice, které do něj vjíždí.
            draw_roundabout(self.surface, GRID_X[1], GRID_Y[1], 86, 40)

        random.seed()

class MapManager:
    def __init__(self):
        self.loaded_chunks = {}

    def get_chunk(self, cx, cy):
        key = (cx, cy)
        if key not in self.loaded_chunks:
            self.loaded_chunks[key] = PragueChunk(cx, cy)
        return self.loaded_chunks[key]

    def is_road(self, world_x, world_y, allow_river=False):
        cx = math.floor(world_x / CHUNK_SIZE_W)
        cy = math.floor(world_y / CHUNK_SIZE_H)
        rx = world_x - (cx * CHUNK_SIZE_W)
        ry = world_y - (cy * CHUNK_SIZE_H)
        
        if (cx + cy) % 2 == 0:
            dist_to_center = math.hypot(rx - GRID_X[1], ry - GRID_Y[1])
            if 40 <= dist_to_center <= 86:
                return True

        # UPRAVENO: řeka (sloupec chunk_x == -1) se teď počítá jako "silnice" JEN pro
        # vozidla, která mají allow_river=True (v praxi jen loď z garáže) - pro všechna
        # ostatní auta (hráče i AI) se řeka chová jako obyčejná neprůjezdná zeď.
        if allow_river and cx == -1:
            river_center_x = (CHUNK_SIZE_W // 2) + math.sin((cy * CHUNK_SIZE_H + ry) * 0.004) * 100
            if abs(rx - river_center_x) <= 100:
                return True

        half_road = ROAD_THICKNESS / 2
        for grid_x in GRID_X:
            if grid_x - half_road <= rx <= grid_x + half_road:
                return True
        for grid_y in GRID_Y:
            if grid_y - half_road <= ry <= grid_y + half_road:
                return True

        return False

    def draw(self, surface, cam_x, cam_y):
        start_cx = math.floor((cam_x - GAME_CENTER_X) / CHUNK_SIZE_W) - 1
        end_cx = math.floor((cam_x + GAME_CENTER_X) / CHUNK_SIZE_W) + 1
        start_cy = math.floor((cam_y - GAME_CENTER_Y) / CHUNK_SIZE_H) - 1
        end_cy = math.floor((cam_y + GAME_CENTER_Y) / CHUNK_SIZE_H) + 1

        for cx in range(start_cx, end_cx + 1):
            for cy in range(start_cy, end_cy + 1):
                chunk = self.get_chunk(cx, cy)
                screen_x = int(cx * CHUNK_SIZE_W - cam_x + GAME_CENTER_X)
                screen_y = int(cy * CHUNK_SIZE_H - cam_y + GAME_CENTER_Y)
                surface.blit(chunk.surface, (screen_x, screen_y))


# PŘIDÁNO: náhodné umístění hráče na start, ale vždy přesně na silnici.
# Místo náhodného bodu kdekoliv ve světě (což by skoro vždy skončilo ve zdi budovy)
# se náhodně vybere jedna ze známých silničních linií (svislá/vodorovná z GRID_X/GRID_Y)
# v okolí startovní oblasti a na ní náhodná pozice - to je vždy garantovaně silnice,
# navíc se to ještě ověří přes map_manager.is_road jako pojistku.
SPAWN_SEARCH_RADIUS_CHUNKS = 1  # kolik chunků od středu (0,0) na každou stranu se smí hráč zrodit


def find_random_road_spawn(map_manager):
    for _ in range(200):
        cx = random.randint(-SPAWN_SEARCH_RADIUS_CHUNKS, SPAWN_SEARCH_RADIUS_CHUNKS)
        cy = random.randint(-SPAWN_SEARCH_RADIUS_CHUNKS, SPAWN_SEARCH_RADIUS_CHUNKS)
        if random.random() < 0.5:
            local_x = random.choice(GRID_X)
            local_y = random.uniform(0, CHUNK_SIZE_H)
        else:
            local_x = random.uniform(0, CHUNK_SIZE_W)
            local_y = random.choice(GRID_Y)
        world_x = cx * CHUNK_SIZE_W + local_x
        world_y = cy * CHUNK_SIZE_H + local_y
        if map_manager.is_road(world_x, world_y):
            return world_x, world_y
    return 425.0, 375.0  # záložní bezpečná pozice, kdyby se náhodou nic nenašlo
class Particle:
    def __init__(self, x, y, color):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(-5, 5)
        self.lifetime = random.randint(15, 30)
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1

    def draw(self, surface, camera_x, camera_y):
        screen_x = int(self.x - camera_x + GAME_CENTER_X)
        screen_y = int(self.y - camera_y + GAME_CENTER_Y)
        if 0 <= screen_x <= CHUNK_SIZE_W and 0 <= screen_y <= CHUNK_SIZE_H:
            if self.lifetime > 0:
                pygame.draw.circle(surface, self.color, (screen_x, screen_y), max(1, self.lifetime // 6))

class Player:
    def __init__(self, world_x, world_y, car_config=None):
        self.world_x = float(world_x)
        self.world_y = float(world_y)
        self.radius = 12
        # UPRAVENO: rychlost a barva teď vychází z vybraného auta z garáže (obchodu);
        # bez zadání se použije základní auto z CAR_CATALOG (index 0).
        car_config = car_config or CAR_CATALOG[0]
        self.speed = PLAYER_BASE_SPEED * car_config.get("speed_mult", 1.0)
        self.color = car_config.get("color", (0, 120, 255))
        # PŘIDÁNO: lepší auta mají kratší cooldown dashe (dash_cd_mult < 1.0)
        self.dash_cooldown_frames = max(1, int(PLAYER_DASH_COOLDOWN_FRAMES * car_config.get("dash_cd_mult", 1.0)))

        # PŘIDÁNO: jen loď (is_boat=True v CAR_CATALOG) smí vjíždět do řeky - všechna
        # ostatní auta se o ni chovají jako o obyčejnou zeď.
        self.is_boat = car_config.get("is_boat", False)

        # PŘIDÁNO: akcelerace - hráč se nerozjíždí/nebrzdí okamžitě, ale postupně
        self.vel_x = 0.0
        self.vel_y = 0.0

        # PŘIDÁNO: dash (rychlý výpad) - aktivuje se klávesou R, cooldown 3s (podle auta i méně)
        self.dash_timer = 0        # kolik snímků ještě běží aktivní dash
        self.dash_cooldown = 0     # kolik snímků zbývá, než bude dash znovu použitelný
        self.dash_dir = (0.0, 0.0)

        # PŘIDÁNO: cooldown pro pokládání bodců (klávesa F)
        self.spike_cooldown = 0

        # PŘIDÁNO: systém životů - většina aut má jen 1 život (náraz AI auta = konec),
        # ale některá auta (např. autobus, loď, tank z kategorie "těžká vozidla", nebo
        # Festival Car z kategorie "speciální") mají "lives" > 1 v CAR_CATALOG a vydrží
        # víc nárazů, než skutečně dojde ke game overu.
        self.max_lives = car_config.get("lives", 1)
        self.lives = self.max_lives
        # PŘIDÁNO: krátká neporazitelnost po nárazu, který nestál poslední život -
        # bez toho by hráč mohl během jednoho snímku přijít o všechny životy najednou
        # kvůli více AI autům v těsné blízkosti.
        self.invuln_timer = 0

        # PŘIDÁNO: úhel, kterým je hráč aktuálně natočený (podle posledního směru pohybu) -
        # používá se pro vykreslení pixel-art autíčka správným směrem
        self.face_angle = math.pi / 2  # výchozí natočení "nahoru"

        # PŘIDÁNO: pixel-art textura autíčka hráče, vytvořená přímo v kódu
        self.car_surface = build_pixel_car_surface(self.color)

        # PŘIDÁNO: podpora speciálních vozidel z kategorie "SPECIÁLNÍ" -
        # self.special drží klíčové slovo ("duck" / "umbrella" / "festival" / None).
        self.special = car_config.get("special")
        # Gumová kachna: jakýkoliv náraz do zdi/mimo silnici = okamžitá smrt.
        self.dies_on_wall = (self.special == "duck")
        # Kouzelný deštník: po dashi na chvíli "letí vzduchem" - ignoruje kolize se
        # silnicí/budovami/řekou a je nezranitelný vůči AI autům.
        self.airborne_timer = 0
        # PŘIDÁNO: příznak nastavený v tomto snímku, pokud právě došlo k nárazu do zdi
        # (využívá ho hlavní smyčka k vyhodnocení smrti gumové kachny).
        self.wall_crash = False

    def trigger_dash(self, dir_x, dir_y):
        """Pokusí se aktivovat dash daným směrem, pokud právě neběží cooldown."""
        if self.dash_cooldown <= 0:
            self.dash_timer = PLAYER_DASH_DURATION_FRAMES
            self.dash_cooldown = self.dash_cooldown_frames
            self.dash_dir = (dir_x, dir_y)
            # PŘIDÁNO: kouzelný deštník při dashi navíc vzlétne na 1 sekundu do vzduchu -
            # po tuto dobu ho nemůže dostihnout žádné AI auto a přeletí i překážky.
            if self.special == "umbrella":
                self.airborne_timer = FPS

    def move(self, keys, map_manager):
        dx, dy = 0, 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy = 1

        if dx != 0 and dy != 0:
            dx *= 0.707; dy *= 0.707

        # PŘIDÁNO: cooldown dashe i bodců postupně odpočítává každý snímek
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
        if self.spike_cooldown > 0:
            self.spike_cooldown -= 1
        if self.invuln_timer > 0:
            self.invuln_timer -= 1

        if self.dash_timer > 0:
            # PŘIDÁNO: během dashe se hráč pohybuje pevnou vysokou rychlostí ve směru dashe -
            # normální akcelerace se na tuto chvíli přeskočí
            self.dash_timer -= 1
            self.vel_x = self.dash_dir[0] * PLAYER_DASH_SPEED
            self.vel_y = self.dash_dir[1] * PLAYER_DASH_SPEED
        else:
            # PŘIDÁNO: normální akcelerace/decelerace směrem k cílové rychlosti podle vstupu z klávesnice
            target_vx = dx * self.speed
            target_vy = dy * self.speed
            self.vel_x = approach_value(self.vel_x, target_vx, PLAYER_ACCEL)
            self.vel_y = approach_value(self.vel_y, target_vy, PLAYER_ACCEL)

        # PŘIDÁNO: pokud se hráč reálně pohybuje, aktualizuje se úhel natočení (pro vykreslení autíčka)
        if abs(self.vel_x) > 0.05 or abs(self.vel_y) > 0.05:
            self.face_angle = math.atan2(-self.vel_y, self.vel_x)

        new_x = self.world_x + self.vel_x
        new_y = self.world_y + self.vel_y

        self.wall_crash = False  # PŘIDÁNO: reset příznaku nárazu do zdi na začátku každého snímku

        if self.airborne_timer > 0:
            # PŘIDÁNO: kouzelný deštník ve vzduchu ignoruje veškeré kolize (silnice, budovy,
            # řeka) - jednoduše "přeletí" nad vším, dokud let netrvá
            self.airborne_timer -= 1
            self.world_x = new_x
            self.world_y = new_y
        else:
            # UPRAVENO: řeka teď propouští jen loď (allow_river=self.is_boat) - všechna
            # ostatní auta se o ni chovají jako o zeď, i kdyby ji dřív brala jako silnici.
            if map_manager.is_road(new_x, self.world_y, allow_river=self.is_boat):
                self.world_x = new_x
            else:
                # PŘIDÁNO: gumová kachna umírá na jakýkoliv skutečný náraz do zdi
                if self.dies_on_wall and abs(self.vel_x) > 0.5:
                    self.wall_crash = True
                self.vel_x = 0.0  # PŘIDÁNO: náraz do zdi zastaví rychlost na dané ose
            if map_manager.is_road(self.world_x, new_y, allow_river=self.is_boat):
                self.world_y = new_y
            else:
                # PŘIDÁNO: gumová kachna umírá na jakýkoliv skutečný náraz do zdi
                if self.dies_on_wall and abs(self.vel_y) > 0.5:
                    self.wall_crash = True
                self.vel_y = 0.0  # PŘIDÁNO

    def draw(self, surface, alpha_surface):
        center_x, center_y = GAME_CENTER_X, GAME_CENTER_Y
        pygame.draw.circle(alpha_surface, (*self.color, 50), (center_x, center_y), self.radius + 8)
        # PŘIDÁNO: místo obyčejného kolečka se vykresluje pixel-art autíčko natočené
        # ve směru pohybu (-90°, protože základní sprite má přední část nahoru)
        rotated_car = pygame.transform.rotate(self.car_surface, math.degrees(self.face_angle) - 90)
        car_rect = rotated_car.get_rect(center=(center_x, center_y))
        surface.blit(rotated_car, car_rect.topleft)

class SmartAICar:
    def __init__(self, world_x, world_y):
        self.world_x = float(world_x)
        self.world_y = float(world_y)
        brand = random.choice(AI_CAR_BRANDS)
        self.name = brand["name"]
        self.color = brand["color"]
        self.size = 24
        self.speed = AI_BASE_SPEED  # UPRAVENO: základní rychlost - dál se navyšuje podle obtížnosti (skóre)
        self.angle = 0.0

        # PŘIDÁNO: každé auto je "přiřazené" k jednomu genomu (mozku) ve sdílené populaci
        self.slot = random.randrange(AI_POPULATION.size)
        self.prev_distance = None  # PŘIDÁNO: pro sledování, jestli se auto přibližuje nebo vzdaluje

        # PŘIDÁNO: akcelerace - aktuální rychlost se plynule přibližuje k té, kterou chce síť
        self.current_speed = 0.0

        # PŘIDÁNO: zamrznutí (po bodcích nebo nárazu do zdi na plnou rychlost) - kolik snímků
        # ještě auto nemůže hýbat
        self.freeze_timer = 0

        # PŘIDÁNO: historie polohy pro detekci kroužení/zaseknutí na místě
        self.stuck_timer = 0
        self.pos_history = []

        # FUNKCE: Každé auto si při vytvoření náhodně vytáhne jeden z načtených obrázků ze seznamu
        if AI_CAR_TEXTURES:
            self.assigned_texture = random.choice(AI_CAR_TEXTURES)
        else:
            self.assigned_texture = None

    def update(self, player_x, player_y, map_manager, placed_spikes):
        # PŘIDÁNO: pokud je auto zmražené (bodce nebo náraz do zdi na plnou rychlost),
        # přeskočí se veškerý pohyb i rozhodování sítě, dokud čas zmražení nevyprší.
        if self.freeze_timer > 0:
            self.freeze_timer -= 1
            self.current_speed = 0.0
            return

        dx = player_x - self.world_x
        dy = player_y - self.world_y
        distance = math.hypot(dx, dy)

        if distance > 0:
            # PŮVODNÍ VÝPOČET (zachován) - úhel k hráči ve stejné konvenci jako předtím
            target_angle = math.atan2(-dy, dx)

            # PŘIDÁNO: místo přímého "target_angle -> self.angle" tahu necháme
            # rozhodnout neuronovou síť daného auta (self.slot určuje, který genom používá).
            rel_angle = target_angle - self.angle
            rel_x = math.cos(rel_angle)
            rel_y = math.sin(rel_angle)

            look_ahead = 45
            def road_probe(angle_offset):
                probe_x = self.world_x + math.cos(self.angle + angle_offset) * look_ahead
                probe_y = self.world_y - math.sin(self.angle + angle_offset) * look_ahead
                return 1.0 if map_manager.is_road(probe_x, probe_y) else -1.0

            inputs = [
                rel_x,
                rel_y,
                min(distance, 900) / 900.0,
                road_probe(0.0),
                road_probe(-0.6),
                road_probe(0.6),
            ]

            weights = AI_POPULATION.get_weights(self.slot)
            turn, speed_mult = ai_think(weights, inputs)

            desired_angle = self.angle + turn * 0.35
            self.angle += (desired_angle - self.angle) * 0.2

            target_speed = self.speed * max(0.3, min(1.3, 0.8 + speed_mult * 0.5))
            # UPRAVENO: rychlost se teď plynule akceleruje/decceleruje k cílové hodnotě,
            # místo aby se každý snímek nastavila okamžitě (proto se ukládá do self.current_speed).
            self.current_speed = approach_value(self.current_speed, target_speed, AI_ACCEL)

            step_x = math.cos(self.angle) * self.current_speed
            step_y = -math.sin(self.angle) * self.current_speed

            moved_x = moved_y = False
            if map_manager.is_road(self.world_x + step_x, self.world_y):
                self.world_x += step_x
                moved_x = True
            if map_manager.is_road(self.world_x, self.world_y + step_y):
                self.world_y += step_y
                moved_y = True

            # PŘIDÁNO: pokud auto narazí do zdi na obou osách zároveň (úplně se zastaví),
            # a jelo přitom skoro na plnou rychlost, dostane navíc 2sekundové zamrznutí.
            if not moved_x and not moved_y and self.current_speed >= self.speed * AI_FULL_SPEED_CRASH_RATIO:
                self.freeze_timer = AI_WALL_CRASH_FREEZE_FRAMES
                self.current_speed = 0.0

            # UPRAVENO: bodce už nejsou pevnou součástí mapy, ale hráč je pokládá sám (klávesa F).
            # Pokud auto vjede do dosahu některého z aktuálně položených bodců, zamrzne na 2s
            # (pokud už mělo delší zamrznutí z nárazu do zdi, ponechá se to delší) a bodec se
            # zároveň spotřebuje - zmizí ze země, takže dalším autům už v cestě nestojí.
            hit_spike = None
            for spike in placed_spikes:
                spike_x, spike_y = spike
                if math.hypot(self.world_x - spike_x, self.world_y - spike_y) <= SPIKE_RADIUS:
                    hit_spike = spike
                    break
            if hit_spike is not None:
                self.freeze_timer = max(self.freeze_timer, SPIKE_FREEZE_FRAMES)
                if hit_spike in placed_spikes:
                    placed_spikes.remove(hit_spike)

            # UPRAVENO: náraz do okraje silnice = středně velký trest.
            # Padá i tehdy, když je zablokovaná jen jedna osa (sklouznutí podél zdi),
            # ne jen když auto úplně zůstane stát.
            if not moved_x or not moved_y:
                AI_POPULATION.add_fitness(self.slot, AI_OFFROAD_HIT_PENALTY)

            # UPRAVENO: odměna/trest podle směru vůči hráči -
            # jede-li auto k hráči (vzdálenost klesá) = středně velká odměna,
            # jede-li auto od hráče (vzdálenost roste) = velký trest.
            if self.prev_distance is not None:
                approached_by = self.prev_distance - distance  # kladné = blíž, záporné = dál
                if approached_by >= 0:
                    AI_POPULATION.add_fitness(self.slot, approached_by * AI_APPROACH_REWARD_SCALE)
                else:
                    AI_POPULATION.add_fitness(self.slot, approached_by * AI_RETREAT_PENALTY_SCALE)
            self.prev_distance = distance

            # PŘIDÁNO: detekce dlouhého opakování stejného pohybu / kroužení na místě.
            # Pravidelně (každou sekundu) si auto uloží svou polohu; pokud se za posledních
            # AI_STUCK_HISTORY_LEN sekund reálně nikam neposunulo (kouká na místě nebo
            # jen krouží v malém okruhu), dostane trest.
            self.stuck_timer += 1
            if self.stuck_timer >= AI_STUCK_SAMPLE_INTERVAL:
                self.stuck_timer = 0
                self.pos_history.append((self.world_x, self.world_y))
                if len(self.pos_history) > AI_STUCK_HISTORY_LEN:
                    self.pos_history.pop(0)
                if len(self.pos_history) == AI_STUCK_HISTORY_LEN:
                    oldest_x, oldest_y = self.pos_history[0]
                    net_progress = math.hypot(self.world_x - oldest_x, self.world_y - oldest_y)
                    if net_progress < AI_STUCK_DISTANCE_THRESHOLD:
                        AI_POPULATION.add_fitness(self.slot, AI_STUCK_PENALTY)

    def draw(self, surface, camera_x, camera_y):
        screen_x = int(self.world_x - camera_x + GAME_CENTER_X)
        screen_y = int(self.world_y - camera_y + GAME_CENTER_Y)
        
        # Pokud má auto přiřazenou texturu, vykreslí se s rotací za hráčem
        if self.assigned_texture:
            rotated_car = pygame.transform.rotate(self.assigned_texture, math.degrees(self.angle))
            new_rect = rotated_car.get_rect(center=(screen_x, screen_y))
            surface.blit(rotated_car, new_rect.topleft)
        else:
            # UPRAVENO: záložní vektorové auto vypadá teď víc jako skutečné autíčko -
            # tmavý obrys karoserie, barevný lak, přední sklo a zadní světla.
            car_w, car_h = self.size * 1.6, self.size * 0.95
            car_rect_surf = pygame.Surface((int(car_w), int(car_h)), pygame.SRCALPHA)
            pygame.draw.rect(car_rect_surf, (20, 20, 20), (0, 0, car_w, car_h), border_radius=6)
            pygame.draw.rect(car_rect_surf, self.color, (2, 2, car_w - 4, car_h - 4), border_radius=5)
            # přední sklo (vpravo, protože úhel 0 = auto jede doprava)
            pygame.draw.rect(car_rect_surf, (210, 235, 250),
                              (car_w * 0.58, 3, car_w * 0.30, car_h - 6), border_radius=3)
            # zadní světla (vlevo)
            pygame.draw.circle(car_rect_surf, (255, 60, 60), (4, 4), 2)
            pygame.draw.circle(car_rect_surf, (255, 60, 60), (4, int(car_h) - 4), 2)
            rotated_car = pygame.transform.rotate(car_rect_surf, math.degrees(self.angle))
            new_rect = rotated_car.get_rect(center=(screen_x, screen_y))
            surface.blit(rotated_car, new_rect.topleft)

class AnimatedCrashScene:
    def __init__(self):
        self.center_x = 425.0
        self.center_y = -375.0
        self.font = pygame.font.SysFont("Consolas", 14, bold=True)
        
        self.triggered = False
        self.finished = False
        self.timer = 0
        
        self.merc_x = self.center_x - 300
        self.merc_y = self.center_y
        self.amb_x = self.center_x
        self.amb_y = self.center_y + 300
        
        self.amb_angle = 90.0
        self.bubble_text = "Pan Kaficko: To je krasny klidny den v Praze..."

    def update(self, player_x, player_y, particles):
        if not self.triggered and math.hypot(player_x - self.center_x, player_y - self.center_y) < 300:
            self.triggered = True

        if self.triggered and not self.finished:
            self.timer += 1
            if self.timer < 50:
                self.merc_x += 5.0
                self.amb_y -= 5.0
                self.bubble_text = "Pan Kaficko: Hele, kam ten Mercedes tak leti?!"
            elif self.timer == 50:
                self.merc_x = self.center_x - 10
                self.amb_y = self.center_y
                self.bubble_text = "* BUM !!! *"
                for _ in range(30):
                    particles.append(Particle(self.center_x, self.center_y, (255, 200, 0)))
            elif 50 < self.timer < 100:
                self.amb_x += 2.0
                self.amb_y -= 1.0
                self.amb_angle += 3.6
                self.bubble_text = "Pan Kaficko: Pane boze! Sanitka je na boku!"
                if self.timer % 3 == 0:
                    particles.append(Particle(self.amb_x, self.amb_y, (230, 230, 230)))
            elif self.timer >= 100:
                self.bubble_text = "Pan Kaficko: Tady jsi v bezpeci, odpocin si!"
                self.finished = True

    def draw(self, surface, camera_x, camera_y):
        ex = int(self.center_x - camera_x + GAME_CENTER_X)
        ey = int(self.center_y - camera_y + GAME_CENTER_Y)
        
        pygame.draw.circle(surface, (120, 70, 40), (ex - 50, ey + 50), 8)
        
        txt = self.font.render(self.bubble_text, True, (20, 20, 20))
        pygame.draw.rect(surface, (255, 255, 255), (ex - 120, ey - 70, len(self.bubble_text)*8 + 10, 25), border_radius=5)
        surface.blit(txt, (ex - 110, ey - 65))

        mx = int(self.merc_x - camera_x + GAME_CENTER_X)
        my = int(self.merc_y - camera_y + GAME_CENTER_Y)
        ax = int(self.amb_x - camera_x + GAME_CENTER_X)
        ay = int(self.amb_y - camera_y + GAME_CENTER_Y)

        pygame.draw.rect(surface, (15, 15, 15), (mx - 20, my - 10, 35, 18), border_radius=3)
        
        amb_surf = pygame.Surface((40, 22), pygame.SRCALPHA)
        pygame.draw.rect(amb_surf, (240, 220, 30), (0, 0, 40, 22), border_radius=4)
        pygame.draw.rect(amb_surf, (255, 30, 30), (10, 0, 5, 22)) 
        pygame.draw.circle(amb_surf, (0, 150, 255), (25, 11), 4)
        
        rot_amb = pygame.transform.rotate(amb_surf, self.amb_angle)
        amb_rect = rot_amb.get_rect(center=(ax, ay))
        surface.blit(rot_amb, amb_rect.topleft)
# ==========================================
# 3. HLAVNÍ HERNÍ SMYČKA, DETAILNÍ MINIMAPA A UI
# ==========================================
def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Deadly Traffic s dynamickými AI texturami")
    clock = pygame.time.Clock()

    font_main = pygame.font.SysFont("Arial", 16, bold=True)
    font_title = pygame.font.SysFont("Arial", 22, bold=True)
    font_small = pygame.font.SysFont("Arial", 14)  # PŘIDÁNO: menší písmo pro karty aut v garáži

    map_manager = MapManager()

    # PŘIDÁNO: perzistentní mince a koupená/vybraná auta hráče (garáž/obchod)
    player_data = load_player_data()
    main_menu_play_rect, main_menu_garage_rect, main_menu_shop_rect, main_menu_exit_rect = compute_main_menu_layout()
    menu_back_rect = pygame.Rect(60, SCREEN_HEIGHT - 90, 220, 55)  # PŘIDÁNO: tlačítko návratu do hlavního menu

    # UPRAVENO: hra teď začíná v hlavním menu se třemi volbami (Hrát / Garáž / Obchod)
    state = "main_menu"

    # PŘIDÁNO: aktuální posun scrollování v garáži a v obchodě (nezávisle na sobě) -
    # v obou obrazovkách jde teď scrollovat kolečkem myši, protože aut je víc, než se
    # jich vejde najednou na obrazovku.
    garage_scroll_y = 0
    shop_scroll_y = 0

    player = None
    crash_scene = None
    enemies = []
    particles = []
    placed_spikes = []  # PŘIDÁNO: bodce, které si hráč sám pokládá klávesou F, jako [x, y]

    score = 0
    high_score = load_high_score()  # PŘIDÁNO: nejvyšší skóre se načte z uloženého souboru
    game_over = False
    game_over_timer = 0  # PŘIDÁNO: počítadlo snímků od bouračky pro automatický restart
    spawn_timer = 0
    ai_gen_timer = 0  # PŘIDÁNO: počítadlo snímků pro evoluci AI populace

    AUTO_RESTART_DELAY_FRAMES = FPS * 3  # PŘIDÁNO: za kolik snímků (zde 3 sekundy) po bouračce se hra sama restartuje

    btn_x = CHUNK_SIZE_W + 20
    btn_y = SCREEN_HEIGHT - 70
    btn_w = UI_WIDTH - 40
    btn_h = 45
    exit_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    # PŘIDÁNO: sledování předchozího stavu, aby se hudba v menu spouštěla/zastavovala
    # jen při přechodu mezi "v menu" a "ve hře", ne úplně pořád dokola každý snímek.
    MENU_STATES = ("main_menu", "garage", "shop")
    prev_state = None

    def start_new_run():
        """PŘIDÁNO: spustí novou jízdu s aktuálně vybraným autem z garáže -
        používá se jak při prvním kliknutí na HRÁT, tak při restartu po bouračce."""
        nonlocal player, crash_scene, enemies, particles, placed_spikes
        nonlocal score, spawn_timer, ai_gen_timer, game_over, game_over_timer
        selected_car = CAR_CATALOG[player_data["selected"]]
        player = Player(*find_random_road_spawn(map_manager), car_config=selected_car)
        crash_scene = AnimatedCrashScene()
        enemies = [SmartAICar(150.0, 150.0)]
        particles = []
        placed_spikes = []
        score = 0
        spawn_timer = 0
        ai_gen_timer = 0
        game_over = False
        game_over_timer = 0

    while True:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_ai_population(AI_POPULATION)  # PŘIDÁNO: uložit AI paměť před ukončením hry
                save_high_score(high_score)  # PŘIDÁNO: uložit nejvyšší skóre před ukončením hry
                save_player_data(player_data)  # PŘIDÁNO: uložit mince a auta před ukončením hry
                pygame.quit()
                sys.exit()

            # PŘIDÁNO: klávesa ESC ukončí hru, pokud jsi právě v hlavním menu, garáži nebo obchodě
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and state in ("main_menu", "garage", "shop"):
                save_ai_population(AI_POPULATION)
                save_high_score(high_score)
                save_player_data(player_data)
                pygame.quit()
                sys.exit()

            # PŘIDÁNO: scrollování obsahu garáže/obchodu kolečkem myši - směr dolů (event.y < 0)
            # posouvá obsah nahoru (zvyšuje scroll), rozsah je vždy ořezán na 0..max_scroll.
            if event.type == pygame.MOUSEWHEEL:
                if state == "garage":
                    max_scroll = compute_shop_max_scroll("garage", player_data)
                    garage_scroll_y = max(0, min(max_scroll, garage_scroll_y - event.y * 60))
                elif state == "shop":
                    max_scroll = compute_shop_max_scroll("shop", player_data)
                    shop_scroll_y = max(0, min(max_scroll, shop_scroll_y - event.y * 60))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "main_menu":
                    # UPRAVENO: hlavní menu - čtyři volby Hrát / Garáž / Obchod / Ukončit hru
                    if main_menu_play_rect.collidepoint(mouse_pos):
                        start_new_run()
                        state = "playing"
                    elif main_menu_garage_rect.collidepoint(mouse_pos):
                        garage_scroll_y = 0  # PŘIDÁNO: při vstupu do garáže se scroll vrátí na začátek
                        state = "garage"
                    elif main_menu_shop_rect.collidepoint(mouse_pos):
                        shop_scroll_y = 0  # PŘIDÁNO: při vstupu do obchodu se scroll vrátí na začátek
                        state = "shop"
                    elif main_menu_exit_rect.collidepoint(mouse_pos):
                        save_ai_population(AI_POPULATION)
                        save_high_score(high_score)
                        save_player_data(player_data)
                        pygame.quit()
                        sys.exit()
                elif state == "garage":
                    # UPRAVENO: v garáži se zobrazují jen vlastněná auta, rozdělená do sekcí
                    # (BĚŽNÁ AUTA / TĚŽKÁ VOZIDLA / SPECIÁLNÍ) - klik na kartu = výběr,
                    # klik na HRÁT = start jízdy, klik na ZPĚT = návrat do hlavního menu.
                    # PŘIDÁNO: kliky na karty se teď posouvají o aktuální scroll a platí jen
                    # uvnitř viditelné (ořezané) oblasti obsahu, aby scrollnutá karta omylem
                    # nezasáhla do tlačítek HRÁT/ZPĚT.
                    visible_indices = get_shop_visible_indices("garage", player_data)
                    card_rects, _headers, play_rect, _content_bottom = compute_shop_layout(visible_indices)
                    if SHOP_CONTENT_TOP <= mouse_pos[1] <= SHOP_CONTENT_BOTTOM:
                        for idx in visible_indices:
                            rect = card_rects[idx].move(0, -garage_scroll_y)
                            if rect.collidepoint(mouse_pos):
                                player_data["selected"] = idx
                                save_player_data(player_data)
                    if play_rect.collidepoint(mouse_pos):
                        start_new_run()
                        state = "playing"
                    elif menu_back_rect.collidepoint(mouse_pos):
                        state = "main_menu"
                elif state == "shop":
                    # UPRAVENO: v obchodě se zobrazují všechna auta z katalogu, rozdělená
                    # do sekcí (BĚŽNÁ AUTA / TĚŽKÁ VOZIDLA / SPECIÁLNÍ) - klik na nekoupenou kartu =
                    # pokus o koupi, klik na ZPĚT = návrat do hlavního menu.
                    # PŘIDÁNO: stejně jako v garáži se kliky posouvají o aktuální scroll a
                    # platí jen uvnitř viditelné oblasti obsahu.
                    visible_indices = get_shop_visible_indices("shop", player_data)
                    card_rects, _headers, _play_rect, _content_bottom = compute_shop_layout(visible_indices)
                    if SHOP_CONTENT_TOP <= mouse_pos[1] <= SHOP_CONTENT_BOTTOM:
                        for idx in visible_indices:
                            rect = card_rects[idx].move(0, -shop_scroll_y)
                            if rect.collidepoint(mouse_pos):
                                car = CAR_CATALOG[idx]
                                if idx not in player_data["owned"] and player_data["coins"] >= car["price"]:
                                    player_data["coins"] -= car["price"]
                                    player_data["owned"].append(idx)
                                    save_player_data(player_data)
                    if menu_back_rect.collidepoint(mouse_pos):
                        state = "main_menu"
                elif state == "playing":
                    if exit_button_rect.collidepoint(mouse_pos):
                        save_ai_population(AI_POPULATION)  # PŘIDÁNO: totéž pro tlačítko "UKONČIT HRU"
                        save_high_score(high_score)  # PŘIDÁNO
                        save_player_data(player_data)  # PŘIDÁNO
                        pygame.quit()
                        sys.exit()

            if state == "playing":
                if event.type == pygame.KEYDOWN and game_over:
                    # UPRAVENO: restart po smrti funguje na R i na MEZERNÍK; M vrátí do hlavního menu
                    if event.key in (pygame.K_r, pygame.K_SPACE):
                        start_new_run()
                    elif event.key == pygame.K_m:
                        state = "main_menu"

                # UPRAVENO: dash je teď na klávese R (jede ve směru, kterým se hráč právě pohybuje,
                # nebo ve směru, kterým je naposledy natočený, pokud zrovna nestojí) a bodce se
                # pokládají na aktuální pozici klávesou F.
                if event.type == pygame.KEYDOWN and not game_over:
                    if event.key == pygame.K_r:
                        cur_keys = pygame.key.get_pressed()
                        ddx, ddy = 0.0, 0.0
                        if cur_keys[pygame.K_LEFT] or cur_keys[pygame.K_a]: ddx = -1.0
                        if cur_keys[pygame.K_RIGHT] or cur_keys[pygame.K_d]: ddx = 1.0
                        if cur_keys[pygame.K_UP] or cur_keys[pygame.K_w]: ddy = -1.0
                        if cur_keys[pygame.K_DOWN] or cur_keys[pygame.K_s]: ddy = 1.0
                        if ddx != 0.0 and ddy != 0.0:
                            ddx *= 0.707; ddy *= 0.707
                        if ddx == 0.0 and ddy == 0.0:
                            # PŘIDÁNO: pokud hráč zrovna nemačká žádný směr, dash vyrazí ve směru,
                            # kam je autíčko naposledy natočené
                            ddx = math.cos(player.face_angle)
                            ddy = -math.sin(player.face_angle)
                        player.trigger_dash(ddx, ddy)
                    elif event.key == pygame.K_f:
                        if player.spike_cooldown <= 0:
                            placed_spikes.append([player.world_x, player.world_y])
                            player.spike_cooldown = SPIKE_PLACE_COOLDOWN_FRAMES

        # PŘIDÁNO: hudba hraje, dokud je hráč v jakékoli menu obrazovce (hlavní menu,
        # garáž, obchod), a zastaví se, jakmile začne samotná jízda.
        if HAS_MENU_MUSIC:
            if state in MENU_STATES and prev_state not in MENU_STATES:
                pygame.mixer.music.play(-1)
            elif state not in MENU_STATES and prev_state in MENU_STATES:
                pygame.mixer.music.stop()
        prev_state = state

        if state == "main_menu":
            # PŘIDÁNO: hlavní menu se třemi volbami - Hrát / Garáž / Obchod
            draw_main_menu(screen, font_title, font_main, player_data, mouse_pos,
                           main_menu_play_rect, main_menu_garage_rect, main_menu_shop_rect, main_menu_exit_rect)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        if state == "garage":
            # UPRAVENO: garáž zobrazuje jen vlastněná auta (rozdělená do sekcí), umožňuje
            # výběr + start jízdy a jde v ní scrollovat kolečkem myši (garage_scroll_y)
            draw_shop_menu(screen, font_title, font_main, font_small, player_data, mouse_pos,
                           mode="garage", back_rect=menu_back_rect, scroll_y=garage_scroll_y)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        if state == "shop":
            # PŘIDÁNO: obchod zobrazuje všechna auta z katalogu (rozdělená do sekcí
            # BĚŽNÁ AUTA / TĚŽKÁ VOZIDLA / SPECIÁLNÍ), umožňuje koupi a jde v něm scrollovat
            # kolečkem myši (shop_scroll_y)
            draw_shop_menu(screen, font_title, font_main, font_small, player_data, mouse_pos,
                           mode="shop", back_rect=menu_back_rect, scroll_y=shop_scroll_y)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        # PŘIDÁNO: obtížnost roste s dosaženým skóre v aktuálním běhu - za každých 100 bodů
        # se AI auta zrychlí o 0.1 a smí jich najednou jezdit o jedno víc.
        displayed_score = score // 10
        difficulty_tier = difficulty_tier_for_score(displayed_score)
        current_ai_speed = AI_BASE_SPEED + difficulty_tier * AI_SPEED_PER_TIER
        current_max_enemies = AI_SPAWN_CAP_BASE + difficulty_tier

        if not game_over:
            keys = pygame.key.get_pressed()
            player.move(keys, map_manager)

            # PŘIDÁNO: gumová kachna umírá okamžitě na jakýkoliv náraz do zdi/mimo silnici -
            # kontroluje se hned po pohybu hráče, ať se to vyhodnotí ve stejném snímku.
            if player.wall_crash and not game_over:
                game_over = True
                player_data["coins"] += displayed_score // 10
                save_player_data(player_data)
                for _ in range(40):
                    particles.append(Particle(player.world_x, player.world_y, COLOR_DANGER))

            crash_scene.update(player.world_x, player.world_y, particles)
            in_safe_zone = crash_scene.triggered and not crash_scene.finished

            if not in_safe_zone and not game_over:
                spawn_timer += 1
                if spawn_timer > 90 and len(enemies) < current_max_enemies:  # UPRAVENO: strop podle obtížnosti
                    spawn_timer = 0
                    sx = player.world_x + random.choice([-500, 500])
                    sy = player.world_y + random.choice([-500, 500])
                    if map_manager.is_road(sx, sy):
                        enemies.append(SmartAICar(sx, sy))

                for enemy in enemies:
                    enemy.speed = current_ai_speed  # UPRAVENO: rychlost AI se zvyšuje i za jízdy podle obtížnosti
                    enemy.update(player.world_x, player.world_y, map_manager, placed_spikes)
                    if random.random() < 0.1 and enemy.freeze_timer <= 0:  # PŘIDÁNO: zmražené auto negeneruje částice
                        particles.append(Particle(enemy.world_x, enemy.world_y, (160, 160, 160)))

                    dist = math.hypot(player.world_x - enemy.world_x, player.world_y - enemy.world_y)
                    # UPRAVENO: náraz se teď počítá i s životy hráče (viz Player.lives) -
                    # AI auto pokaždé dostane svou velkou odměnu za zásah, ale game over
                    # (a proměna skóre na mince) nastane až po vyčerpání všech životů.
                    # invuln_timer chrání hráče před tím, aby v jednom snímku přišel
                    # o víc životů najednou kvůli více blízkým AI autům. airborne_timer
                    # (kouzelný deštník za letu) dělá hráče dočasně zcela nezranitelným.
                    if (dist < (player.radius + enemy.size / 2) and not game_over
                            and player.invuln_timer <= 0 and player.airborne_timer <= 0):
                        AI_POPULATION.add_fitness(enemy.slot, AI_CRASH_INTO_PLAYER_REWARD)  # UPRAVENO: velký bonus za dostižení hráče
                        enemy.freeze_timer = max(enemy.freeze_timer, AI_WALL_CRASH_FREEZE_FRAMES)  # PŘIDÁNO: AI se po nárazu na chvíli zastaví
                        player.lives -= 1
                        for _ in range(25):
                            particles.append(Particle(player.world_x, player.world_y, COLOR_DANGER))
                        if player.lives <= 0:
                            game_over = True
                            # UPRAVENO: skóre dosažené v tomto běhu se převede na mince do garáže -
                            # teď platí kurz 1 mince za 10 bodů zobrazeného skóre (displayed_score).
                            player_data["coins"] += displayed_score // 10
                            save_player_data(player_data)
                            for _ in range(40):
                                particles.append(Particle(player.world_x, player.world_y, COLOR_DANGER))
                        else:
                            # PŘIDÁNO: přišel jen o jeden život (např. autobus, Festival Car) - krátká
                            # neporazitelnost, ať hned zase nenarazí do stejného/dalšího auta.
                            player.invuln_timer = FPS * 2
                score += 1
                # UPRAVENO: nejvyšší skóre se teď při zlepšení rovnou ukládá na disk,
                # takže se nezapomene ani po zavření hry.
                new_high = max(high_score, score // 10)
                if new_high > high_score:
                    high_score = new_high
                    save_high_score(high_score)

                # PŘIDÁNO: po uplynutí jedné generace proběhne evoluce populace AI mozků
                ai_gen_timer += 1
                if ai_gen_timer >= AI_GENERATION_FRAMES:
                    AI_POPULATION.evolve()
                    save_ai_population(AI_POPULATION)  # PŘIDÁNO: uložit pokrok na disk po každé generaci
                    ai_gen_timer = 0

            for p in particles:
                p.update()
            particles = [p for p in particles if p.lifetime > 0]
        else:
            # PŘIDÁNO: automatický restart hry po bouračce, bez nutnosti mačkat klávesu
            game_over_timer += 1
            if game_over_timer >= AUTO_RESTART_DELAY_FRAMES:
                start_new_run()

        camera_x = player.world_x
        camera_y = player.world_y

        # --- VYKRESLENÍ HERNÍ PLOCHY ---
        screen.fill((40, 45, 50))
        game_surface = pygame.Surface((CHUNK_SIZE_W, CHUNK_SIZE_H))

        map_manager.draw(game_surface, camera_x, camera_y)

        # PŘIDÁNO: vykreslení všech aktuálně položených bodců hráče
        for spike_x, spike_y in placed_spikes:
            sx = int(spike_x - camera_x + GAME_CENTER_X)
            sy = int(spike_y - camera_y + GAME_CENTER_Y)
            if -50 <= sx <= CHUNK_SIZE_W + 50 and -50 <= sy <= CHUNK_SIZE_H + 50:
                draw_spike_trap(game_surface, sx, sy)

        crash_scene.draw(game_surface, camera_x, camera_y)

        for p in particles:
            p.draw(game_surface, camera_x, camera_y)

        alpha_surface = pygame.Surface((CHUNK_SIZE_W, CHUNK_SIZE_H), pygame.SRCALPHA)
        player.draw(game_surface, alpha_surface)
        game_surface.blit(alpha_surface, (0, 0))

        if not (crash_scene.triggered and not crash_scene.finished):
            for enemy in enemies:
                enemy.draw(game_surface, camera_x, camera_y)

        screen.blit(game_surface, (0, 0))

        # --- UI INFO PANEL ---
        ui_rect = pygame.Rect(CHUNK_SIZE_W, 0, UI_WIDTH, SCREEN_HEIGHT)
        pygame.draw.rect(screen, (30, 35, 40), ui_rect)
        pygame.draw.line(screen, COLOR_GOLD, (CHUNK_SIZE_W, 0), (CHUNK_SIZE_W, SCREEN_HEIGHT), 3)

        screen.blit(font_title.render("Deadly Traffic", True, COLOR_GOLD), (CHUNK_SIZE_W + 20, 30))
        # UPRAVENO: pokud má aktuální auto víc než 1 život (např. autobus, loď, tank, Festival Car),
        # zobrazí se vedle skóre i počet zbývajících životů.
        score_text = f"Skóre: {score // 10}"
        if player.max_lives > 1:
            score_text += f"   Životy: {player.lives}/{player.max_lives}"
        screen.blit(font_main.render(score_text, True, (255, 255, 255)), (CHUNK_SIZE_W + 20, 80))
        # PŘIDÁNO: zobrazení nejvyššího dosaženého skóre
        screen.blit(font_main.render(f"Nejvyšší skóre: {high_score}", True, COLOR_GOLD), (CHUNK_SIZE_W + 20, 105))
        screen.blit(font_main.render(f"Auta za tebou: {len(enemies)}", True, (180, 180, 180)), (CHUNK_SIZE_W + 20, 130))
        # PŘIDÁNO: viditelnost evoluce AI populace
        screen.blit(font_main.render(f"Generace AI: {AI_POPULATION.generation}", True, (180, 220, 255)), (CHUNK_SIZE_W + 20, 175))
        screen.blit(font_main.render(f"Nejlepší fitness: {int(AI_POPULATION.best_fitness_ever)}", True, (180, 220, 255)), (CHUNK_SIZE_W + 20, 195))
        # PŘIDÁNO: aktuální (živé) fitness skóre nejlepšího auta v právě probíhající generaci
        current_best_fitness = max(AI_POPULATION.fitness) if AI_POPULATION.fitness else 0
        screen.blit(font_main.render(f"Aktuální fitness: {int(current_best_fitness)}", True, (180, 220, 255)), (CHUNK_SIZE_W + 20, 215))

        # PŘIDÁNO: přehled cooldownů schopností (dash na R, bodce na F)
        dash_cd_text = "Dash (R): Připraven" if player.dash_cooldown <= 0 else f"Dash (R): {player.dash_cooldown / FPS:.1f}s"
        spike_cd_text = "Bodce (F): Připraveny" if player.spike_cooldown <= 0 else f"Bodce (F): {player.spike_cooldown / FPS:.1f}s"
        dash_color = (120, 255, 150) if player.dash_cooldown <= 0 else (255, 210, 120)
        spike_color = (120, 255, 150) if player.spike_cooldown <= 0 else (255, 210, 120)
        screen.blit(font_main.render(dash_cd_text, True, dash_color), (CHUNK_SIZE_W + 20, 235))
        screen.blit(font_main.render(spike_cd_text, True, spike_color), (CHUNK_SIZE_W + 20, 255))

        # PŘIDÁNO: pokud právě letí kouzelný deštník ve vzduchu, zobraz to jako stavový hlášku v UI
        if player.special == "umbrella" and player.airborne_timer > 0:
            screen.blit(font_main.render("VE VZDUCHU - NEZRANITELNÝ", True, (200, 170, 255)), (CHUNK_SIZE_W + 20, 270))

        if crash_scene.triggered and not crash_scene.finished:
            screen.blit(font_main.render("ZÓNA NEHODY (BEZPEČÍ)", True, COLOR_ACCENT), (CHUNK_SIZE_W + 20, 150))
        else:
            screen.blit(font_main.render("STAV: Na silnici", True, (100, 255, 100)), (CHUNK_SIZE_W + 20, 150))

        # PŘIDÁNO: zobrazení aktuální obtížnosti (rychlost AI a maximální počet aut) a mincí v garáži
        screen.blit(font_main.render(f"Obtížnost: rychlost AI {current_ai_speed:.1f}, max aut {current_max_enemies}",
                                      True, (255, 200, 140)), (CHUNK_SIZE_W + 20, 660))
        screen.blit(font_main.render(f"Mince: {player_data['coins']}", True, COLOR_GOLD), (CHUNK_SIZE_W + 20, 685))

        # --- DETAILNÍ MINIMAPA ---
        map_ui_y = 290  # UPRAVENO: posunuto z 250 na 290, aby byl prostor pro nové cooldowny schopností
        map_size = UI_WIDTH - 40
        minimap_rect = pygame.Rect(CHUNK_SIZE_W + 20, map_ui_y, map_size, map_size)

        minimap_surf = pygame.Surface((map_size, map_size))
        minimap_surf.fill((20, 25, 30))

        mm_center_x = map_size // 2
        mm_center_y = map_size // 2
        zoom = 0.12

        start_cx = math.floor((player.world_x - 1000) / CHUNK_SIZE_W)
        end_cx = math.floor((player.world_x + 1000) / CHUNK_SIZE_W)
        start_cy = math.floor((player.world_y - 1000) / CHUNK_SIZE_H)
        end_cy = math.floor((player.world_y + 1000) / CHUNK_SIZE_H)

        for cx in range(start_cx, end_cx + 1):
            for cy in range(start_cy, end_cy + 1):
                chunk_offset_x = cx * CHUNK_SIZE_W - player.world_x
                chunk_offset_y = cy * CHUNK_SIZE_H - player.world_y

                if cx == -1:
                    r_pts = []
                    for y in range(0, CHUNK_SIZE_H, 40):
                        x = (CHUNK_SIZE_W // 2) + math.sin((cy * CHUNK_SIZE_H + y) * 0.004) * 100
                        mm_rx = mm_center_x + (chunk_offset_x + x) * zoom
                        mm_ry = mm_center_y + (chunk_offset_y + y) * zoom
                        r_pts.append((mm_rx, mm_ry))
                    if len(r_pts) > 1:
                        pygame.draw.lines(minimap_surf, (80, 110, 140), False, r_pts, int(200 * zoom))

                for rx in GRID_X:
                    mm_x = mm_center_x + (chunk_offset_x + rx) * zoom
                    pygame.draw.line(minimap_surf, (70, 75, 80), (mm_x, 0), (mm_x, map_size), int(ROAD_THICKNESS * zoom))
                for ry in GRID_Y:
                    mm_y = mm_center_y + (chunk_offset_y + ry) * zoom
                    pygame.draw.line(minimap_surf, (70, 75, 80), (0, mm_y), (map_size, mm_y), int(ROAD_THICKNESS * zoom))

                if (cx + cy) % 2 == 0:
                    mm_cx = mm_center_x + (chunk_offset_x + GRID_X[1]) * zoom
                    mm_cy = mm_center_y + (chunk_offset_y + GRID_Y[1]) * zoom
                    pygame.draw.circle(minimap_surf, (70, 75, 80), (int(mm_cx), int(mm_cy)), int(86 * zoom))
                    pygame.draw.circle(minimap_surf, (40, 70, 35), (int(mm_cx), int(mm_cy)), int(40 * zoom))

        for enemy in enemies:
            rel_ex = (enemy.world_x - player.world_x) * zoom
            rel_ey = (enemy.world_y - player.world_y) * zoom
            pygame.draw.circle(minimap_surf, COLOR_DANGER, (int(mm_center_x + rel_ex), int(mm_center_y + rel_ey)), 4)

        # Zobrazení polohy Easter Eggu (Bouračky) na minimapě
        rel_eex = (crash_scene.center_x - player.world_x) * zoom
        rel_eey = (crash_scene.center_y - player.world_y) * zoom
        pygame.draw.circle(minimap_surf, COLOR_GOLD, (int(mm_center_x + rel_eex), int(mm_center_y + rel_eey)), 5)

        pygame.draw.circle(minimap_surf, COLOR_ACCENT, (mm_center_x, mm_center_y), 5)

        screen.blit(minimap_surf, minimap_rect.topleft)
        pygame.draw.rect(screen, COLOR_GOLD, minimap_rect, 2)
        screen.blit(font_main.render("MINIMAPA MĚSTA", True, (150, 150, 150)), (CHUNK_SIZE_W + 20, map_ui_y + map_size + 5))

        if game_over:
            # UPRAVENO: posunuto níž (bylo 520/560), aby nekolidovalo s popiskem minimapy
            screen.blit(font_title.render("BOURAČKA!", True, COLOR_DANGER), (CHUNK_SIZE_W + 20, 570))
            # UPRAVENO: text teď zmiňuje i mezerník jako rychlou možnost restartu, plus M pro návrat do menu
            screen.blit(font_main.render("Stiskni MEZERNÍK pro restart", True, (255, 255, 255)), (CHUNK_SIZE_W + 20, 605))
            screen.blit(font_main.render("Stiskni M pro návrat do menu", True, (180, 220, 255)), (CHUNK_SIZE_W + 20, 625))

        btn_color = (180, 40, 60) if exit_button_rect.collidepoint(mouse_pos) else (130, 25, 40)
        pygame.draw.rect(screen, btn_color, exit_button_rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_DANGER, exit_button_rect, 2, border_radius=6)

        exit_txt = font_main.render("UKONČIT HRU", True, (255, 255, 255))
        screen.blit(exit_txt, (exit_button_rect.x + (btn_w - exit_txt.get_width()) // 2, exit_button_rect.y + 12))

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()