"""
Train with MaskablePPO — actions that cost more energy than available are
masked out before sampling, so the agent never wastes time on illegal moves.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.callbacks import MaskableEvalCallback
from stable_baselines3.common.monitor import Monitor
from src.mini_sts_env import MiniStsEnv
import os


def make_env():
    return Monitor(MiniStsEnv())


train_env = make_env()
eval_env = make_env()

model = MaskablePPO(
    "MlpPolicy",
    train_env,
    n_steps=512,
    batch_size=64,
    ent_coef=0.01,
    device="cpu",
    verbose=1,
)

eval_callback = MaskableEvalCallback(
    eval_env,
    best_model_save_path="./models/",
    log_path="./models/",
    eval_freq=5_000,
    deterministic=True,
)

print("\nTraining MaskablePPO for 50k steps...\n")
model.learn(total_timesteps=50_000, callback=eval_callback)

os.makedirs("models", exist_ok=True)
model.save("models/mini_sts_masked_ppo")
print("\nModel saved to models/mini_sts_masked_ppo.zip")
