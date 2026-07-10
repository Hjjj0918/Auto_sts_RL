"""
Passive observer — receives game state and prints its structure.
Used to understand what fields are available for the Gym observation vector.
"""
import socket
import json

HOST = "127.0.0.1"
PORT = 9339

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(300.0)
sock.connect((HOST, PORT))
print("Connected. Observing game state structure...\n")

seen_combat = False

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

    gs = state.get("game_state", {})
    combat = gs.get("combat_state", {})
    player = combat.get("player", {})
    hand = combat.get("hand", [])
    monsters = combat.get("monsters", [])
    draw_pile = combat.get("draw_pile", [])
    discard_pile = combat.get("discard_pile", [])
    cmds = state.get("available_commands", [])

    # Only print during combat (player's turn).
    if "play" in cmds and not seen_combat:
        seen_combat = True

        print("=" * 60)
        print("COMBAT STATE STRUCTURE")
        print("=" * 60)

        # Player stats.
        print(f"\n--- Player ---")
        for k, v in player.items():
            if not isinstance(v, (list, dict)):
                print(f"  {k}: {v}")

        # Powers.
        powers = player.get("powers", [])
        if powers:
            print(f"\n--- Powers ({len(powers)}) ---")
            for p in powers[:5]:
                print(f"  {p.get('name')}: amount={p.get('amount')}")

        # Hand.
        print(f"\n--- Hand ({len(hand)} cards) ---")
        for i, c in enumerate(hand[:5]):
            print(f"  [{i}] {c['name']} cost={c['cost']} "
                  f"playable={c.get('is_playable')} target={c.get('has_target')} "
                  f"type={c.get('type')}")

        # Monsters.
        print(f"\n--- Monsters ({len(monsters)}) ---")
        for m in monsters:
            print(f"  {m.get('name')}: hp={m.get('current_hp')}/{m.get('max_hp')} "
                  f"block={m.get('block')} intent={m.get('intent')} "
                  f"gone={m.get('is_gone')}")

        # Draw / Discard piles.
        print(f"\n--- Piles ---")
        print(f"  draw: {len(draw_pile)}  discard: {len(discard_pile)}")

        # Global game info.
        print(f"\n--- Global ---")
        for k in ["current_hp", "max_hp", "gold", "floor", "act", "class"]:
            if k in gs:
                print(f"  {k}: {gs[k]}")

        print(f"\n--- Available Commands ---")
        print(f"  {cmds}")

        print(f"\n--- Other game_state keys ---")
        for k in gs:
            if k not in ["combat_state", "current_hp", "max_hp", "gold",
                         "floor", "act", "class", "relics", "deck",
                         "potions", "map", "screen_state"]:
                print(f"  {k}: {type(gs[k]).__name__}")

        # Stop after first combat view.
        print("\n(Structure captured. Press Ctrl+C to exit, or keep running.)")

    # Auto-reply to keep game moving.
    if "play" in cmds or "end" in cmds:
        sock.sendall(b"end\n")
    else:
        sock.sendall(b"state\n")
