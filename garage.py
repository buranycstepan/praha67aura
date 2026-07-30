# garage.py

import pygame


class Garage:

    def __init__(self, shop, save):

        self.shop = shop
        self.save = save

        self.selected = self.save.get("selected_car")

        self.font = pygame.font.SysFont("Arial", 34, True)

        self.small = pygame.font.SysFont("Arial", 24)

    def handle_event(self, event):

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_LEFT:

                self.selected -= 1

                if self.selected < 0:
                    self.selected = len(self.shop.cars) - 1

            elif event.key == pygame.K_RIGHT:

                self.selected += 1

                if self.selected >= len(self.shop.cars):
                    self.selected = 0

            elif event.key == pygame.K_RETURN:

                if self.save.owns_car(self.selected):

                    self.save.select_car(self.selected)

                    self.save.save()

                    return "selected"

            elif event.key == pygame.K_ESCAPE:

                return "menu"

        return None

    def draw(self, screen):

        screen.fill((30, 30, 30))

        title = self.font.render(
            "GARÁŽ",
            True,
            (255,220,60)
        )

        screen.blit(title, (50,40))

        car = self.shop.cars[self.selected]

        image = pygame.transform.scale(
            car.image,
            (180,320)
        )

        screen.blit(image,(120,180))

        y = 180

        lines = [

            f"Model: {car.name}",

            f"HP: {car.hp}",

            f"Rychlost: {car.speed}",

            f"Cena: {car.price} Kč"

        ]

        for line in lines:

            txt = self.small.render(
                line,
                True,
                (255,255,255)
            )

            screen.blit(txt,(420,y))

            y += 40

        if self.save.owns_car(self.selected):

            info = self.font.render(
                "VLASTNÍŠ",
                True,
                (0,255,0)
            )

        else:

            info = self.font.render(
                "ZAMČENO",
                True,
                (255,60,60)
            )

        screen.blit(info,(420,380))

        help_text = self.small.render(
            "← → změna auta | ENTER vybrat | ESC menu",
            True,
            (180,180,180)
        )

        screen.blit(help_text,(50,950))
