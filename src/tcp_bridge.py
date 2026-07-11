"""TCP bridge: Communication Mod <-> RL agent."""
import sys
import json
import socket
import threading
import traceback


HOST = "127.0.0.1"
PORT = 9339
client_sock = None
lock = threading.Lock()


def accept_client():
    global client_sock
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((HOST, PORT))
    except OSError:
        print(f"[bridge] port {PORT} in use, another instance running.", file=sys.stderr)
        return  # exit thread silently
    server.listen(1)
    print(f"[bridge] listening on {HOST}:{PORT}", file=sys.stderr)
    while True:
        try:
            sock, addr = server.accept()
            print(f"[bridge] client {addr}", file=sys.stderr)
            with lock:
                if client_sock:
                    try:
                        client_sock.close()
                    except Exception:
                        pass
                client_sock = sock
        except Exception as e:
            print(f"[bridge] accept: {e}", file=sys.stderr)


def forward(state):
    global client_sock
    with lock:
        if client_sock is None:
            return None
        try:
            msg = json.dumps(state, ensure_ascii=False) + "\n"
            client_sock.sendall(msg.encode("utf-8"))
            buf = b""
            while b"\n" not in buf:
                chunk = client_sock.recv(65536)
                if not chunk:
                    raise ConnectionError()
                buf += chunk
            return buf.split(b"\n")[0].decode("utf-8").strip()
        except Exception as e:
            print(f"[bridge] client err: {e}", file=sys.stderr)
            try:
                client_sock.close()
            except Exception:
                pass
            client_sock = None
            return None


def main():
    threading.Thread(target=accept_client, daemon=True).start()
    print("ready", flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            state = json.loads(line)
        except json.JSONDecodeError:
            continue

        cmds = state.get("available_commands", [])
        in_combat = "play" in cmds or "end" in cmds or "choose" in cmds

        if in_combat:
            cmd = forward(state)
        else:
            # Forward non-combat state too, so env can control flow.
            cmd = forward(state)
        if cmd is None:
            cmd = "state"
        print(cmd, flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
