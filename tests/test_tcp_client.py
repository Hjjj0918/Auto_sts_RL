"""
Test client for the TCP bridge.

Receives game state as JSON, sends plain-text commands.
Valid commands: end, play N, choose N, confirm, cancel, wait, proceed, potion, etc.
"""
import socket
import json

HOST = "127.0.0.1"
PORT = 9339

print(f"Connecting to bridge on {HOST}:{PORT}...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(120.0)
sock.connect((HOST, PORT))
print("Connected.\n")

turn = 0
try:
    while True:
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(65536)
            if not chunk:
                print("[client] Bridge closed connection.")
                break
            buf += chunk
        if not buf:
            break

        line = buf.split(b"\n")[0].decode("utf-8", errors="replace")
        turn += 1

        try:
            state = json.loads(line)
        except json.JSONDecodeError:
            print(f"[client] Turn {turn}: not JSON: {line[:200]}")
            continue

        print(f"\n--- Turn {turn} ---")
        print(f"  State keys ({len(state)} total):")

        for key in sorted(state.keys()):
            val = state[key]
            if isinstance(val, list):
                print(f"    {key}: list[{len(val)}]")
            elif isinstance(val, dict):
                print(f"    {key}: dict[{len(val)} keys]")
            elif isinstance(val, str) and len(str(val)) > 80:
                print(f"    {key}: str[{len(val)}] = {str(val)[:80]}...")
            else:
                print(f"    {key}: {repr(val)}")

        # Send plain-text command (not JSON).
        # "end" = end turn, "play 0" = play card at index 0.
        cmd = "end"
        sock.sendall((cmd + "\n").encode("utf-8"))
        print(f"  -> Sent: {cmd}")

except KeyboardInterrupt:
    print("\n[client] Interrupted.")
except Exception as e:
    print(f"\n[client] Error: {e}")
finally:
    sock.close()
    print("[client] Disconnected.")
