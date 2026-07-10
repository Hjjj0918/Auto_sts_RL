"""
Gym environment for real Slay the Spire via Communication Mod.
Observation: 78-dim. Actions: 0-9 = play hand[n], 10 = end turn.
"""
import socket
import json
import numpy as np
import gymnasium as gym
from gymnasium import spaces


class StsGymEnv(gym.Env):
    metadata = {"render_modes": []}
    MAX_HAND = 10
    MAX_MONSTERS = 5
    OBS_DIM = 4 + 10 * 5 + 5 * 4 + 4

    def __init__(self, host="127.0.0.1", port=9339):
        super().__init__()
        self.host = host
        self.port = port
        self.sock = None
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(self.OBS_DIM,), dtype=np.float32)
        self.action_space = spaces.Discrete(11)
        self._state = None
        self._prev_hp = None
        self._prev_enemy_hp = None
        self._turn_count = 0

    def _connect(self):
        for _ in range(30):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(5.0)
                self.sock.connect((self.host, self.port))
                return
            except ConnectionRefusedError:
                time.sleep(1.0)
        raise ConnectionError(f"Could not connect to {self.host}:{self.port}")

    def _send(self, cmd: str):
        self.sock.sendall((cmd + "\n").encode("utf-8"))

    def _recv(self) -> dict:
        buf = b""
        while b"\n" not in buf:
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                raise ConnectionError("Bridge closed")
            buf += chunk
        return json.loads(buf.split(b"\n")[0].decode("utf-8"))

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self._connect()
        # Drain until we get a combat state.
        while True:
            state = self._recv()
            cmds = state.get("available_commands", [])
            if "play" in cmds:
                break
            self._send("state")
        self._prev_hp = None
        self._prev_enemy_hp = None
        self._turn_count = 0
        self._state = state
        return self._build_obs(state), self._build_info(state)

    def step(self, action):
        action = int(action)
        prev_player = self._state.get("game_state", {}).get(
            "combat_state", {}).get("player", {})
        prev_enemies = self._state.get("game_state", {}).get(
            "combat_state", {}).get("monsters", [])
        hand = self._state.get("game_state", {}).get(
            "combat_state", {}).get("hand", [])

        if action == 10:
            self._send("end")
            self._turn_count += 1
        elif action < len(hand):
            self._send(f"play {action}")
        else:
            self._send("state")

        # Read one state — simple and synchronous, like test_random_play.py.
        state = self._recv()
        cmds = state.get("available_commands", [])

        # Handle target selection.
        if "choose" in cmds:
            self._send("choose 0")
            state = self._recv()

        self._state = state

        reward = self._compute_reward(state, prev_player, prev_enemies)
        if action != 10:
            new_e = state.get("game_state", {}).get(
                "combat_state", {}).get("player", {}).get("energy", -1)
            old_e = prev_player.get("energy", -1)
            if new_e == old_e:
                reward -= 0.1

        ended = state.get("game_state", {}).get("room_phase") != "COMBAT"
        return self._build_obs(state), reward, ended, False, self._build_info(state)

    def _build_obs(self, state):
        gs = state.get("game_state", {})
        combat = gs.get("combat_state", {})
        player = combat.get("player", {})
        hand = combat.get("hand", [])
        enemies = combat.get("monsters", [])
        obs = np.zeros(self.OBS_DIM, dtype=np.float32)
        hp = float(player.get("current_hp", 0))
        mx = max(float(player.get("max_hp", 1)), 1.0)
        obs[0] = hp / mx
        obs[1] = min(float(player.get("block", 0)) / 20.0, 1.0)
        obs[2] = float(player.get("energy", 0)) / 9.0
        obs[3] = hp / mx
        for i in range(self.MAX_HAND):
            b = 4 + i * 5
            if i < len(hand):
                c = hand[i]
                obs[b + 0] = 1.0
                obs[b + 1] = float(c.get("cost", 0)) / 3.0
                obs[b + 2] = 1.0 if c.get("type") == "ATTACK" else 0.0
                obs[b + 3] = 1.0 if c.get("type") == "SKILL" else 0.0
                obs[b + 4] = 1.0 if c.get("is_playable") else 0.0
        for i in range(self.MAX_MONSTERS):
            b = 54 + i * 4
            if i < len(enemies) and not enemies[i].get("is_gone", False):
                e = enemies[i]
                eh = float(e.get("current_hp", 0))
                em = max(float(e.get("max_hp", 1)), 1.0)
                obs[b + 0] = 1.0
                obs[b + 1] = eh / em
                obs[b + 2] = min(float(e.get("block", 0)) / 20.0, 1.0)
                obs[b + 3] = 1.0 if e.get("intent") == "ATTACK" else 0.0
        obs[74] = min(len(combat.get("draw_pile", [])) / 20.0, 1.0)
        obs[75] = min(len(combat.get("discard_pile", [])) / 20.0, 1.0)
        obs[76] = float(gs.get("floor", 0)) / 50.0
        obs[77] = min(self._turn_count / 10.0, 1.0)
        return obs

    def action_masks(self):
        if self._state is None:
            m = np.zeros(11, dtype=bool)
            m[10] = True
            return m
        player = self._state.get("game_state", {}).get(
            "combat_state", {}).get("player", {})
        energy = player.get("energy", 0) if isinstance(player, dict) else 0
        hand = self._state.get("game_state", {}).get(
            "combat_state", {}).get("hand", [])
        m = np.zeros(11, dtype=bool)
        for i in range(10):
            if i < len(hand):
                c = hand[i]
                m[i] = c.get("is_playable", False) and c["cost"] <= energy
        m[10] = True
        return m

    def _compute_reward(self, state, prev_player, prev_enemies):
        r = 0.0
        player = state.get("game_state", {}).get(
            "combat_state", {}).get("player", {})
        enemies = state.get("game_state", {}).get(
            "combat_state", {}).get("monsters", [])
        hp = player.get("current_hp", 0) if isinstance(player, dict) else 0
        if prev_enemies and enemies:
            now = sum(e.get("current_hp", 0) for e in enemies if not e.get("is_gone"))
            prev = sum(e.get("current_hp", 0) for e in prev_enemies if not e.get("is_gone"))
            r += (prev - now) * 0.5
        if prev_player:
            r += (hp - prev_player.get("current_hp", 0)) / max(
                prev_player.get("max_hp", 1), 1) * 5.0
        if state.get("game_state", {}).get("room_phase") != "COMBAT":
            r += 20.0 if hp > 0 else -20.0
        return float(r)

    def _build_info(self, state):
        player = state.get("game_state", {}).get(
            "combat_state", {}).get("player", {})
        return {
            "action_mask": self.action_masks(),
            "hp": player.get("current_hp", 0) if isinstance(player, dict) else 0,
            "max_hp": player.get("max_hp", 0) if isinstance(player, dict) else 0,
            "energy": player.get("energy", 0) if isinstance(player, dict) else 0,
            "hand_size": len(state.get("game_state", {}).get(
                "combat_state", {}).get("hand", [])),
            "floor": state.get("game_state", {}).get("floor", 0),
        }

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
