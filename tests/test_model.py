"""
Load the trained PPO model and play one episode with verbose output.
Usage: python tests/test_model.py   (run from project root)
"""
import sys
from pathlib import Path

# Ensure project root is on Python's module search path,
# so 'from src.mini_sts_env import ...' works regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stable_baselines3 import PPO
from src.mini_sts_env import MiniStsEnv

model = PPO.load("models/mini_sts_ppo.zip", device="cpu")
env = MiniStsEnv()

obs, _ = env.reset()
terminated = False
total_reward = 0.0
step = 0

action_names = ["Strike", "Defend", "Heavy", "EndTurn"]

print("=" * 50)
print("Trained model playing one episode")
print("=" * 50)

while not terminated:
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(int(action))
    total_reward += reward
    step += 1

    print(f"\n--- Step {step} ---")
    print(f"  AI chooses: {action_names[int(action)]} (action={action})")
    print(f"  Reward: {reward:+.1f}")
    env.render()

    # Show enemy action details when the turn ends
    if int(action) == 3 and info:
        raw = info.get("enemy_raw_dmg", "?")
        blocked = info.get("blocked", 0)
        actual = info.get("actual_dmg", "?")
        print(f"  >>> Enemy attacks! raw={raw:.0f} blocked={blocked:.0f} taken={actual:.0f}")

    if step >= 100:
        print("Truncated (100 step limit)")
        break

print(f"\nEpisode finished: {step} steps, total reward = {total_reward:+.1f}")
env.close()
