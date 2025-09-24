# RTleak

RTleak is a project demonstrating an attack scenario using two components: an Attacker and a Victim. The Attacker monitors and listens for specific events, while the Victim simulates a target process.

## Project Structure


```
Attacker/
   listener_monitor.py
   listener.py
Victim/
   payload.py
   payload_monitor.py
```


### Attacker
- `listener.py`: Implements the core listening logic for the attack scenario.
- `listener_monitor.py`: Monitors the listener and manages its activity.

### Victim
- `payload.py`: Reverse shell with PTY support and inotify-based file monitoring. Connects to the attacker, executes commands, and can spawn an interactive shell.
- `payload_monitor.py`: Reverse shell that also spawns monitoring threads for file events (via inotifywait) and process list changes (via psutil). Sends structured alerts to the attacker.

## Usage

1. Clone the repository:
   ```powershell
   git clone https://github.com/AditS-H/Rtleak.git
   ```
2. Navigate to the project directory:
   ```powershell
   cd Rtleak
   ```

3. Run the attacker scripts from the `Attacker` folder:
   ```powershell
   python Attacker/listener.py
   python Attacker/listener_monitor.py
   ```

4. Run the victim scripts from the `Victim` folder (on the target machine):
   ```powershell
   python Victim/payload.py
   # or
   python Victim/payload_monitor.py
   ```


## Requirements
- Python 3.x
- `psutil` (for `payload_monitor.py`)
- `inotify-tools` (for file monitoring on Linux)

## License
MIT License

## Author
AditS-H
