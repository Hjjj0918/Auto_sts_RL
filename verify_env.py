"""
Verify that all core dependencies are installed correctly.

Usage: python verify_env.py
"""
import torch
import gymnasium as gym
import stable_baselines3 as sb3
import numpy as np

print("=" * 50)
print("Core library versions")
print("=" * 50)
print(f"  Python:    {__import__('sys').version.split()[0]}")
print(f"  PyTorch:   {torch.__version__}")
print(f"  Gymnasium: {gym.__version__}")
print(f"  SB3:       {sb3.__version__}")
print(f"  NumPy:     {np.__version__}")

print(f"\n{'=' * 50}")
print("Hardware")
print("=" * 50)
print(f"  CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"  VRAM: {mem:.1f} GB")
print(f"  CPU cores: {__import__('os').cpu_count()}")

print(f"\n{'=' * 50}")
print("Quick smoke test (CartPole-v1)")
print("=" * 50)
env = gym.make("CartPole-v1")
obs, _ = env.reset()
print(f"  Observation shape: {env.observation_space.shape}")
print(f"  Action count: {getattr(env.action_space, 'n', '?')}")
for i in range(3):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, _ = env.step(action)
    print(f"  Step {i+1}: action={action}, reward={reward:+.0f}, "
          f"obs={[round(float(x), 2) for x in obs]}")
env.close()

print(f"\n{'=' * 50}")
print("All checks passed.")
print("=" * 50)
