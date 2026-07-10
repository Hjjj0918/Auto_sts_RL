"""
TCP bridge: Communication Mod (stdin/stdout) <-> RL agent (TCP client).

Protocol:
  - Game -> bridge (stdin):  JSON game state (one line, can be very long)
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
        with self.lock:
            if self.client_sock is None:
                return None
            try:
                msg = json.dumps(state, ensure_ascii=False) + "\n"
                self.client_sock.sendall(msg.encode("utf-8"))

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

        # Handshake: the game waits for the first message before sending state.
        print("ready", flush=True)
        print("[bridge] Handshake sent", file=sys.stderr)

        msg_count = 0
        for line in sys.stdin:
            msg_count += 1
            line = line.strip()
            if not line:
                continue

            try:
                state = json.loads(line)
            except json.JSONDecodeError:
                print(f"[bridge] Msg #{msg_count}: invalid JSON, len={len(line)}",
                      file=sys.stderr)
                print(f"  first 200 chars: {line[:200]}", file=sys.stderr)
                continue

            if isinstance(state, dict):
                ks = len(state)
                # Log one-line summary: available commands + game state keys
                cmds = state.get("available_commands", [])
                gs = state.get("game_state", {})
                print(f"[bridge] Msg #{msg_count}: {ks} keys, "
                      f"cmds={cmds}, "
                      f"gs_keys={list(gs.keys())[:10] if isinstance(gs, dict) else '?'}",
                      file=sys.stderr)
            else:
                print(f"[bridge] Msg #{msg_count}: non-dict state", file=sys.stderr)

            cmd = self.send_to_client(state)
            if cmd is None:
                cmd = "end"

            print(cmd, flush=True)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--port", type=int, default=9339)
        args = parser.parse_args()
        bridge = TCPBridge(port=args.port)
        bridge.run()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
