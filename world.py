# world.py

import random
import pygame


class World:

    def __init__(self):

        self.road_texture = pygame.image.load(
            "assets/background-1.png"
        ).convert()

        self.tile_size = 512

        self.tiles = {}

    def get_tile(self, x, y):

        key = (x, y)

        if key not in self.tiles:

            self.tiles[key] = {
                "type": "road"
            }

        return self.tiles[key]

    def update(self, player):

        px = int(player.x // self.tile_size)
        py = int(player.y // self.tile_size)

        for x in range(px - 4, px + 5):

            for y in range(py - 4, py + 5):

                self.get_tile(x, y)

    def draw(self, screen, camera_x, camera_y):

        start_x = int(camera_x // self.tile_size)
        start_y = int(camera_y // self.tile_size)

        for x in range(start_x - 1, start_x + 6):

            for y in range(start_y - 1, start_y + 5):

                screen_x = x * self.tile_size - camera_x
                screen_y = y * self.tile_size - camera_y

                screen.blit(
                    self.road_texture,
                    (screen_x, screen_y)
                )
