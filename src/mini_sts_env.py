"""
A minimal Slay the Spire combat environment for reinforcement learning.

Rules:
  - Player: 30 HP, 3 energy per turn
  - Enemy: 20 HP, deals 5~8 damage per turn
  - Hand each turn: Strike (1 cost, 6 dmg), Defend (1 cost, 5 block), Heavy (2 cost, 12 dmg)
  - Actions: 0=Strike, 1=Defend, 2=Heavy, 3=End Turn
  - After ending turn: enemy attacks, block resets, energy refreshes

Observation (4D, normalized to [0,1]):
  [player_hp/30, enemy_hp/20, energy/3, block/15]

Reward:
  +damage dealt, +10 for killing enemy, -damage taken, -10 for dying
  -1 penalty for attempting an unaffordable card
"""
import gymnasium as gym
import numpy as np
from gymnasium import spaces


class MiniStsEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self, render_mode: str | None = None):
        super().__init__()

        self.player_max_hp = 30.0
        self.enemy_max_hp = 20.0
        self.max_energy = 3.0
        self.max_block = 15.0
        self.max_episode_steps = 100

        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(4,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(4)
        self.render_mode = render_mode

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)

        self.player_hp = self.player_max_hp
        self.enemy_hp = self.enemy_max_hp
        self.energy = self.max_energy
        self.block = 0.0
        self.step_count = 0

        return self._get_obs(), {}

    def step(self, action: int):
        reward = 0.0
        self.step_count += 1

        if action == 0:  # Strike: 1 cost, 6 damage
            if self.energy >= 1:
                self.energy -= 1
                self.enemy_hp -= 6.0
                reward += 6.0
                if self.enemy_hp <= 0:
                    self.enemy_hp = 0.0
                    reward += 10.0
            else:
                reward -= 1.0  # penalty for attempting unaffordable action

        elif action == 1:  # Defend: 1 cost, 5 block
            if self.energy >= 1:
                self.energy -= 1
                self.block += 5.0
            else:
                reward -= 1.0

        elif action == 2:  # Heavy: 2 cost, 12 damage
            if self.energy >= 2:
                self.energy -= 2
                self.enemy_hp -= 12.0
                reward += 12.0
                if self.enemy_hp <= 0:
                    self.enemy_hp = 0.0
                    reward += 10.0
            else:
                reward -= 1.0

        elif action == 3:  # End Turn
            enemy_dmg = float(self.np_random.integers(5, 9))

            if self.block > 0:
                blocked = min(self.block, enemy_dmg)
                self.block -= blocked
                actual_dmg = enemy_dmg - blocked
            else:
                blocked = 0.0
                actual_dmg = enemy_dmg

            self.player_hp -= actual_dmg
            reward -= actual_dmg

            # Expose enemy action details via info dict for rendering / debugging.
            # The agent does NOT see this — it only sees the 4D observation vector.
            self.last_enemy_info = {
                "enemy_raw_dmg": enemy_dmg,
                "blocked": blocked,
                "actual_dmg": actual_dmg,
            }

            self.block = 0.0
            self.energy = self.max_energy

        terminated = False
        truncated = False

        if self.enemy_hp <= 0:
            terminated = True
        elif self.player_hp <= 0:
            self.player_hp = 0.0
            reward -= 10.0
            terminated = True
        elif self.step_count >= self.max_episode_steps:
            truncated = True

        self.player_hp = max(0.0, self.player_hp)
        self.enemy_hp = max(0.0, self.enemy_hp)

        info = getattr(self, "last_enemy_info", {})
        return self._get_obs(), reward, terminated, truncated, info

    def _get_obs(self) -> np.ndarray:
        return np.array([
            self.player_hp / self.player_max_hp,
            self.enemy_hp / self.enemy_max_hp,
            self.energy / self.max_energy,
            self.block / self.max_block,
        ], dtype=np.float32)

    def render(self):
        print(f"\n{'='*40}")
        print(f"  Player HP: {self.player_hp:.0f}/{self.player_max_hp:.0f}  "
              f"Energy: {self.energy:.0f}/{self.max_energy:.0f}  "
              f"Block: {self.block:.0f}")
        print(f"  Enemy HP: {self.enemy_hp:.0f}/{self.enemy_max_hp:.0f}")
        print(f"  Actions: 0=Strike(1e/6dmg) 1=Defend(1e/5blk) "
              f"2=Heavy(2e/12dmg) 3=EndTurn")
        print(f"{'='*40}")

    def close(self):
        pass
