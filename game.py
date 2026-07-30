# game.py

import pygame

from player import Player


class Game:

    def __init__(self, screen):

        self.screen = screen

        self.game_over = False

        self.camera_x = 0
        self.camera_y = 0

        # ---------- Assety ----------
        self.player_image = pygame.image.load(
            "assets/tile000.png"
        ).convert_alpha()

        # ---------- Hráč ----------
        self.player = Player(
            self.player_image,
            0,
            0
        )

        # ---------- Skupiny ----------
        self.ai_cars = []

        self.traffic = []

        self.effects = []

    def reset(self):

        self.game_over = False

        self.player.x = 0
        self.player.y = 0

        self.player.hp = self.player.max_hp

        self.player.speed = 0

        self.player.money = 0

        self.player.wanted = 0
        self.player.wanted_points = 0

        self.ai_cars.clear()

        self.traffic.clear()

        self.effects.clear()

    def handle_event(self, event):

        return None

    def update(self, dt):

        self.player.update(dt)

        if self.player.is_dead():

            self.game_over = True

        self.camera_x = self.player.x - 960
        self.camera_y = self.player.y - 540

    def draw(self):

        self.screen.fill((50, 120, 50))

        self.player.draw(
            self.screen,
            self.camera_x,
            self.camera_y
        )

        self.draw_hud()

    def draw_hud(self):

        font = pygame.font.SysFont("Arial", 28)

        hp = font.render(
            f"HP: {self.player.hp}",
            True,
            (255,255,255)
        )

        money = font.render(
            f"Kč: {self.player.money}",
            True,
            (255,255,0)
        )

        wanted = font.render(
            "★"*self.player.wanted,
            True,
            (255,180,0)
        )

        self.screen.blit(hp,(20,20))
        self.screen.blit(money,(20,60))
        self.screen.blit(wanted,(20,100))
