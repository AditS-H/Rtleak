# RTleak

RTleak is a project demonstrating an attack scenario using two components: an Attacker and a Victim. The Attacker monitors and listens for specific events, while the Victim simulates a target process.

## Project Structure

```
Attacker/
    listener_monitor.py
    listener.py
Victim/
```

### Attacker
- `listener.py`: Implements the core listening logic for the attack scenario.
- `listener_monitor.py`: Monitors the listener and manages its activity.

### Victim
- Contains code simulating the victim process (details to be added).

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
4. (Optional) Run the victim code from the `Victim` folder.

## Requirements
- Python 3.x

## License
MIT License

## Author
AditS-H
