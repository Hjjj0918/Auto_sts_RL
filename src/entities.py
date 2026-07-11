"""
Pure-Python Slay the Spire combat entities.

Card, Character, Enemy — decoupled from the environment engine
so they can be reused across different frontends (Gym, LLM agent, etc.).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import random


class CardType(Enum):
    ATTACK = "attack"
    SKILL = "skill"
    POWER = "power"


class Status(Enum):
    VULNERABLE = "vulnerable"   # takes 50% more damage
    WEAK = "weak"               # deals 25% less damage
    STRENGTH = "strength"       # +N attack damage


class Intent(Enum):
    ATTACK = "attack"
    DEFEND = "defend"
    BUFF = "buff"
    NONE = "none"


# ---------------------------------------------------------------------------
# Card
# ---------------------------------------------------------------------------
@dataclass
class Card:
    id: str
    name: str
    cost: int
    card_type: CardType
    description: str
    damage: int = 0
    block: int = 0
    # Extra effects applied on hit, e.g. {Status.VULNERABLE: 1}
    effects: dict[Status, int] = field(default_factory=dict)
    upgraded: bool = False

    def __repr__(self) -> str:
        return f"Card({self.name}, cost={self.cost}, dmg={self.damage}, blk={self.block})"


# ---------------------------------------------------------------------------
# Character (player)
# ---------------------------------------------------------------------------
@dataclass
class Character:
    hp: int
    max_hp: int
    energy: int = 3
    max_energy: int = 3
    block: int = 0
    deck: list[Card] = field(default_factory=list)
    hand: list[Card] = field(default_factory=list)
    discard_pile: list[Card] = field(default_factory=list)
    draw_pile: list[Card] = field(default_factory=list)
    statuses: dict[Status, int] = field(default_factory=dict)
    draw_per_turn: int = 5

    def take_damage(self, amount: int) -> int:
        """Apply damage after block. Returns actual HP lost."""
        if amount <= 0:
            return 0
        if self.block > 0:
            blocked = min(self.block, amount)
            self.block -= blocked
            amount -= blocked
        # Vulnerable = +50% damage (rounded down)
        if Status.VULNERABLE in self.statuses:
            amount = int(amount * 1.5)
        actual = min(amount, self.hp)
        self.hp -= actual
        return actual

    def add_block(self, amount: int):
        self.block += amount

    def gain_energy(self, amount: int):
        self.energy = min(self.energy + amount, self.max_energy)

    def start_turn(self):
        """Reset energy, clear block, draw cards."""
        self.energy = self.max_energy
        self.block = 0
        self._draw(self.draw_per_turn)
        # Tick down statuses (1 turn passes).
        self._tick_statuses()

    def _draw(self, n: int):
        """Draw n cards from draw pile, shuffling discard if needed."""
        for _ in range(n):
            if not self.draw_pile:
                if not self.discard_pile:
                    break  # no cards left at all
                self.draw_pile = list(self.discard_pile)
                self.discard_pile = []
                random.shuffle(self.draw_pile)
            self.hand.append(self.draw_pile.pop())

    def play_card(self, idx: int) -> Card:
        """Remove card at hand[idx], place in discard. Caller handles costs."""
        card = self.hand.pop(idx)
        self.discard_pile.append(card)
        return card

    def _tick_statuses(self):
        """Decrement status counters, remove expired ones."""
        expired = [s for s, v in self.statuses.items() if v <= 1]
        for s in expired:
            del self.statuses[s]
        for s in list(self.statuses):
            self.statuses[s] -= 1

    def is_alive(self) -> bool:
        return self.hp > 0


# ---------------------------------------------------------------------------
# Enemy
# ---------------------------------------------------------------------------
@dataclass
class Enemy:
    name: str
    hp: int
    max_hp: int
    block: int = 0
    statuses: dict[Status, int] = field(default_factory=dict)
    current_intent: Intent = Intent.NONE
    intent_value: int = 0  # damage amount, block amount, etc.

    def take_damage(self, amount: int) -> int:
        if amount <= 0:
            return 0
        if self.block > 0:
            blocked = min(self.block, amount)
            self.block -= blocked
            amount -= blocked
        if Status.VULNERABLE in self.statuses:
            amount = int(amount * 1.5)
        actual = min(amount, self.hp)
        self.hp -= actual
        return actual

    def add_block(self, amount: int):
        self.block += amount

    def set_intent(self, intent: Intent, value: int):
        self.current_intent = intent
        self.intent_value = value

    def start_turn(self):
        self.block = 0
        self._tick_statuses()

    def _tick_statuses(self):
        expired = [s for s, v in self.statuses.items() if v <= 1]
        for s in expired:
            del self.statuses[s]
        for s in list(self.statuses):
            self.statuses[s] -= 1

    def is_alive(self) -> bool:
        return self.hp > 0
