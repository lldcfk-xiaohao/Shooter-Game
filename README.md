# TopDown Shooter v1

A top-down shooter game built with Python & Pygame, featuring multiple game modes, boss fights, an account system, and a companion cheat tool.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Pygame](https://img.shields.io/badge/Pygame-2.x-green)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

## Features

- **10 Levels** with increasing difficulty — survive waves of enemies across varied maps
- **2 Boss Fights** (Level 5 & Level 10) with multiple attack patterns
- **4 Game Modes**: Normal, Hard, Endless, Speedrun
- **Cover System**: Hide behind obstacles for tactical advantage
- **Account System**: Register / Login to track progress; offline mode available
- **Companion Cheat Tool**: Real-time parameter tweaking via shared JSON config
- **Procedural Sound Effects**: All sounds generated in code — no external audio files needed
- **Particle Effects**: Explosions, bullet trails, boss death animations
- **800x600 Windowed** — lightweight and runs on any machine
- **Standalone EXE**: Pre-built executables included in `/dist`

## Quick Start

### Prerequisites

- **Python 3.10+** (tested on 3.11)
- **Pygame** (`pip install pygame`)

### Option A: Run from Source

```bash
# Clone the repository
git clone https://github.com/lldcfk-xiaohao/Shooter-Game.git
cd Shooter-Game

# Install dependencies
pip install pygame

# Launch the game
python shooter.py

# Launch the cheat tool (optional, in a separate terminal)
python cheat_tool.py
```

### Option B: Run EXE directly (Windows, no Python required)

1. Download the latest release or build from source
2. Open the `/dist` folder
3. Double-click `TopDown-Shooter.exe` to start the game
4. Double-click `Shooter-CheatTool.exe` to open the cheat tool (optional)

> Note: Both EXEs must be kept in the same folder.

Or use the included batch files (Windows):

- `启动游戏.bat` — Auto-installs pygame and launches the game
- `启动修改器.bat` — Launches the cheat tool

## Controls

| Key       | Action     |
|-----------|------------|
| WASD      | Move       |
| Mouse     | Aim        |
| Left Click| Shoot      |
| R         | Reload     |
| ESC       | Pause      |

## Game Modes

| Mode     | Description                                                |
|----------|------------------------------------------------------------|
| NORMAL   | Standard difficulty — the intended experience              |
| HARD     | 2x enemy HP, 1.4x enemy speed — for veterans               |
| ENDLESS  | No level cap, difficulty keeps scaling — how far can you go?|
| SPEEDRUN | 30 seconds per level — beat the clock or lose!             |

## Account System

- **Register** a new account or **Login** with existing credentials
- **Offline Mode**: Play without an account, limited to Levels 1–5
- Player data stored locally in `users.json`

## Cheat Tool

A standalone Tkinter application that communicates with the game via `cheat_cfg.json`.

### Two Access Levels

| Feature                    | Full Mode (Login) | Trial Mode (No Login) |
|---------------------------|:------------------:|:---------------------:|
| HP / Max HP / Invincibility    | :white_check_mark: | :x: |
| Magazine Size                  | :white_check_mark: | :x: |
| Fire Rate                       | :white_check_mark: | :x: |
| Bullet Size / Damage           | :white_check_mark: | :x: |
| Bullet Speed                   | :white_check_mark: | :white_check_mark: *(capped)* |
| Player Speed                   | :white_check_mark: | :white_check_mark: *(capped at 15)* |
| Reload Speed                   | :white_check_mark: | :x: |
| Infinite Ammo                  | :white_check_mark: | :white_check_mark: |
| Teleport to Center            | :white_check_mark: | :x: |
| Kill All Enemies              | :white_check_mark: | :x: |
| Full Restore (HP + Ammo)      | :white_check_mark: | :x: |

**Login credentials for full mode**: Username `ADMIN`, Password `3kau`

### Usage

1. Start the game first
2. Launch `cheat_tool.py` (or `Shooter-CheatTool.exe`)
3. Adjust parameters and click **"Apply"** — changes take effect on the next frame

## Project Structure

```
.
├── shooter.py          # Main game (single-file, ~1200 lines)
├── cheat_tool.py       # Companion cheat tool (Tkinter GUI)
├── users.json          # User account data (auto-generated)
├── cheat_cfg.json      # Real-time config bridge (auto-generated)
├── dist/
│   ├── TopDown-Shooter.exe      # Standalone game executable
│   └── Shooter-CheatTool.exe    # Standalone cheat tool executable
├── 启动游戏.bat         # Windows launcher for the game
├── 启动修改器.bat        # Windows launcher for the cheat tool
├── README.md            # This file
└── LICENSE              # MIT License
```

## Technical Details

- **Rendering**: Double-buffered with logical 800x600 surface scaled to window
- **Sound**: Procedurally generated using waveform synthesis (sine, square, sawtooth, noise) — no external audio files needed
- **Communication**: Game <-> Cheat Tool via polling `cheat_cfg.json` with version counter
- **Collision**: Circle-circle distance checks
- **Boss AI**: 3 attack patterns — spread shot, radial burst, rotating cross
- **EXE Packaging**: PyInstaller `--onefile` with `sys.frozen` path detection

## Building EXE from Source

```bash
pip install pyinstaller

# Package game (no console window)
pyinstaller --onefile --noconsole --name TopDown-Shooter shooter.py

# Package cheat tool (no console window)
pyinstaller --onefile --noconsole --name Shooter-CheatTool cheat_tool.py

# Output is in the dist/ folder
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with [Pygame](https://www.pygame.org/) and [Python](https://www.python.org/).
