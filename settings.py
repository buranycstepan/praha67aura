# settings.py

import pygame

pygame.init()

# ------------------------
# Okno
# ------------------------

WIDTH = 1920
HEIGHT = 1080
FPS = 60

TITLE = "Pražská honička"

FULLSCREEN = False

# ------------------------
# Barvy
# ------------------------

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

RED = (220, 40, 40)
GREEN = (60, 220, 60)
BLUE = (50, 120, 255)

YELLOW = (255, 220, 70)

GRAY = (50, 50, 50)
DARK_GRAY = (30, 30, 30)

# ------------------------
# Hráč
# ------------------------

PLAYER_HP = 100

PLAYER_ACCELERATION = 500

PLAYER_MAX_SPEED = 320

PLAYER_BRAKE = 700

PLAYER_TURN_SPEED = 240

# ------------------------
# AI
# ------------------------

AI_CARS = 30

AI_MAX_SPEED = 290

AI_SPAWN_DISTANCE = 900

AI_DESPAWN_DISTANCE = 1200

# ------------------------
# Hledanost
# ------------------------

MAX_WANTED = 5

WANTED_POINTS = [
    0,
    10,
    30,
    60,
    100,
    150
]

# ------------------------
# Peníze
# ------------------------

START_MONEY = 0

# ------------------------
# Fonty
# ------------------------

FONT_SMALL = pygame.font.SysFont("Arial", 22)

FONT = pygame.font.SysFont("Arial", 30)

FONT_BIG = pygame.font.SysFont("Arial", 70, True)

# ------------------------
# Assety
# ------------------------

ASSET_DIR = "assets"

MENU_BACKGROUND = "assets/menu_background.png"

ROAD_TEXTURE = "assets/background-1.png"

SAVE_FILE = "save.json"
