"""
Minimal TCP connection test for Communication Mod.

The mod broadcasts game state as JSON over TCP port 9339.
This script connects, reads one state message, and prints it.

Prerequisites:
  1. Subscribe to ModTheSpire, BaseMod, CommunicationMod on Steam Workshop.
  2. Launch STS via ModTheSpire, check both mods, click Play.
  3. Start a run (any character) so the game is in an active state.
  4. Run this script: python tests/test_comm_mod.py
"""
import socket
import json

HOST = "127.0.0.1"
PORT = 9339

print(f"Connecting to Communication Mod on {HOST}:{PORT}...")

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)
    sock.connect((HOST, PORT))
    print("Connected. Waiting for game state...\n")

    # The mod sends state messages as newline-delimited JSON.
    # Read a few bytes to see what we get.
    data = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
        if b"\n" in data:
            break

    line = data.split(b"\n")[0].decode("utf-8")
    state = json.loads(line)
    print("Received game state (keys shown):")
    for key in sorted(state.keys()):
        val = state[key]
        if isinstance(val, (list, dict)):
            print(f"  {key}: {type(val).__name__} (len={len(val)})")
        else:
            print(f"  {key}: {repr(val)[:80]}")

except ConnectionRefusedError:
    print("Connection refused. Make sure STS is running with Communication Mod enabled.")
except socket.timeout:
    print("Timed out waiting for data. Start a run in STS first, then retry.")
except Exception as e:
    print(f"Error: {e}")
finally:
    sock.close()
    print("\nDisconnected.")
