"""Quick test: StsGymEnv with random masked actions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sts_gym_env import StsGymEnv
import numpy as np

env = StsGymEnv()
print("Connecting...\n")

obs, info = env.reset()
print(f"Obs: {obs.shape}  HP: {info['hp']}/{info['max_hp']}  "
      f"Energy: {info['energy']}  Hand: {info['hand_size']}")
print(f"Mask: {info['action_mask'].astype(int)}\n")

step = 0
total = 0.0
names = [f"play_{i}" for i in range(10)] + ["end"]

while True:
    mask = env.action_masks()
    valid = np.where(mask)[0]
    if len(valid) == 0:
        break
    action = np.random.choice(valid)
    obs, reward, term, trunc, info = env.step(action)
    total += reward
    step += 1
    print(f"{'END' if term else '  '} S{step}: {names[int(action)]:>8} "
          f"r={reward:+.2f} total={total:+.1f}  E={info['energy']} "
          f"HP={info['hp']}/{info['max_hp']}")
    if term:
        print(f"\nDone! {step} steps, total={total:+.1f}")
        break
    if step >= 200:
        break

env.close()
