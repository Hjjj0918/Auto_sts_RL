"""
Headless mini Slay the Spire combat environment.

Provides an OpenAI Gym-style interface (reset / step / get_state)
designed specifically to generate (state, action) pairs for LLM fine-tuning.

Cards:
  - Strike    1-cost, 6 damage
  - Defend    1-cost, 5 block
  - Bash      2-cost, 8 damage + 1 vulnerable to enemy

Enemy:
  - Slime: 20 HP, attacks for 5 every turn.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from src.entities import Card, CardType, Character, Enemy, Intent, Status


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------
def _starter_deck() -> list[Card]:
    """Ironclad-style 3-card deck (multiplied to 9 for a full draw pile)."""
    cards = [
        Card("strike", "Strike", 1, CardType.ATTACK, "Deal 6 damage.", damage=6),
        Card("strike", "Strike", 1, CardType.ATTACK, "Deal 6 damage.", damage=6),
        Card("strike", "Strike", 1, CardType.ATTACK, "Deal 6 damage.", damage=6),
        Card("defend", "Defend", 1, CardType.SKILL, "Gain 5 block.", block=5),
        Card("defend", "Defend", 1, CardType.SKILL, "Gain 5 block.", block=5),
        Card("defend", "Defend", 1, CardType.SKILL, "Gain 5 block.", block=5),
        Card("bash", "Bash", 2, CardType.ATTACK, "Deal 8 damage. Apply 1 Vulnerable.",
             damage=8, effects={Status.VULNERABLE: 1}),
    ]
    import random
    random.shuffle(cards)
    return cards


def _create_player(hp: int = 80, max_hp: int = 80) -> Character:
    deck = _starter_deck()
    return Character(
        hp=hp, max_hp=max_hp,
        draw_pile=list(deck),
    )


def _create_slime() -> Enemy:
    e = Enemy("Slime", hp=20, max_hp=20)
    e.set_intent(Intent.ATTACK, 5)
    return e


# ---------------------------------------------------------------------------
# Action definitions
# ---------------------------------------------------------------------------
INVALID_ACTION = {"error": "invalid_action", "message": ""}


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
class HeadlessEnv:
    """Single-combat environment for LLM data generation.

    Usage
    -----
        env = HeadlessEnv()
        env.reset()
        done = False
        while not done:
            text = env.get_state()
            # ... send text to LLM, get back action dict ...
            obs, reward, done, info = env.step(action)
    """

    def __init__(self, player_hp: int = 80, player_max_hp: int = 80):
        self.player_hp_init = player_hp
        self.player_max_hp_init = player_max_hp
        self.player: Character | None = None
        self.enemy: Enemy | None = None
        self.turn: int = 0
        self.done: bool = False
        self.victory: bool = False
        self.last_action: dict | None = None

    # ------------------------------------------------------------------
    # Gym interface
    # ------------------------------------------------------------------
    def reset(self) -> str:
        """Start a new combat. Returns initial state text."""
        self.player = _create_player(self.player_hp_init, self.player_max_hp_init)
        self.enemy = _create_slime()
        self.turn = 1
        self.done = False
        self.victory = False
        self.last_action = None
        self.player.start_turn()
        return self.get_state()

    def step(self, action: dict) -> tuple[str, float, bool, dict]:
        """Execute one action. Returns (state_text, reward, done, info)."""
        if self.done:
            return self.get_state(), 0.0, True, {"reason": "combat_over"}

        reward = 0.0
        info: dict[str, Any] = {}

        cmd = action.get("action", "")
        if cmd == "end_turn":
            reward += self._enemy_turn()
            self.turn += 1
            if not self.done:
                self.player.start_turn()
        elif cmd == "play":
            idx = action.get("card_index", -1)
            target = action.get("target", "enemy")
            ok, rwd, err = self._play_card(idx, target)
            if not ok:
                info["error"] = err
            reward += rwd
        else:
            info["error"] = f"unknown action: {cmd}"

        self.last_action = action
        state = self.get_state()
        return state, reward, self.done, info

    # ------------------------------------------------------------------
    # Core mechanics
    # ------------------------------------------------------------------
    def _play_card(self, idx: int, target: str) -> tuple[bool, float, str]:
        """Play card at hand[idx]. Returns (success, reward, error_message)."""
        if idx < 0 or idx >= len(self.player.hand):
            return False, 0.0, f"invalid card index {idx}"
        card = self.player.hand[idx]
        if card.cost > self.player.energy:
            return False, 0.0, f"not enough energy (need {card.cost}, have {self.player.energy})"

        # Pay cost.
        self.player.energy -= card.cost
        self.player.play_card(idx)
        reward = 0.0

        # Apply card effects.
        if card.damage > 0:
            dmg = card.damage
            # Strength bonus.
            dmg += self.player.statuses.get(Status.STRENGTH, 0)
            # Weak debuff on player.
            if Status.WEAK in self.player.statuses:
                dmg = int(dmg * 0.75)
            dealt = self.enemy.take_damage(dmg)
            reward += float(dealt)

            # Apply on-hit effects.
            for effect, stacks in card.effects.items():
                self.enemy.statuses[effect] = self.enemy.statuses.get(effect, 0) + stacks

        if card.block > 0:
            self.player.add_block(card.block)

        # Check enemy death.
        if not self.enemy.is_alive():
            self.done = True
            self.victory = True
            reward += 10.0

        return True, reward, ""

    def _enemy_turn(self) -> float:
        """Enemy executes its intent. Returns reward (negative = damage taken)."""
        reward = 0.0

        if self.enemy.current_intent == Intent.ATTACK:
            dmg = self.enemy.intent_value
            actual = self.player.take_damage(dmg)
            reward -= float(actual)

        if not self.player.is_alive():
            self.done = True
            self.victory = False
            reward -= 10.0

        self.enemy.start_turn()
        self.enemy.set_intent(Intent.ATTACK, 5)  # Slime always attacks for 5.
        return reward

    # ------------------------------------------------------------------
    # State serialization (for LLM consumption)
    # ------------------------------------------------------------------
    def get_state(self) -> str:
        """Render the current game state as a structured text block."""
        p = self.player
        e = self.enemy
        lines = []

        # Combat header.
        lines.append(f"=== Turn {self.turn} ===")
        if self.done:
            result = "Victory!" if self.victory else "Defeat!"
            lines.append(f"Combat over: {result}")
            return "\n".join(lines)

        # Player.
        pw = ", ".join(f"{s.name}={v}" for s, v in p.statuses.items()) or "none"
        lines.append(
            f"Player  HP={p.hp}/{p.max_hp}  Block={p.block}  "
            f"Energy={p.energy}/{p.max_energy}  Statuses=[{pw}]"
        )

        # Hand.
        lines.append(f"Hand ({len(p.hand)} cards):")
        for i, c in enumerate(p.hand):
            afford = "OK" if c.cost <= p.energy else "NO"
            eff = ""
            if c.damage:
                eff += f"dmg={c.damage} "
            if c.block:
                eff += f"blk={c.block} "
            for s, v in c.effects.items():
                eff += f"{s.name}={v} "
            lines.append(f"  [{i}] {c.name}  cost={c.cost}  {eff.strip()}  [{afford}]")

        # Piles.
        lines.append(
            f"Draw pile: {len(p.draw_pile)}  |  "
            f"Discard pile: {len(p.discard_pile)}"
        )

        # Enemy.
        ew = ", ".join(f"{s.name}={v}" for s, v in e.statuses.items()) or "none"
        intent = f"{e.current_intent.name} {e.intent_value}" if e.current_intent != Intent.NONE else "?"
        lines.append(
            f"Enemy   {e.name}  HP={e.hp}/{e.max_hp}  Block={e.block}  "
            f"Intent=[{intent}]  Statuses=[{ew}]"
        )

        # Valid commands.
        lines.append("Valid actions:")
        lines.append("  {\"action\": \"play\", \"card_index\": <n>}  -- play hand[n]")
        lines.append("  {\"action\": \"end_turn\"}                    -- end turn")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    env = HeadlessEnv()
    print(env.reset(), "\n")

    # Play a few turns with a simple policy.
    for _ in range(10):
        # Pick a random affordable card or end turn.
        hand = env.player.hand
        playable = [i for i, c in enumerate(hand) if c.cost <= env.player.energy]
        if playable:
            idx = playable[0]  # always pick first playable card
            action = {"action": "play", "card_index": idx}
        else:
            action = {"action": "end_turn"}

        state, reward, done, info = env.step(action)
        print(f"Action: {action}  reward={reward}")
        print(state)
        print()
        if done:
            break
