"""
Direct stdin/stdout agent (no TCP bridge).
Configure Communication Mod command= to point to this script.
"""
import sys
import json
import random

print("ready", flush=True)
print("Direct agent started", file=sys.stderr)

turn = 0
prev_hash = None

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    state = json.loads(line)
    turn += 1

    cmds = state.get("available_commands", [])
    gs = state.get("game_state", {})
    combat = gs.get("combat_state", {})
    player = combat.get("player", {})
    energy = player.get("energy", 0) if isinstance(player, dict) else 0
    hand = combat.get("hand", [])
    enemies = combat.get("monsters", [])

    changed = "(unchanged)" if str(state) == prev_hash else ""
    prev_hash = str(state)

    if "choose" in cmds:
        alive = [j for j, e in enumerate(enemies) if not e.get("is_gone", False)]
        cmd = f"choose {random.choice(alive)}" if alive else "choose 0"
        print(f"[agent] T{turn}: {cmd}", file=sys.stderr)

    elif "play" in cmds and "end" in cmds:
        playable = [
            i for i, c in enumerate(hand)
            if c.get("is_playable", False) and c["cost"] <= energy
        ]
        if playable:
            cmd = f"play {random.choice(playable)}"
        else:
            cmd = "end"
        print(f"[agent] T{turn}: {cmd} energy={energy} hand={len(hand)} {changed}",
              file=sys.stderr)

    else:
        print(f"[agent] T{turn}: STATE cmds={cmds} {changed}", file=sys.stderr)
        cmd = "state"

    print(cmd, flush=True)
