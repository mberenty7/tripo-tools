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

## License

MIT
