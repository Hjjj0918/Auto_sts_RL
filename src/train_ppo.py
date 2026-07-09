"""
Train a PPO agent on MiniStsEnv.

Usage: python train_ppo.py
Output: models/mini_sts_ppo.zip — the trained model file
"""
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.monitor import Monitor
from src.mini_sts_env import MiniStsEnv
import os


def make_env():
    """Factory: returns a monitored env instance."""
    return Monitor(MiniStsEnv())


# Total timesteps. For a 4D observation and 4 discrete actions this is more
# than enough — training completes in under a minute on a 16-core CPU.
TOTAL_TIMESTEPS = 50_000

# Create training and evaluation environments.
# Wrapping with Monitor lets SB3 track episode lengths and rewards automatically.
train_env = make_env()
eval_env = make_env()

# PPO hyperparameters tuned for this tiny environment.
# n_steps=512: collect 512 steps per rollout before updating (small env, small batch).
# batch_size=64: mini-batch size for gradient updates.
# ent_coef=0.01: small entropy bonus to encourage exploration early on.
model = PPO(
    "MlpPolicy",
    train_env,
    n_steps=512,
    batch_size=64,
    ent_coef=0.01,
    device="cpu",              # small network + small env: CPU is faster than GPU here
    verbose=1,
)

# Evaluation callback: runs the model every 5000 steps to check progress
# without exploration noise, so we see its true performance.
eval_callback = EvalCallback(
    eval_env,
    best_model_save_path="./models/",
    log_path="./models/",
    eval_freq=5_000,
    deterministic=True,
)

print(f"\nStarting PPO training for {TOTAL_TIMESTEPS} timesteps...\n")
model.learn(total_timesteps=TOTAL_TIMESTEPS, callback=eval_callback)

# Save the final model.
os.makedirs("models", exist_ok=True)
model.save("models/mini_sts_ppo")
print("\nModel saved to models/mini_sts_ppo.zip")
