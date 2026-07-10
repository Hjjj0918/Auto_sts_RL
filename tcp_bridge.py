"""
TCP bridge: Communication Mod (stdin/stdout) <-> RL agent (TCP client).

Protocol:
  - Game -> bridge (stdin):  JSON game state (one line)
  - Bridge -> game (stdout): plain-text command (e.g. "end", "play 0")
  - Bridge <-> client (TCP): JSON (both directions), newline-delimited

Usage (run by Communication Mod automatically):
  python tcp_bridge.py [--port 9339]
"""
import sys
import json
import socket
import threading
import argparse
import traceback


class TCPBridge:
    def __init__(self, host: str = "127.0.0.1", port: int = 9339):
        self.host = host
        self.port = port
        self.client_sock: socket.socket | None = None
        self.lock = threading.Lock()

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(1)
        print(f"[bridge] TCP server listening on {self.host}:{self.port}",
              file=sys.stderr)

        def accept():
            try:
                sock, addr = server.accept()
                print(f"[bridge] Client connected from {addr}", file=sys.stderr)
                with self.lock:
                    self.client_sock = sock
            except Exception as e:
                print(f"[bridge] Accept error: {e}", file=sys.stderr)

        threading.Thread(target=accept, daemon=True).start()

    def send_to_client(self, state: dict) -> str | None:
        """Send game state to RL client, return plain-text command."""
        with self.lock:
            if self.client_sock is None:
                return None
            try:
                # Forward game state as JSON.
                msg = json.dumps(state, ensure_ascii=False) + "\n"
                self.client_sock.sendall(msg.encode("utf-8"))

                # Wait for plain-text command from client.
                buf = b""
                while b"\n" not in buf:
                    chunk = self.client_sock.recv(65536)
                    if not chunk:
                        raise ConnectionError("Client disconnected")
                    buf += chunk

                return buf.split(b"\n")[0].decode("utf-8").strip()

            except (ConnectionError, OSError) as e:
                print(f"[bridge] Client error: {e}", file=sys.stderr)
                try:
                    self.client_sock.close()
                except Exception:
                    pass
                self.client_sock = None
                return None

    def run(self):
        self.start_server()

        # Handshake: game expects the first message as plain text.
        # Any non-empty message signals readiness.
        print("ready", flush=True)
        print("[bridge] Handshake sent, waiting for game state...", file=sys.stderr)

        msg_count = 0
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            msg_count += 1
            try:
                state = json.loads(line)
            except json.JSONDecodeError:
                print(f"[bridge] Msg #{msg_count}: invalid JSON (first 120 chars):",
                      file=sys.stderr)
                print(f"  {line[:120]}", file=sys.stderr)
                continue

            print(f"[bridge] Msg #{msg_count}: state ({len(state)} keys)",
                  file=sys.stderr)

            cmd = self.send_to_client(state)
            if cmd is None:
                cmd = "end"

            print(cmd, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9339)
    args = parser.parse_args()
    bridge = TCPBridge(port=args.port)
    bridge.run()
