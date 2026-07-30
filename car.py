# car.py

import math
import pygame


class Car:

    def __init__(self, image, x, y):

        self.image = image
        self.original_image = image

        self.x = x
        self.y = y

        self.angle = 0

        self.speed = 0
        self.max_speed = 250

        self.acceleration = 350
        self.brake = 550
        self.turn_speed = 180

        self.max_hp = 100
        self.hp = 100

        self.width = image.get_width()
        self.height = image.get_height()

        self.destroyed = False

    def accelerate(self, dt):
        self.speed += self.acceleration * dt

    def brake_car(self, dt):
        self.speed -= self.brake * dt

    def turn_left(self, dt):
        self.angle += self.turn_speed * dt

    def turn_right(self, dt):
        self.angle -= self.turn_speed * dt

    def update(self, dt):

        self.speed *= 0.99

        self.speed = max(-80, min(self.speed, self.max_speed))

        r = math.radians(self.angle)

        self.x -= math.sin(r) * self.speed * dt
        self.y -= math.cos(r) * self.speed * dt

    def damage(self, amount):

        self.hp -= amount

        if self.hp <= 0:
            self.hp = 0
            self.destroyed = True

    def repair(self):

        self.hp = self.max_hp
        self.destroyed = False

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

    def get_rect(self):

        return pygame.Rect(
            self.x - self.width // 2,
            self.y - self.height // 2,
            self.width,
            self.height
        )
