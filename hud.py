# hud.py

import pygame


class HUD:

    def __init__(self):

        self.font = pygame.font.SysFont("Arial", 28, True)
        self.small = pygame.font.SysFont("Arial", 20)

    def draw(self, screen, player):

        # ----- HP -----

        pygame.draw.rect(screen, (40, 40, 40), (20, 20, 300, 28))

        hp_width = int((player.hp / player.max_hp) * 300)

        pygame.draw.rect(
            screen,
            (220, 40, 40),
            (20, 20, hp_width, 28)
        )

        text = self.font.render(
            f"HP {player.hp}/{player.max_hp}",
            True,
            (255,255,255)
        )

        screen.blit(text, (25, 20))

        # ----- Peníze -----

        money = self.font.render(
            f"{player.money:,} Kč",
            True,
            (255,220,0)
        )

        screen.blit(money, (20, 65))

        # ----- Hledanost -----

        stars = ""

        for i in range(player.wanted):
            stars += "★"

        wanted = self.font.render(
            stars,
            True,
            (255,200,0)
        )

        screen.blit(wanted, (20, 105))

        # ----- Tachometr -----

        speed = self.font.render(
            f"{int(player.speed)} km/h",
            True,
            (255,255,255)
        )

        screen.blit(speed, (20, 145))

        # ----- Ujetá vzdálenost -----

        distance = self.small.render(
            f"{int(player.distance)} m",
            True,
            (255,255,255)
        )

        screen.blit(distance, (20, 185))
