# player.py

import math
import pygame


class Player:

    def __init__(self, image, x, y):

        self.image = image
        self.original_image = image

        self.x = x
        self.y = y

        self.angle = 0

        self.speed = 0

        self.max_speed = 320
        self.acceleration = 450
        self.brake = 700
        self.turn_speed = 220

        # Stav auta
        self.max_hp = 100
        self.hp = self.max_hp

        self.money = 0

        self.wanted = 0
        self.wanted_points = 0

        self.distance = 0

    def update(self, dt):

        keys = pygame.key.get_pressed()

        if keys[pygame.K_w]:
            self.speed += self.acceleration * dt

        if keys[pygame.K_s]:
            self.speed -= self.brake * dt

        if keys[pygame.K_a]:
            self.angle += self.turn_speed * dt

        if keys[pygame.K_d]:
            self.angle -= self.turn_speed * dt

        if not keys[pygame.K_w]:
            self.speed *= 0.985

        self.speed = max(-80, min(self.speed, self.max_speed))

        rad = math.radians(self.angle)

        self.x -= math.sin(rad) * self.speed * dt
        self.y -= math.cos(rad) * self.speed * dt

        self.distance += abs(self.speed * dt)

    def damage(self, amount):

        self.hp -= amount

        if self.hp < 0:
            self.hp = 0

    def repair(self):

        self.hp = self.max_hp

    def add_money(self, amount):

        self.money += amount

    def add_wanted(self, amount):

        self.wanted_points += amount

        if self.wanted_points >= 150:
            self.wanted = 5

        elif self.wanted_points >= 100:
            self.wanted = 4

        elif self.wanted_points >= 60:
            self.wanted = 3

        elif self.wanted_points >= 30:
            self.wanted = 2

        elif self.wanted_points >= 10:
            self.wanted = 1

        else:
            self.wanted = 0

    def is_dead(self):

        return self.hp <= 0

    def draw(self, screen, camera_x, camera_y):

        sprite = pygame.transform.rotate(
            self.original_image,
            self.angle
        )

        rect = sprite.get_rect(
            center=(
                self.x - camera_x,
                self.y - camera_y
            )
        )

        screen.blit(sprite, rect)
