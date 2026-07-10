"""
Bridge script: Communication Mod ↔ Python RL agent.

Communication Mod launches this script as a subprocess and sends game
state as JSON over stdin. This script parses the state, picks an action,
and writes the action JSON back over stdout.

For now this is a skeleton — it just reads and prints the game state
so we can verify the communication channel works.
"""
import sys
import json


def main():
    print("STS Agent started, waiting for game state...", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            state = json.loads(line)
        except json.JSONDecodeError:
            print(f"Failed to parse: {line[:100]}", file=sys.stderr)
            continue

        # Print available keys so we can see what data the mod sends.
        print(f"Received state with keys: {sorted(state.keys())}", file=sys.stderr)

        # For now, always send a dummy action (end turn).
        # We'll replace this with actual RL inference later.
        action = {"command": "end_turn"}
        print(json.dumps(action), flush=True)


if __name__ == "__main__":
    main()
