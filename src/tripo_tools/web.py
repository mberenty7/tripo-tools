"""
Tripo Tools Web Interface (Gradio).

Usage:
    tripo-web
    tripo-web --port 8080
    tripo-web --share
"""

import argparse
import os
import sys
import logging
import tempfile
from io import StringIO
from pathlib import Path

try:
    import gradio as gr
except ImportError:
    gr = None

from .client import TripoClient, MODEL_VERSIONS, TEXTURE_OPTIONS


class LogCapture:
    """Context manager to capture tripo_tools log output to a string."""
    def __init__(self):
        self.buffer = StringIO()
        self.handler = logging.StreamHandler(self.buffer)
        self.handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
        self.logger = logging.getLogger("tripo_tools")

    def __enter__(self):
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.DEBUG)
        return self

    def __exit__(self, *args):
        self.logger.removeHandler(self.handler)

    def get_log(self):
        return self.buffer.getvalue()


def check_gradio():
    """Check if Gradio is installed."""
    if gr is None:
        print("Gradio not installed. Run: pip install gradio")
        print("Or install with web support: pip install tripo-tools[web]")
        sys.exit(1)


def generate_from_image(image_path, output_format, api_key, 
                        model_version, texture, pbr, face_limit, seed, quad, auto_size,
                        progress=None):
    """Generate 3D model from a single image."""
    if not api_key:
        return None, "❌ Error: API key required", ""
    
    if not image_path:
        return None, "❌ Error: Please upload an image", ""
    
    with LogCapture() as log:
        try:
            client = TripoClient(api_key)
            
            if progress:
                progress(0.1, desc="Uploading image...")
            
            output_path = tempfile.mktemp(suffix=f".{output_format}")
            
            def callback(prog, status):
                if progress:
                    mapped = 0.1 + 0.8 * (prog / 100)
                    progress(mapped, desc=f"Generating... {prog}%")
            
            fl = int(face_limit) if face_limit and str(face_limit).strip() else None
            sd = int(seed) if seed and str(seed).strip() else None
            
            client.image_to_3d(
                image_path, output_path, output_format, callback,
                model_version=model_version if model_version != "default" else None,
                texture=texture,
                pbr=pbr,
                face_limit=fl,
                seed=sd,
                quad=quad,
                auto_size=auto_size
            )
            
            if progress:
                progress(1.0, desc="Done!")
            
            return output_path, f"✅ Success! Generated {Path(output_path).name}", log.get_log()
        
        except Exception as e:
            return None, f"❌ Error: {str(e)}", log.get_log()


def generate_from_text(prompt, output_format, api_key,
                       model_version, texture, pbr, face_limit, seed, quad, auto_size,
                       progress=None):
    """Generate 3D model from text prompt."""
    if not api_key:
        return None, "❌ Error: API key required", ""
    
    if not prompt or not prompt.strip():
        return None, "❌ Error: Please enter a prompt", ""
    
    with LogCapture() as log:
        try:
            client = TripoClient(api_key)
            
            if progress:
                progress(0.1, desc="Creating task...")
            
            output_path = tempfile.mktemp(suffix=f".{output_format}")
            
            def callback(prog, status):
                if progress:
                    mapped = 0.1 + 0.8 * (prog / 100)
                    progress(mapped, desc=f"Generating... {prog}%")
            
            fl = int(face_limit) if face_limit and str(face_limit).strip() else None
            sd = int(seed) if seed and str(seed).strip() else None
            
            client.text_to_3d(
                prompt.strip(), output_path, output_format, callback,
                model_version=model_version if model_version != "default" else None,
                texture=texture,
                pbr=pbr,
                face_limit=fl,
                seed=sd,
                quad=quad,
                auto_size=auto_size
            )
            
            if progress:
                progress(1.0, desc="Done!")
            
            return output_path, f"✅ Success! Generated {Path(output_path).name}", log.get_log()
        
        except Exception as e:
            return None, f"❌ Error: {str(e)}", log.get_log()


def generate_from_multiview(front, back, left, right, output_format, api_key,
                            model_version, texture, pbr, face_limit, seed, quad, auto_size,
                            progress=None):
    """Generate 3D model from 4 views."""
    if not api_key:
        return None, "❌ Error: API key required", ""
    
    images = [front, back, left, right]
    if not all(images):
        return None, "❌ Error: All 4 views required (front, back, left, right)", ""
    
    with LogCapture() as log:
        try:
            client = TripoClient(api_key)
            
            if progress:
                progress(0.1, desc="Uploading images...")
            
            output_path = tempfile.mktemp(suffix=f".{output_format}")
            
            def callback(prog, status):
                if progress:
                    mapped = 0.2 + 0.7 * (prog / 100)
                    progress(mapped, desc=f"Generating... {prog}%")
            
            fl = int(face_limit) if face_limit and str(face_limit).strip() else None
            sd = int(seed) if seed and str(seed).strip() else None
            
            client.multiview_to_3d(
                images, output_path, output_format, callback,
                model_version=model_version if model_version != "default" else None,
                texture=texture,
                pbr=pbr,
                face_limit=fl,
                seed=sd,
                quad=quad,
                auto_size=auto_size
            )
            
            if progress:
                progress(1.0, desc="Done!")
            
            return output_path, f"✅ Success! Generated {Path(output_path).name}", log.get_log()
        
        except Exception as e:
            return None, f"❌ Error: {str(e)}", log.get_log()


def check_balance(api_key):
    """Check API credit balance."""
    if not api_key:
        return "❌ Enter API key first"
    
    try:
        client = TripoClient(api_key)
        balance = client.get_balance()
        return f"💰 Balance: {balance}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def build_interface():
    """Build the Gradio interface."""
    check_gradio()
    
    with gr.Blocks(title="Tripo 3D Generator", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🎮 Tripo 3D Generator
        Generate 3D models from images or text using [Tripo AI](https://tripo3d.ai).
        """)
        
        # API Key (shared across tabs)
        with gr.Row():
            api_key = gr.Textbox(
                label="API Key",
                placeholder="tsk_...",
                type="password",
                scale=4,
            )
            balance_btn = gr.Button("Check Balance", scale=1)
            balance_out = gr.Textbox(label="Balance", interactive=False, scale=2)
        
        balance_btn.click(check_balance, inputs=[api_key], outputs=[balance_out])
        
        # Shared settings
        with gr.Accordion("Generation Settings", open=False):
            with gr.Row():
                model_version = gr.Dropdown(
                    choices=["default"] + MODEL_VERSIONS,
                    value="default",
                    label="Model Version",
                )
                texture = gr.Dropdown(
                    choices=TEXTURE_OPTIONS,
                    value="standard",
                    label="Texture Quality",
                )
                output_format = gr.Radio(
                    choices=["glb", "fbx", "obj", "stl", "usdz"],
                    value="glb",
                    label="Output Format",
                )
            
            with gr.Row():
                pbr = gr.Checkbox(value=True, label="PBR Materials")
                quad = gr.Checkbox(value=False, label="Quad Mesh (extra cost)")
                auto_size = gr.Checkbox(value=False, label="Auto Scale (real-world size)")
            
            with gr.Row():
                face_limit = gr.Textbox(
                    label="Face Limit (optional)",
                    placeholder="e.g., 10000",
                    value="",
                )
                seed = gr.Textbox(
                    label="Seed (optional)",
                    placeholder="e.g., 12345",
                    value="",
                )
        
        with gr.Tabs():
            # Tab 1: Image to 3D
            with gr.TabItem("📷 Image → 3D"):
                gr.Markdown("Upload a single image to generate a 3D model.")
                
                with gr.Row():
                    with gr.Column():
                        image_input = gr.Image(
                            label="Input Image",
                            type="filepath",
                            height=300,
                        )
                        image_btn = gr.Button("Generate 3D", variant="primary")
                    
                    with gr.Column():
                        image_output = gr.File(label="Download Model")
                        image_status = gr.Textbox(label="Status", interactive=False)
                
                image_log = gr.Textbox(label="Debug Log", interactive=False, lines=8, max_lines=20)
                
                image_btn.click(
                    generate_from_image,
                    inputs=[image_input, output_format, api_key,
                            model_version, texture, pbr, face_limit, seed, quad, auto_size],
                    outputs=[image_output, image_status, image_log],
                )
            
            # Tab 2: Text to 3D
            with gr.TabItem("✏️ Text → 3D"):
                gr.Markdown("Describe what you want to generate.")
                
                with gr.Row():
                    with gr.Column():
                        prompt_input = gr.Textbox(
                            label="Prompt",
                            placeholder="a wooden barrel with metal bands",
                            lines=3,
                        )
                        text_btn = gr.Button("Generate 3D", variant="primary")
                    
                    with gr.Column():
                        text_output = gr.File(label="Download Model")
                        text_status = gr.Textbox(label="Status", interactive=False)
                
                text_log = gr.Textbox(label="Debug Log", interactive=False, lines=8, max_lines=20)
                
                text_btn.click(
                    generate_from_text,
                    inputs=[prompt_input, output_format, api_key,
                            model_version, texture, pbr, face_limit, seed, quad, auto_size],
                    outputs=[text_output, text_status, text_log],
                )
            
            # Tab 3: Multiview to 3D
            with gr.TabItem("🔄 Multiview → 3D"):
                gr.Markdown("Upload 4 views (front, back, left, right) for better geometry.")
                
                with gr.Row():
                    front_img = gr.Image(label="Front", type="filepath", height=150)
                    back_img = gr.Image(label="Back", type="filepath", height=150)
                    left_img = gr.Image(label="Left", type="filepath", height=150)
                    right_img = gr.Image(label="Right", type="filepath", height=150)
                
                with gr.Row():
                    with gr.Column():
                        multi_btn = gr.Button("Generate 3D", variant="primary")
                    with gr.Column():
                        multi_output = gr.File(label="Download Model")
                        multi_status = gr.Textbox(label="Status", interactive=False)
                
                multi_log = gr.Textbox(label="Debug Log", interactive=False, lines=8, max_lines=20)
                
                multi_btn.click(
                    generate_from_multiview,
                    inputs=[front_img, back_img, left_img, right_img, output_format, api_key,
                            model_version, texture, pbr, face_limit, seed, quad, auto_size],
                    outputs=[multi_output, multi_status, multi_log],
                )
        
        gr.Markdown("""
        ---
        **Settings Guide:**
        - **Model Version**: Newer = better quality, Turbo = faster
        - **Texture**: HD costs more but higher quality
        - **PBR**: Physically-based rendering materials (recommended)
        - **Quad Mesh**: Cleaner topology for animation (extra cost)
        - **Face Limit**: Control polygon count for optimization
        - **Seed**: Use same seed for reproducible results
        """)
    
    return demo


def main():
    parser = argparse.ArgumentParser(description="Tripo Web Interface")
    parser.add_argument("--port", type=int, default=7860, help="Port to run on")
    parser.add_argument("--share", action="store_true", help="Create public share link")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()
    
    check_gradio()
    demo = build_interface()
    
    print(f"\n🚀 Starting Tripo Web Interface")
    print(f"   Local URL: http://{args.host}:{args.port}")
    if args.share:
        print("   Creating public share link...")
    print()
    
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
    )


if __name__ == "__main__":
    main()
