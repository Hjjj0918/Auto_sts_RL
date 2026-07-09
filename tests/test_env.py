"""Smoke test for MiniStsEnv — runs one episode with random actions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.mini_sts_env import MiniStsEnv

env = MiniStsEnv()
obs, _ = env.reset()

print("Initial observation:", obs)
print("Expected: [1.0, 1.0, 1.0, 0.0] (full HP, full energy, no block)\n")

total_reward = 0.0
step = 0
terminated = False

action_names = ["Strike", "Defend", "Heavy", "EndTurn"]

while not terminated:
    action = env.action_space.sample()
    obs, reward, terminated, truncated, _ = env.step(action)
    total_reward += reward
    step += 1

    print(f"Step {step}: {action_names[action]:>8}  "
          f"reward={reward:+6.1f}  total={total_reward:+6.1f}")
    env.render()

    if step >= 200:
        print("Hit step limit, stopping.")
        break

print(f"\nEpisode finished: {step} steps, total reward = {total_reward:+.1f}")
env.close()
