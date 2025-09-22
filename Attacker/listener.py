#!/usr/bin/env python3
# listener.py
import socket

LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 4444
RECV_BUFFER = 4096
RECV_TIMEOUT = 1.0  # seconds to wait while receiving command output

def start_listener():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((LISTEN_IP, LISTEN_PORT))
    s.listen(1)
    print(f"[+] Listening on {LISTEN_IP}:{LISTEN_PORT} ...")

    conn, addr = s.accept()
    print(f"[+] Connection established from {addr[0]}:{addr[1]}")
    conn.settimeout(RECV_TIMEOUT)

    try:
        while True:
            cmd = input("Shell> ")
            if not cmd:
                continue
            # send command (ensure newline so remote shells expecting it behave nicely)
            conn.sendall((cmd + "\n").encode(errors="ignore"))

            if cmd.lower().strip() == "exit":
                print("[!] Sent exit; closing connection.")
                break

            # receive loop: accumulate until timeout (means remote finished sending)
            output_parts = []
            while True:
                try:
                    data = conn.recv(RECV_BUFFER)
                    if not data:
                        # connection closed by client
                        break
                    output_parts.append(data)
                    # continue receiving until timeout triggers
                except socket.timeout:
                    break
            if output_parts:
                try:
                    print(b"".join(output_parts).decode(errors="ignore"), end="")
                except Exception:
                    print(repr(b"".join(output_parts)))
    except KeyboardInterrupt:
        print("\n[!] Listener interrupted by user.")
    finally:
        conn.close()
        s.close()

if __name__ == "__main__":
    start_listener()
