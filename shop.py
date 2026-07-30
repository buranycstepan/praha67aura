# shop.py

import pygame


class ShopCar:

    def __init__(self, name, image, price, hp, speed):

        self.name = name
        self.image = image

        self.price = price

        self.hp = hp
        self.speed = speed


class Shop:

    def __init__(self):

        self.selected = 0

        self.cars = []

        self.owned = [0]

        self.create_cars()

    def create_cars(self):

        names = [

            "Starter",
            "City",
            "Sedan",
            "Taxi",
            "SUV",
            "Sport",
            "Muscle",
            "Van"

        ]

        for i in range(8):

            image = pygame.image.load(
                f"assets/tile{i:03}.png"
            ).convert_alpha()

            car = ShopCar(

                names[i],

                image,

                price=i * 10000,

                hp=100 + i * 15,

                speed=220 + i * 15

            )

            self.cars.append(car)

    def next(self):

        self.selected += 1

        if self.selected >= len(self.cars):
            self.selected = 0

    def previous(self):

        self.selected -= 1

        if self.selected < 0:
            self.selected = len(self.cars) - 1

    def buy(self, player):

        car = self.cars[self.selected]

        if self.selected in self.owned:
            return True

        if player.money >= car.price:

            player.money -= car.price

            self.owned.append(self.selected)

            return True

        return False

    def get_selected(self):

        return self.cars[self.selected]

    def draw(self, screen):

        screen.fill((20,20,20))

        font = pygame.font.SysFont("Arial",42,True)

        small = pygame.font.SysFont("Arial",26)

        car = self.get_selected()

        title = font.render(
            "AUTOSALON",
            True,
            (255,220,50)
        )

        screen.blit(title,(50,40))

        img = pygame.transform.scale(
            car.image,
            (180,320)
        )

        screen.blit(img,(150,180))

        y = 180

        for txt in [

            f"Model: {car.name}",
            f"Cena: {car.price} Kč",
            f"HP: {car.hp}",
            f"Max rychlost: {car.speed} km/h"

        ]:

            t = small.render(
                txt,
                True,
                (255,255,255)
            )

            screen.blit(t,(420,y))

            y += 40

        help_text = small.render(
            "← → změna | ENTER koupit | ESC zpět",
            True,
            (180,180,180)
        )

        screen.blit(help_text,(50,950))
