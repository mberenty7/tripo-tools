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
```

## Tripo AI — Houdini Node

A Houdini SOP node for generating 3D models from images, text prompts, or multiview turnarounds using the [Tripo AI](https://tripo3d.ai) API.

Runs generation in a background thread so Houdini stays fully responsive during the ~60–120 second API call. The generated mesh auto-loads into the viewport when done.

---

### Setup

### 1. Install `requests` into Houdini's Python (one-time)

```powershell
& "C:\Program Files\Side Effects Software\Houdini 21.0.xxx\python\python.exe" -m pip install requests
```

Replace `xxx` with your exact Houdini version number.

### 2. Add to `houdini.env`

Add the `tripo-tools/src` path to your `PYTHONPATH` in `~/Documents/houdini21.0/houdini.env`:

```
PYTHONPATH = "C:/Users/mberenty/Documents/Gits/tripo-tools/src;"
```

If you already have a `PYTHONPATH`, append it with a semicolon:

```
PYTHONPATH = "C:/your/other/path;C:/Users/mberenty/Documents/Gits/tripo-tools/src;"
```

### 3. Restart Houdini

The `PYTHONPATH` change requires a restart to take effect.

### 4. Get a Tripo API key

Sign up at [platform.tripo3d.ai](https://platform.tripo3d.ai) and copy your API key (starts with `tsk_...`).

You can either:
- Enter it in the node's **API Key** parameter each session
- Set it as a persistent environment variable so you don't have to re-enter it:
  ```powershell
  [System.Environment]::SetEnvironmentVariable("TRIPO_API_KEY", "tsk_your_key_here", "User")
  ```

---

## Creating the Node

Open Houdini's Python Shell (**Windows > Python Shell**) and run:

```python
exec(open("C:/Users/mberenty/Documents/Gits/tripo-tools/houdini/create_tripo_node.py").read())
```

This creates `/obj/tripo/tripo_generate` — a Python SOP with all Tripo parameters in the Parameter Editor.

To recreate from scratch (delete old node first):

```python
n = hou.node("/obj/tripo")
if n: n.destroy()
exec(open("C:/Users/mberenty/Documents/Gits/tripo-tools/houdini/create_tripo_node.py").read())
```

---

## Usage

### Image to 3D

1. Set **Mode** to "Image to 3D"
2. Set the **Image** path (browse for a PNG/JPG)
3. Adjust settings (model version, face limit, format, etc.)
4. Click **"Generate 3D Model"**
5. The mesh auto-loads in the viewport when done

You can also wire a **File SOP** (pointing to your image) into the node's input instead of setting the path manually:

```
[File SOP: character.png] ──→ [tripo_generate] ─── [tripo_result] (mesh appears here)
```

### Text to 3D

1. Set **Mode** to "Text to 3D"
2. Enter a **Text Prompt** (e.g. "a weathered wooden barrel")
3. Optionally set a **Negative Prompt** to exclude unwanted features
4. Click **"Generate 3D Model"**

### Multiview to 3D

1. Set **Mode** to "Multiview to 3D"
2. Set the **Front**, **Back**, **Left**, and **Right** image paths (minimum 2 required)
3. Click **"Generate 3D Model"**

The multiview image pickers only appear when "Multiview to 3D" is selected.

---

## Node Parameters

### API Key

| Parameter | Description |
|-----------|-------------|
| **Tripo API Key** | Your API key (or set `TRIPO_API_KEY` env var) |

### Input

| Parameter | Description |
|-----------|-------------|
| **Mode** | Image to 3D, Text to 3D, or Multiview to 3D |
| **Image** | Input image file picker (Image mode) |
| **Text Prompt** | Text description (Text mode) |
| **Output Directory** | Where generated files are saved (default: `$HIP/tripo_output`) |
| **Front / Back / Left / Right** | Multiview image pickers (only visible in Multiview mode) |

### Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| **Format** | GLB | Output format: GLB, FBX, OBJ, STL, USDZ |
| **Model Version** | v3.0 (Latest) | Tripo model: v3.0, v2.5, v2.0 |
| **Style** | (none) | Style preset: Person Cartoon/Game/Realistic, Animal Cartoon |
| **Face Limit** | -1 (auto) | Target face count, up to 500,000 |
| **Generate Texture** | On | Generate texture maps |
| **Generate PBR** | On | Generate PBR materials (metallic/roughness/normal) |
| **Texture Quality** | Standard | Standard or Detailed |
| **Texture Alignment** | Geometry | How textures map: Geometry, Original Image, Prefer Original Image |
| **Orientation** | Default | Model orientation: Default or Align to Image |
| **Auto Size** | On | Auto-determine mesh scale/proportions |
| **Quad Mesh** | Off | Generate quad topology instead of triangles |
| **Geometry Seed** | -1 (random) | Random seed for geometry (0–999999999) |
| **Texture Seed** | -1 (random) | Random seed for texture (0–999999999) |
| **Negative Prompt** | *(empty)* | Negative prompt — Text to 3D mode only |

### Generate

| Parameter | Description |
|-----------|-------------|
| **Generate 3D Model** | Button — starts generation in background thread |
| **Status** | Shows current progress (Ready → Generating... 45% → Done!) |
| **Mesh File** | Auto-filled with the path to the generated mesh |

---

## How It Works

1. You click **Generate 3D Model**
2. The image is uploaded to Tripo's API and a generation task is created
3. The node polls for progress every 3 seconds — status updates in the Parameter Editor and Houdini's status bar
4. When done, the model is downloaded to `{output_dir}/{image_name}/model.{format}`
5. A **File SOP** sibling node (`tripo_result`) is automatically created to load the mesh
6. The mesh appears in the viewport immediately

Houdini stays fully responsive throughout — the API calls run in a background thread using `hdefereval.executeDeferred()` for safe UI updates.

---

## Dependencies

- **[tripo-tools](https://github.com/mberenty7/tripo-tools)** — Python client library for the Tripo API (`tripo_tools.client.TripoClient`)
- **requests** — HTTP client (installed into Houdini's Python)
- **Tripo API key** — from [platform.tripo3d.ai](https://platform.tripo3d.ai)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No API key" error | Set `TRIPO_API_KEY` env var or enter key in the node parameter |
| "Auth error" | API key is invalid or expired — get a new one from platform.tripo3d.ai |
| `ModuleNotFoundError: tripo_tools` | Check `PYTHONPATH` in `houdini.env` points to `tripo-tools/src` and restart Houdini |
| `ModuleNotFoundError: requests` | Install requests into Houdini's Python (see Setup step 1) |
| Node doesn't load mesh | Check the Status field for errors. The mesh downloads to `{output_dir}/{name}/model.glb` |
| Want to regenerate | Just click "Generate 3D Model" again — the `tripo_result` File SOP updates automatically |


## License

MIT
