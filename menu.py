import pygame
import os

WIDTH = 1920
HEIGHT = 1080


class Button:

    def __init__(self, text, x, y, w, h):

        self.text = text
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, screen, font, mouse):

        hover = self.rect.collidepoint(mouse)

        color = (235, 180, 40) if hover else (40, 40, 40)

        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 3, border_radius=10)

        txt = font.render(self.text, True, (255, 255, 255))
        screen.blit(
            txt,
            (
                self.rect.centerx - txt.get_width() // 2,
                self.rect.centery - txt.get_height() // 2
            )
        )


class MainMenu:

    def __init__(self, screen):

        self.screen = screen

        self.title_font = pygame.font.SysFont("Arial", 72, True)
        self.button_font = pygame.font.SysFont("Arial", 34, True)

        path = os.path.join("assets", "menu_background.png")

        if os.path.exists(path):
            img = pygame.image.load(path).convert()
            self.background = pygame.transform.scale(img, (WIDTH, HEIGHT))
        else:
            self.background = None

        start_y = 380

        self.buttons = [

            Button("HRÁT", 120, start_y, 320, 65),

            Button("GARÁŽ", 120, start_y + 90, 320, 65),

            Button("NASTAVENÍ", 120, start_y + 180, 320, 65),

            Button("KONEC", 120, start_y + 270, 320, 65),

        ]

    def update(self, dt):
        pass

    def draw(self):

        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill((30, 30, 30))

        shadow = self.title_font.render("PRAŽSKÁ HONIČKA", True, (0, 0, 0))
        self.screen.blit(shadow, (64, 64))

        title = self.title_font.render("PRAŽSKÁ HONIČKA", True, (255, 220, 70))
        self.screen.blit(title, (60, 60))

        mouse = pygame.mouse.get_pos()

        for b in self.buttons:
            b.draw(self.screen, self.button_font, mouse)

        info = pygame.font.SysFont("Arial", 24)

        txt = info.render("Verze 2.0", True, (255, 255, 255))
        self.screen.blit(txt, (20, HEIGHT - 40))

    def handle_event(self, event):

        if event.type == pygame.MOUSEBUTTONDOWN:

            if event.button == 1:

                for button in self.buttons:

                    if button.rect.collidepoint(event.pos):

                        if button.text == "HRÁT":
                            return "start"

                        elif button.text == "GARÁŽ":
                            return "garage"

                        elif button.text == "NASTAVENÍ":
                            return "settings"

                        elif button.text == "KONEC":
                            return "quit"

        return None
