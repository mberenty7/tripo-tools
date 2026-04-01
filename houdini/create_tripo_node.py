"""
Tripo AI SOP Node Creator for Houdini

Run this in Houdini's Python Shell to create a fully configured
Tripo AI SOP node with all parameters and a Generate button.

The node does NOT freeze Houdini — generation runs in a background
thread, and a File SOP sibling loads the mesh when done.

Usage:
    1. Open Houdini
    2. Windows > Python Shell
    3. Run:
       exec(open("C:/Users/mberenty/Documents/assetgen-tool/houdini/create_tripo_node.py").read())
    4. Set the image path or text prompt, click "Generate 3D Model"

Requires:
    - PYTHONPATH includes tripo-tools/src in houdini.env
    - TRIPO_API_KEY env var set, or enter key in the node's parameter
    - requests installed in Houdini's Python
"""

import hou

# ── Cook script ──────────────────────────────────────────────────────

COOK_SCRIPT = '''
import os
import hou

node = hou.pwd()
geo = node.geometry()

# If an upstream node is connected, read its "file" parm as the image path
inputs = node.inputs()
if inputs and inputs[0] is not None:
    upstream = inputs[0]
    file_parm = upstream.parm("file")
    if file_parm:
        upstream_path = file_parm.eval()
        if upstream_path and node.parm("image_path").eval() != upstream_path:
            node.parm("image_path").set(upstream_path)
'''

# ── Generate button callback ─────────────────────────────────────────

GENERATE_CALLBACK = '''
import os
import threading
import hou

node = kwargs["node"]

# Check for upstream input first
inputs = node.inputs()
if inputs and inputs[0] is not None:
    upstream = inputs[0]
    file_parm = upstream.parm("file")
    if file_parm:
        upstream_path = file_parm.eval()
        if upstream_path:
            node.parm("image_path").set(upstream_path)

# Determine mode
mode_idx = node.parm("mode").eval()
mode_map = ["image", "text", "multiview"]
mode = mode_map[mode_idx]

image_path = node.parm("image_path").eval()
text_prompt = node.parm("text_prompt").eval()
output_dir = node.parm("output_dir").eval()

format_items = ["glb", "fbx", "obj", "stl", "usdz"]
mesh_format = format_items[node.parm("mesh_format").eval()]

api_key = node.parm("api_key").eval() or os.environ.get("TRIPO_API_KEY", "")

# Read advanced settings
version_items = ["v3.0-20250812", "v2.5-20250123", "v2.0-20240919"]
model_version = version_items[node.parm("model_version").eval()]

style_items = ["", "person:person2cartoon", "person:person2game", "person:person2realistic", "animal:animal2cartoon"]
style_id = style_items[node.parm("style_id").eval()] or None

texture_val = bool(node.parm("texture").eval())
pbr_val = bool(node.parm("pbr").eval())
auto_size_val = bool(node.parm("auto_size").eval())
quad_val = bool(node.parm("quad").eval())

seed_val = node.parm("seed").eval()
if seed_val < 0:
    seed_val = None

texture_seed_val = node.parm("texture_seed").eval()
if texture_seed_val < 0:
    texture_seed_val = None

face_limit_val = node.parm("face_limit").eval()

tex_quality_items = ["standard", "detailed"]
texture_quality_val = tex_quality_items[node.parm("texture_quality").eval()]

tex_align_items = ["geometry", "original_image", "prefer_original_image"]
texture_alignment_val = tex_align_items[node.parm("texture_alignment").eval()]

orientation_items = ["default", "align_image"]
orientation_val = orientation_items[node.parm("orientation").eval()]

negative_prompt = node.parm("negative_prompt").eval() or None

# Validate
_valid = True

if not api_key:
    hou.ui.displayMessage("No API key. Set TRIPO_API_KEY env var or enter it in the API Key parameter.", severity=hou.severityType.Error)
    _valid = False

if _valid and mode == "image":
    if not image_path or not os.path.isfile(image_path):
        hou.ui.displayMessage("Please select a valid image file.", severity=hou.severityType.Error)
        _valid = False

if _valid and mode == "text":
    if not text_prompt:
        hou.ui.displayMessage("Please enter a text prompt.", severity=hou.severityType.Error)
        _valid = False

multiview_paths = []
if _valid and mode == "multiview":
    for pname in ["mv_front", "mv_back", "mv_left", "mv_right"]:
        p = node.parm(pname).eval()
        if p and os.path.isfile(p):
            multiview_paths.append(p)
    if len(multiview_paths) < 2:
        hou.ui.displayMessage("Multiview mode needs at least 2 images (front/back/left/right).", severity=hou.severityType.Error)
        _valid = False

if _valid:
    if not output_dir:
        output_dir = hou.text.expandString("$HIP/tripo_output")

    if mode == "image":
        name = os.path.splitext(os.path.basename(image_path))[0]
    elif mode == "text":
        words = text_prompt.strip().split()[:3]
        name = "_".join(words).replace("/", "_").replace("\\\\", "_")
    else:
        name = "multiview_model"

    output_path = os.path.join(output_dir, name, "model." + mesh_format)
    node_path = node.path()

    def _run():
        import hdefereval
        from tripo_tools.client import TripoClient

        def set_status(msg):
            def _do():
                n = hou.node(node_path)
                if n:
                    n.parm("status").set(msg)
            hdefereval.executeDeferred(_do)

        def set_status_bar(msg, sev=hou.severityType.ImportantMessage):
            hdefereval.executeDeferred(
                lambda: hou.ui.setStatusMessage(msg, severity=sev)
            )

        set_status("Connecting...")
        set_status_bar("Tripo: Starting generation for " + name + "...")

        try:
            client = TripoClient(api_key)
        except Exception as exc:
            set_status("Auth error")
            hdefereval.executeDeferred(
                lambda: hou.ui.displayMessage(str(exc), title="Tripo Auth Error", severity=hou.severityType.Error)
            )
            return

        def on_progress(progress, status):
            set_status("Generating... " + str(progress) + "%")
            set_status_bar("Tripo: " + name + " - " + str(progress) + "% " + str(status))

        set_status("Generating...")

        try:
            if mode == "image":
                client.image_to_3d(
                    image_path, output_path, mesh_format, on_progress,
                    model_version=model_version, style_id=style_id,
                    texture=texture_val, pbr=pbr_val, seed=seed_val,
                    orientation=orientation_val, texture_seed=texture_seed_val,
                    texture_quality=texture_quality_val,
                    texture_alignment=texture_alignment_val,
                    face_limit=face_limit_val, auto_size=auto_size_val,
                    quad=quad_val,
                )
            elif mode == "text":
                client.text_to_3d(
                    text_prompt, output_path, mesh_format, on_progress,
                    model_version=model_version, style_id=style_id,
                    texture=texture_val, pbr=pbr_val, seed=seed_val,
                    texture_seed=texture_seed_val,
                    texture_quality=texture_quality_val,
                    face_limit=face_limit_val, auto_size=auto_size_val,
                    quad=quad_val, negative_prompt=negative_prompt,
                )
            elif mode == "multiview":
                client.multiview_to_3d(
                    multiview_paths, output_path, mesh_format, on_progress,
                    model_version=model_version, texture=texture_val,
                    pbr=pbr_val, seed=seed_val, orientation=orientation_val,
                    texture_seed=texture_seed_val,
                    texture_quality=texture_quality_val,
                    texture_alignment=texture_alignment_val,
                    face_limit=face_limit_val, auto_size=auto_size_val,
                    quad=quad_val,
                )
        except Exception as exc:
            set_status("Error: " + str(exc))
            set_status_bar("Tripo: Error", hou.severityType.Error)
            hdefereval.executeDeferred(
                lambda: hou.ui.displayMessage(str(exc), title="Tripo Error", severity=hou.severityType.Error)
            )
            return

        mesh_path = output_path.replace("\\\\", "/")

        def _finish():
            n = hou.node(node_path)
            if n:
                n.parm("status").set("Done!")
                n.parm("mesh_file").set(mesh_path)

                parent = n.parent()
                loader_name = "tripo_result"
                loader = parent.node(loader_name)
                if not loader:
                    loader = parent.createNode("file", loader_name)
                    loader.setPosition(n.position() + hou.Vector2(3, 0))
                loader.parm("file").set(mesh_path)
                loader.parm("reload").pressButton()
                loader.setDisplayFlag(True)
                loader.setRenderFlag(True)
                parent.layoutChildren()

            hou.ui.setStatusMessage(
                "Tripo: " + name + " complete!",
                severity=hou.severityType.Message,
            )

        hdefereval.executeDeferred(_finish)

    node.parm("status").set("Starting...")
    node.parm("mesh_file").set("")
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
'''


# ── Create the node ──────────────────────────────────────────────────

def create_tripo_node():
    """Create a fully configured Tripo AI SOP node."""

    obj = hou.node("/obj")

    geo_name = "tripo"
    geo_node = obj.node(geo_name)
    if not geo_node:
        geo_node = obj.createNode("geo", geo_name)
        geo_node.moveToGoodPosition()
        for child in geo_node.children():
            child.destroy()

    py_sop = geo_node.createNode("python", "tripo_generate")
    py_sop.parm("python").set(COOK_SCRIPT)
    py_sop.setDisplayFlag(True)
    py_sop.setRenderFlag(True)

    # ── Add spare parameters ──────────────────────────────────────
    ptg = py_sop.parmTemplateGroup()

    # --- API Key ---
    key_folder = hou.FolderParmTemplate(
        "key_folder", "API Key",
        folder_type=hou.folderType.Simple,
    )

    key_folder.addParmTemplate(hou.StringParmTemplate(
        "api_key", "Tripo API Key", 1,
        default_value=("",),
        help="Tripo API key (or set TRIPO_API_KEY env var). Get one at platform.tripo3d.ai",
    ))

    ptg.append(key_folder)

    # --- Input ---
    input_folder = hou.FolderParmTemplate(
        "input_folder", "Input",
        folder_type=hou.folderType.Simple,
    )

    input_folder.addParmTemplate(hou.MenuParmTemplate(
        "mode", "Mode",
        menu_items=["image_to_model", "text_to_model", "multiview_to_model"],
        menu_labels=["Image to 3D", "Text to 3D", "Multiview to 3D"],
        default_value=0,
        help="Generation mode",
    ))

    input_folder.addParmTemplate(hou.StringParmTemplate(
        "image_path", "Image", 1,
        default_value=("",),
        string_type=hou.stringParmType.FileReference,
        file_type=hou.fileType.Image,
        help="Input image file (for Image to 3D mode)",
    ))

    input_folder.addParmTemplate(hou.StringParmTemplate(
        "text_prompt", "Text Prompt", 1,
        default_value=("",),
        help="Text description (for Text to 3D mode)",
    ))

    input_folder.addParmTemplate(hou.StringParmTemplate(
        "output_dir", "Output Directory", 1,
        default_value=("$HIP/tripo_output",),
        string_type=hou.stringParmType.FileReference,
        file_type=hou.fileType.Directory,
    ))

    input_folder.addParmTemplate(hou.SeparatorParmTemplate("sep_mv"))

    input_folder.addParmTemplate(hou.LabelParmTemplate(
        "mv_label", "Multiview Images",
    ))

    mv_front = hou.StringParmTemplate(
        "mv_front", "Front", 1, default_value=("",),
        string_type=hou.stringParmType.FileReference,
        file_type=hou.fileType.Image,
        help="Front view image (Multiview mode)",
    )
    mv_front.setConditional(hou.parmCondType.HideWhen, "{ mode != 2 }")
    input_folder.addParmTemplate(mv_front)

    mv_back = hou.StringParmTemplate(
        "mv_back", "Back", 1, default_value=("",),
        string_type=hou.stringParmType.FileReference,
        file_type=hou.fileType.Image,
        help="Back view image (Multiview mode)",
    )
    mv_back.setConditional(hou.parmCondType.HideWhen, "{ mode != 2 }")
    input_folder.addParmTemplate(mv_back)

    mv_left = hou.StringParmTemplate(
        "mv_left", "Left", 1, default_value=("",),
        string_type=hou.stringParmType.FileReference,
        file_type=hou.fileType.Image,
        help="Left view image (Multiview mode)",
    )
    mv_left.setConditional(hou.parmCondType.HideWhen, "{ mode != 2 }")
    input_folder.addParmTemplate(mv_left)

    mv_right = hou.StringParmTemplate(
        "mv_right", "Right", 1, default_value=("",),
        string_type=hou.stringParmType.FileReference,
        file_type=hou.fileType.Image,
        help="Right view image (Multiview mode)",
    )
    mv_right.setConditional(hou.parmCondType.HideWhen, "{ mode != 2 }")
    input_folder.addParmTemplate(mv_right)

    ptg.append(input_folder)

    # --- Settings ---
    settings_folder = hou.FolderParmTemplate(
        "settings_folder", "Settings",
        folder_type=hou.folderType.Simple,
    )

    settings_folder.addParmTemplate(hou.MenuParmTemplate(
        "mesh_format", "Format",
        menu_items=["glb", "fbx", "obj", "stl", "usdz"],
        menu_labels=["GLB", "FBX", "OBJ", "STL", "USDZ"],
        default_value=0,
        help="Output mesh file format",
    ))

    settings_folder.addParmTemplate(hou.MenuParmTemplate(
        "model_version", "Model Version",
        menu_items=["v3.0-20250812", "v2.5-20250123", "v2.0-20240919"],
        menu_labels=["v3.0 (Latest)", "v2.5", "v2.0"],
        default_value=0,
        help="Tripo model version",
    ))

    settings_folder.addParmTemplate(hou.MenuParmTemplate(
        "style_id", "Style",
        menu_items=["none", "person:person2cartoon", "person:person2game", "person:person2realistic", "animal:animal2cartoon"],
        menu_labels=["(none)", "Person: Cartoon", "Person: Game", "Person: Realistic", "Animal: Cartoon"],
        default_value=0,
        help="Style preset for specialized generation",
    ))

    settings_folder.addParmTemplate(hou.IntParmTemplate(
        "face_limit", "Face Limit", 1,
        default_value=(-1,),
        min=-1, max=500000,
        help="Target face count (-1 = auto)",
    ))

    settings_folder.addParmTemplate(hou.SeparatorParmTemplate("sep_tex"))

    settings_folder.addParmTemplate(hou.ToggleParmTemplate(
        "texture", "Generate Texture", default_value=True,
        help="Generate texture maps",
    ))

    settings_folder.addParmTemplate(hou.ToggleParmTemplate(
        "pbr", "Generate PBR", default_value=True,
        help="Generate PBR materials (metallic/roughness/normal)",
    ))

    settings_folder.addParmTemplate(hou.MenuParmTemplate(
        "texture_quality", "Texture Quality",
        menu_items=["standard", "detailed"],
        menu_labels=["Standard", "Detailed"],
        default_value=0,
        help="Texture quality tier",
    ))

    settings_folder.addParmTemplate(hou.MenuParmTemplate(
        "texture_alignment", "Texture Alignment",
        menu_items=["geometry", "original_image", "prefer_original_image"],
        menu_labels=["Geometry", "Original Image", "Prefer Original Image"],
        default_value=0,
        help="How texture maps align to the mesh",
    ))

    settings_folder.addParmTemplate(hou.SeparatorParmTemplate("sep_geo"))

    settings_folder.addParmTemplate(hou.MenuParmTemplate(
        "orientation", "Orientation",
        menu_items=["default", "align_image"],
        menu_labels=["Default", "Align to Image"],
        default_value=0,
        help="Model orientation (image modes only)",
    ))

    settings_folder.addParmTemplate(hou.ToggleParmTemplate(
        "auto_size", "Auto Size", default_value=True,
        help="Auto-determine mesh scale/proportions",
    ))

    settings_folder.addParmTemplate(hou.ToggleParmTemplate(
        "quad", "Quad Mesh", default_value=False,
        help="Generate quad mesh topology instead of triangles",
    ))

    settings_folder.addParmTemplate(hou.SeparatorParmTemplate("sep_seed"))

    settings_folder.addParmTemplate(hou.IntParmTemplate(
        "seed", "Geometry Seed", 1,
        default_value=(-1,),
        min=-1, max=999999999,
        help="Random seed for geometry (-1 = random)",
    ))

    settings_folder.addParmTemplate(hou.IntParmTemplate(
        "texture_seed", "Texture Seed", 1,
        default_value=(-1,),
        min=-1, max=999999999,
        help="Random seed for texture (-1 = random)",
    ))

    settings_folder.addParmTemplate(hou.StringParmTemplate(
        "negative_prompt", "Negative Prompt", 1,
        default_value=("",),
        help="Negative prompt (text-to-3D mode only)",
    ))

    ptg.append(settings_folder)

    # --- Generate ---
    gen_folder = hou.FolderParmTemplate(
        "gen_folder", "Generate",
        folder_type=hou.folderType.Simple,
    )

    gen_btn = hou.ButtonParmTemplate(
        "generate", "Generate 3D Model",
        script_callback=GENERATE_CALLBACK,
        script_callback_language=hou.scriptLanguage.Python,
        help="Click to start 3D model generation",
    )
    gen_folder.addParmTemplate(gen_btn)

    gen_folder.addParmTemplate(hou.SeparatorParmTemplate("sep_status"))

    gen_folder.addParmTemplate(hou.StringParmTemplate(
        "status", "Status", 1, default_value=("Ready",),
    ))

    gen_folder.addParmTemplate(hou.StringParmTemplate(
        "mesh_file", "Mesh File", 1, default_value=("",),
        string_type=hou.stringParmType.FileReference,
        file_type=hou.fileType.Geometry,
    ))

    ptg.append(gen_folder)

    # Apply
    py_sop.setParmTemplateGroup(ptg)

    # Layout
    geo_node.layoutChildren()
    py_sop.setSelected(True, clear_all_selected=True)
    py_sop.setDisplayFlag(True)

    print("=" * 60)
    print("Tripo AI node created: /obj/tripo/tripo_generate")
    print("=" * 60)
    print()
    print("How to use:")
    print("  1. Enter your Tripo API key (or set TRIPO_API_KEY env var)")
    print("  2. Select mode: Image to 3D or Text to 3D")
    print("  3. Set the Image path or Text Prompt")
    print("     (or wire a File SOP into the input)")
    print("  4. Click 'Generate 3D Model'")
    print()
    print("  Houdini stays responsive during generation.")
    print("  The mesh auto-loads via a File SOP when done.")
    print()

    return py_sop


# ── Run ──
create_tripo_node()
