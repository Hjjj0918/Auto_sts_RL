"""
Train PPO on MiniStsEnv with 16 parallel environments.

Usage: python train_ppo_parallel.py   (run from project root: python src/train_ppo_parallel.py)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.monitor import Monitor
from src.mini_sts_env import MiniStsEnv
import os


def make_env(rank: int):
    """
    Factory for SubprocVecEnv. Each env runs in its own Python process.
    `rank` distinguishes processes for debugging (e.g. seeding differently).
    """
    def _init():
        env = MiniStsEnv()
        env = Monitor(env)
        return env
    return _init


if __name__ == "__main__":
    # On Windows, multiprocessing uses 'spawn' — child processes re-import
    # this module. Without this guard, each child would try to spawn 16 more
    # children, causing infinite recursion. The guard prevents that.

    NUM_ENVS = 16
    print(f"Launching {NUM_ENVS} parallel environments...")
    envs = SubprocVecEnv([make_env(i) for i in range(NUM_ENVS)])

    # With 16 envs collecting simultaneously, each rollout gathers 16× more data.
    # n_steps=512 per env → effective batch = 512 × 16 = 8192 steps per update.
    model = PPO(
        "MlpPolicy",
        envs,
        n_steps=512,
        batch_size=256,
        ent_coef=0.01,
        device="cpu",
        verbose=1,
    )

    print(f"\nTraining with {NUM_ENVS} parallel envs for 100k steps...\n")
    model.learn(total_timesteps=100_000)

    os.makedirs("models", exist_ok=True)
    model.save("models/mini_sts_ppo_parallel")
    print("\nModel saved to models/mini_sts_ppo_parallel.zip")
    envs.close()
