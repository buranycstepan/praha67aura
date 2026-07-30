# ai_car.py

import math
import numpy as np
import pygame

from stable_baselines3 import PPO

from car import Car


class AICar(Car):

    def __init__(self, image, x, y):

        super().__init__(image, x, y)

        self.model = PPO.load("models/prague_ai")

        self.think_timer = 0

        self.action = 0

    def get_state(self, player):

        dx = player.x - self.x
        dy = player.y - self.y

        distance = math.sqrt(dx * dx + dy * dy)

        angle = math.atan2(dy, dx)

        return np.array([

            dx,
            dy,

            distance,

            self.speed,

            math.sin(angle),

            math.cos(angle),

            player.speed,

            player.hp,

        ], dtype=np.float32)

    def update_ai(self, player, dt):

        self.think_timer += dt

        if self.think_timer > 0.05:

            self.think_timer = 0

            state = self.get_state(player)

            self.action, _ = self.model.predict(
                state,
                deterministic=True
            )

        self.apply_action(dt)

        self.update(dt)

    def apply_action(self, dt):

        if self.action == 1:
            self.accelerate(dt)

        elif self.action == 2:
            self.brake_car(dt)

        elif self.action == 3:
            self.turn_left(dt)

        elif self.action == 4:
            self.turn_right(dt)
