"""
LLM-powered Slay the Spire agent.

Reads game state via TCP bridge, formats it as a prompt, sends to an
OpenAI-compatible API (DeepSeek, OpenAI, etc.), parses the response
into a game command.

Usage:
  set DEEPSEEK_API_KEY=your_key_here
  python src/llm_agent.py
"""
import socket
import json
import os
import sys
import re
from openai import OpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
HOST = "127.0.0.1"
PORT = 9339

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
if not API_KEY:
    print("Set DEEPSEEK_API_KEY environment variable.", file=sys.stderr)
    sys.exit(1)

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.deepseek.com",  # DeepSeek OpenAI-compatible endpoint
)

MODEL = "deepseek-chat"  # or "deepseek-reasoner" for deep thinking

SYSTEM_PROMPT = """\
You are playing Slay the Spire. You control the player's actions in combat.
Your goal: win the fight while preserving as much HP as possible.

You will receive the current game state, and you must reply with ONE command.

Rules:
- You can only play cards that are AFFORDABLE (cost <= energy) and PLAYABLE.
- Strike deals 6 damage. Defend gives 5 block. Bash deals 8 damage + applies Vulnerable.
- "End Turn" lets the enemy attack. Use it when you have no good plays left.
- Energy resets to 3 each turn. Block resets to 0 each turn.
- Reply with EXACTLY one of:
    play <index>          -- play the card at that hand index (0-based)
    play <index> <target> -- play card at index, targeting enemy at index
    end                   -- end your turn

Reply with the action only, no other text. Example: play 2
Example: end"""


# ---------------------------------------------------------------------------
# State → prompt
# ---------------------------------------------------------------------------
def build_prompt(state: dict) -> str:
    gs = state.get("game_state", {})
    combat = gs.get("combat_state", {})
    player = combat.get("player", {})
    energy = player.get("energy", 0)
    block = player.get("block", 0)
    hp = player.get("current_hp", 0)
    max_hp = player.get("max_hp", 0)
    hand = combat.get("hand", [])
    enemies = combat.get("monsters", [])
    powers = player.get("powers", [])

    lines = [f"HP: {hp}/{max_hp} | Block: {block} | Energy: {energy}"]

    if powers:
        pw = ", ".join(f"{p['name']} x{p['amount']}" for p in powers)
        lines.append(f"Powers: {pw}")

    lines.append("Hand:")
    for i, c in enumerate(hand):
        playable = "✓" if (c.get("is_playable") and c["cost"] <= energy) else "✗"
        target = " (needs target)" if c.get("has_target") else ""
        lines.append(
            f"  [{i}] {c['name']} | cost={c['cost']} | {c['type']}{target} | {playable}"
        )

    lines.append("Enemies:")
    for i, e in enumerate(enemies):
        if e.get("is_gone"):
            continue
        block_str = f" | Block: {e['block']}" if e.get("block", 0) > 0 else ""
        lines.append(
            f"  [{i}] {e['name']} | HP: {e['current_hp']}/{e['max_hp']}{block_str} | Intent: {e.get('intent', '?')}"
        )

    lines.append("\nYour command:")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Parse LLM reply → game command
# ---------------------------------------------------------------------------
def parse_reply(text: str) -> str:
    text = text.strip().lower()
    # Try to extract just "play N" or "end" from any extra text.
    m = re.search(r"\b(end)\b", text)
    if m:
        return "end"
    m = re.search(r"play\s+(\d+)(?:\s+(\d+))?", text)
    if m:
        idx = m.group(1)
        target = m.group(2)
        if target:
            return f"play {idx} {target}"
        return f"play {idx}"
    # Fallback: treat the whole line as the command.
    return text.split("\n")[0].strip()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(300.0)
    sock.connect((HOST, PORT))
    print("LLM agent connected.\n")

    turn = 0
    history = []  # keep recent turns for context

    while True:
        # Read state from bridge.
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(65536)
            if not chunk:
                print("Bridge closed.")
                return
            buf += chunk
        line_text = buf.split(b"\n")[0].decode("utf-8", errors="replace")
        state = json.loads(line_text)
        turn += 1

        prompt = build_prompt(state)

        # Build messages: system + recent history + current state.
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in history[-4:]:  # last 2 turns (user + assistant per turn)
            messages.append(h)
        messages.append({"role": "user", "content": prompt})

        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=20,
                temperature=0.3,
            )
            reply = resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"API error: {e}", file=sys.stderr)
            reply = "end"

        cmd = parse_reply(reply)

        # Quick state summary.
        gs = state.get("game_state", {})
        combat = gs.get("combat_state", {})
        player = combat.get("player", {})
        hp = player.get("current_hp", 0)
        energy = player.get("energy", 0)

        print(f"T{turn}: {cmd:>15}  |  HP={hp}  E={energy}  |  LLM said: {reply[:60]}")

        # Update history.
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": cmd})

        # Send command to bridge.
        sock.sendall((cmd + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
