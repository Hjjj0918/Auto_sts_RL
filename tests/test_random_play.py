"""
Random card-playing agent.
Uses hand indices: play <idx> for non-target, play <idx> <enemy_idx> for target.
Ends turn after 3 cards or when no playable cards remain.
"""
import socket
import json
import random

HOST = "127.0.0.1"
PORT = 9339
MAX_CARDS = 3

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(300.0)
sock.connect((HOST, PORT))
print("Connected.\n")

turn = 0
played = 0

while True:
    buf = b""
    while b"\n" not in buf:
        chunk = sock.recv(65536)
        if not chunk:
            print("Bridge closed.")
            break
        buf += chunk
    if not buf:
        break

    line = buf.split(b"\n")[0].decode("utf-8", errors="replace")
    state = json.loads(line)
    turn += 1

    gs = state.get("game_state", {})
    combat = gs.get("combat_state", {})
    player = combat.get("player", {})
    energy = player.get("energy", 0) if isinstance(player, dict) else 0
    hand = combat.get("hand", [])
    enemies = combat.get("monsters", [])

    # Filter affordable, playable cards.
    can_play = [
        (i, c) for i, c in enumerate(hand)
        if c.get("is_playable", False) and c["cost"] <= energy
    ]

    if can_play and played < MAX_CARDS:
        idx, card = random.choice(can_play)

        if card.get("has_target", False) and enemies:
            target = random.randrange(len(enemies))
            cmd = f"play {idx} {target}"
        elif not card.get("has_target", False):
            cmd = f"play {idx}"
        else:
            cmd = "end"

        played += 1
        print(f"T{turn}: [{card['name']}] idx={idx} cost={card['cost']} "
              f"energy={energy} → {cmd}")
    else:
        cmd = "end"
        print(f"T{turn}: end (played={played}, energy={energy}, hand={len(hand)})")
        played = 0

    sock.sendall((cmd + "\n").encode("utf-8"))
