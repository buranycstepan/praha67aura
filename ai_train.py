# ai_train.py

from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env

from ai_env import PragueEnv


env = PragueEnv()

check_env(env)

model = PPO(

    "MlpPolicy",

    env,

    verbose=1,

    learning_rate=0.0003,

    n_steps=2048,

    batch_size=64,

    gamma=0.99,

    gae_lambda=0.95,

    ent_coef=0.01

)

print("Trénuji AI...")

model.learn(
    total_timesteps=500000
)

model.save("models/prague_ai")

print("Hotovo!")
