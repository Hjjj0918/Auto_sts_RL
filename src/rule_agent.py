"""
Rule-based agent for Slay the Spire combat.

Strategy (simple but effective):
  1. If enemy is attacking and we have no block → play Defend.
  2. If we can kill an enemy this turn → play hardest-hitting attack.
  3. Otherwise → play the highest damage card we can afford.
  4. If nothing playable → end turn.

Can be swapped into any environment that provides the same state JSON format.
"""
import socket
import json


HOST = "127.0.0.1"
PORT = 9339


def playable_cards(hand, energy):
    """Return list of (index, card) that can be played right now."""
    return [(i, c) for i, c in enumerate(hand)
            if c.get("is_playable") and c["cost"] <= energy]


def card_damage(card):
    """Estimate damage from a card. Very rough: parse description."""
    desc = card.get("description", "")
    import re
    nums = re.findall(r"\d+", desc)
    if nums and card.get("type") == "ATTACK":
        return int(nums[0])
    return 0


def rule_decide(state):
    """Return a command string based on the current game state."""
    gs = state.get("game_state", {})
    combat = gs.get("combat_state", {})
    player = combat.get("player", {})
    energy = player.get("energy", 0)
    block = player.get("block", 0)
    hp = player.get("current_hp", 0)
    max_hp = player.get("max_hp", 1)
    hand = combat.get("hand", [])
    enemies = combat.get("monsters", [])

    playable = playable_cards(hand, energy)
    if not playable:
        return "end"

    # Separate attacks and skills.
    attacks = [(i, c) for i, c in playable if c.get("type") == "ATTACK"]
    skills = [(i, c) for i, c in playable if c.get("type") == "SKILL"]

    # Check enemy intents.
    any_attacking = any(
        e.get("intent") == "ATTACK" and not e.get("is_gone")
        for e in enemies
    )

    # Rule 1: If enemy is attacking and we're low on block, defend.
    if any_attacking and block < 5 and skills:
        idx, card = skills[0]
        return f"play {idx}"

    # Rule 2: Can we kill something?
    for idx, card in attacks:
        dmg = card_damage(card)
        for e in enemies:
            if not e.get("is_gone") and e.get("current_hp", 99) <= dmg:
                return f"play {idx}"

    # Rule 3: Play hardest-hitting attack.
    if attacks:
        best = max(attacks, key=lambda x: card_damage(x[1]))
        return f"play {best[0]}"

    # Rule 4: Play any skill (defend before attacking when no kill possible).
    if skills:
        return f"play {skills[0][0]}"

    return "end"


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(300.0)
    sock.connect((HOST, PORT))
    print("Rule agent connected.\n")

    turn = 0
    while True:
        # Read state.
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(65536)
            if not chunk:
                print("Bridge closed.")
                return
            buf += chunk
        line = buf.split(b"\n")[0].decode("utf-8", errors="replace")
        state = json.loads(line)
        turn += 1

        cmd = rule_decide(state)
        gs = state.get("game_state", {})
        combat = gs.get("combat_state", {})
        player = combat.get("player", {})
        hp = player.get("current_hp", 0)
        energy = player.get("energy", 0)
        hand = combat.get("hand", [])

        print(f"T{turn}: {cmd:>10}  HP={hp}  E={energy}  hand={len(hand)}")
        sock.sendall((cmd + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
