# ai_env.py

import gymnasium as gym
from gymnasium import spaces
import numpy as np


class PragueEnv(gym.Env):

    def __init__(self):

        super().__init__()

        # Pozorování:
        # [x hráče, y hráče,
        #  x AI, y AI,
        #  rychlost AI,
        #  vzdálenost]
        self.observation_space = spaces.Box(
            low=-10000,
            high=10000,
            shape=(6,),
            dtype=np.float32
        )

        # Akce:
        # 0 = nic
        # 1 = plyn
        # 2 = brzda
        # 3 = vlevo
        # 4 = vpravo
        self.action_space = spaces.Discrete(5)

        self.reset()

    def reset(self, seed=None, options=None):

        super().reset(seed=seed)

        self.player_x = 0
        self.player_y = 0

        self.ai_x = 300
        self.ai_y = 300

        self.speed = 0

        return self.get_state(), {}

    def get_state(self):

        distance = np.sqrt(
            (self.player_x - self.ai_x) ** 2 +
            (self.player_y - self.ai_y) ** 2
        )

        return np.array([
            self.player_x,
            self.player_y,
            self.ai_x,
            self.ai_y,
            self.speed,
            distance
        ], dtype=np.float32)

    def step(self, action):

        if action == 1:
            self.speed += 2

        elif action == 2:
            self.speed -= 2

        elif action == 3:
            self.ai_x -= 4

        elif action == 4:
            self.ai_x += 4

        self.ai_y -= self.speed

        distance = np.sqrt(
            (self.player_x - self.ai_x) ** 2 +
            (self.player_y - self.ai_y) ** 2
        )

        reward = -distance * 0.01

        done = False

        # AI chytila hráče
        if distance < 30:
            reward += 100
            done = True

        # Ujela moc daleko
        if distance > 2000:
            reward -= 100
            done = True

        return (
            self.get_state(),
            reward,
            done,
            False,
            {}
        )
