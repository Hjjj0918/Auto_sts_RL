"""TCP bridge: Communication Mod (stdin/stdout) <-> RL agent (TCP client)."""
import sys
import json
import socket
import threading
import argparse
import traceback


class TCPBridge:
    def __init__(self, host="127.0.0.1", port=9339):
        self.host = host
        self.port = port
        self.client_sock = None
        self.lock = threading.Lock()
        self.client_ready = threading.Event()

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            server.bind((self.host, self.port))
        except OSError:
            print("[bridge] Port in use, exiting.", file=sys.stderr)
            sys.exit(0)
        server.listen(1)
        print(f"[bridge] TCP on {self.host}:{self.port}", file=sys.stderr)

        def accept():
            try:
                sock, addr = server.accept()
                print(f"[bridge] Client {addr}", file=sys.stderr)
                with self.lock:
                    self.client_sock = sock
                self.client_ready.set()
            except Exception as e:
                print(f"[bridge] Accept error: {e}", file=sys.stderr)

        threading.Thread(target=accept, daemon=True).start()

    def send_to_client(self, state):
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
                        raise ConnectionError()
                    buf += chunk
                return buf.split(b"\n")[0].decode("utf-8").strip()
            except (ConnectionError, OSError) as e:
                print(f"[bridge] Client gone: {e}", file=sys.stderr)
                try:
                    self.client_sock.close()
                except Exception:
                    pass
                self.client_sock = None
                self.client_ready.clear()
                return None

    def _is_combat(self, state):
        cmds = state.get("available_commands", [])
        return "end" in cmds or "play" in cmds

    def run(self):
        self.start_server()
        print("ready", flush=True)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                state = json.loads(line)
            except json.JSONDecodeError:
                continue
            if self._is_combat(state):
                self.client_ready.wait()
                cmd = self.send_to_client(state)
                if cmd is None:
                    self.client_ready.clear()
                    self.client_ready.wait()
                    cmd = self.send_to_client(state)
                    if cmd is None:
                        cmd = "end"
            else:
                cmd = "state"
            print(cmd, flush=True)


if __name__ == "__main__":
    try:
        p = argparse.ArgumentParser()
        p.add_argument("--port", type=int, default=9339)
        TCPBridge(port=p.parse_args().port).run()
    except Exception:
        traceback.print_exc(file=sys.stderr)
