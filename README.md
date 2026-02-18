# Tripo Tools

Image-to-3D and Text-to-3D generation using [Tripo AI](https://tripo3d.ai).

## Installation

```bash
# Basic (CLI only)
pip install tripo-tools

# With desktop GUI (PySide6)
pip install tripo-tools[gui]

# With web interface (Gradio)
pip install tripo-tools[web]

# Everything
pip install tripo-tools[all]
```

### From source

```bash
git clone https://github.com/Obsolete-Robot/tripo-tools.git
cd tripo-tools
pip install -e .[all]
```

## Setup

Get your API key from [platform.tripo3d.ai](https://platform.tripo3d.ai)

```bash
export TRIPO_API_KEY=tsk_your_key_here
```

## Usage

### CLI

```bash
# Image to 3D
tripo --image photo.png --output model.glb

# Text to 3D
tripo --prompt "a wooden barrel" --output barrel.glb

# Multiple views (better geometry)
tripo --multiview front.png back.png left.png right.png --output model.glb

# Check credits
tripo --balance

# Different format
tripo --image photo.png --output model.fbx --format fbx
```

### Web Interface (Gradio)

```bash
tripo-web
```

Open http://localhost:7860 in your browser.

Options:
- `--port 8080` — different port
- `--share` — create public link
- `--host 0.0.0.0` — allow LAN access

### Desktop GUI (PySide6)

```bash
tripo-gui
```

### Python API

```python
from tripo_tools import TripoClient

client = TripoClient("tsk_your_key")

# Image to 3D
client.image_to_3d("photo.png", "model.glb")

# Text to 3D
client.text_to_3d("a wooden barrel", "barrel.glb")

# Multiple views
client.multiview_to_3d(
    ["front.png", "back.png", "left.png", "right.png"],
    "model.glb"
)

# With progress callback
def on_progress(percent, status):
    print(f"{percent}% — {status}")

client.image_to_3d("photo.png", "model.glb", callback=on_progress)
```

## Output Formats

- **GLB** (default) — best for web/game engines
- **FBX** — Autodesk interchange
- **OBJ** — universal, widely supported
- **STL** — 3D printing
- **USDZ** — Apple AR

## Installing Tripo-Tools with Non-Default Python

If you have multiple Python versions installed, or Python isn't in your PATH, use the `py` launcher to target a specific version. **THIS IS IMPORTANT IF YOUR PATHED PYTHON IS BELOW 3.9**

## Prerequisites

- Python 3.9+ installed (3.11 or 3.12 recommended)
- Windows `py` launcher (comes with Python installer)

## Check Available Python Versions

```batch
py --list
```

Example output:
```
 -V:3.12 *        Python 3.12
 -V:3.11          Python 3.11
 -V:3.8           Python 3.8
```

## Install Tripo-Tools

### Basic (CLI only)

```batch
py -3.11 -m pip install git+https://github.com/mberenty7/tripo-tools.git
```

### With Web UI (Gradio)

```batch
py -3.11 -m pip install "tripo-tools[web] @ git+https://github.com/mberenty7/tripo-tools.git"
```

### With Desktop GUI (PySide6)

```batch
py -3.11 -m pip install "tripo-tools[gui] @ git+https://github.com/mberenty7/tripo-tools.git"
```

### Everything

```batch
py -3.11 -m pip install "tripo-tools[all] @ git+https://github.com/mberenty7/tripo-tools.git"
```

## Running Tripo-Tools

Since the `tripo` command may not be in PATH, use the module syntax:

### CLI

```batch
py -3.11 -m tripo_tools.cli --help
py -3.11 -m tripo_tools.cli --balance
py -3.11 -m tripo_tools.cli --image photo.png --output model.glb
```

### Web UI

```batch
py -3.11 -m tripo_tools.web
```

Then open http://localhost:7860

### Desktop GUI

```batch
py -3.11 -m tripo_tools.gui
```

## Set API Key

### Per-session (temporary)

```batch
set TRIPO_API_KEY=tsk_your_key_here
py -3.11 -m tripo_tools.cli --balance
```

### Per-command

```batch
py -3.11 -m tripo_tools.cli --api-key tsk_your_key_here --balance
```

### Permanent (user environment variable)

```batch
setx TRIPO_API_KEY tsk_your_key_here
```
Then open a new terminal.

## Create a Shortcut Batch File

Save as `tripo.bat` somewhere in your PATH:

```batch
@echo off
py -3.11 -m tripo_tools.cli %*
```

Save as `tripo-web.bat`:

```batch
@echo off
py -3.11 -m tripo_tools.web %*
```

Now you can just run:

```batch
tripo --help
tripo-web
```

## Troubleshooting

### "No module named tripo_tools"

Reinstall:
```batch
py -3.11 -m pip install --force-reinstall git+https://github.com/mberenty7/tripo-tools.git
```

### "gradio not installed"

Install with web extras:
```batch
py -3.11 -m pip install gradio
```

Or reinstall with `[web]`:
```batch
py -3.11 -m pip install "tripo-tools[web] @ git+https://github.com/mberenty7/tripo-tools.git"
```

### Check what's installed

```batch
py -3.11 -m pip show tripo-tools
py -3.11 -m pip list | findstr tripo

## License

MIT
