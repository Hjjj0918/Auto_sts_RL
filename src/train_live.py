"""
Train MaskablePPO on live Slay the Spire.

Run this while in combat. The agent learns across multiple combats.
After each combat, manually start the next one and press Enter.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sb3_contrib import MaskablePPO
from src.sts_gym_env import StsGymEnv
import os

print("Connecting...")
env = StsGymEnv()

model = MaskablePPO(
    "MlpPolicy",
    env,
    n_steps=256,
    batch_size=64,
    ent_coef=0.08,
    device="cpu",
    verbose=1,
)

combat = 0
try:
    while True:
        combat += 1
        print(f"\n{'='*40}")
        print(f"Combat #{combat}")
        print(f"{'='*40}")

        # Reset env for the current combat.
        obs, _ = env.reset()

        # Learn for up to 512 steps (enough for several turns).
        model.learn(total_timesteps=512, reset_num_timesteps=False)

        print(f"Combat #{combat} done. Total steps: {model.num_timesteps}")
        model.save("models/sts_live_ppo")
        print("Model saved.")

        ans = input("\nStart next combat then press Enter (q=quit): ").strip()
        if ans.lower() == 'q':
            break

except KeyboardInterrupt:
    print("\nInterrupted.")

model.save("models/sts_live_ppo")
print("Final model saved to models/sts_live_ppo.zip")
env.close()
