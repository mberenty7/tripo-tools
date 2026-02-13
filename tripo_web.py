"""
Tripo AI — Web Interface (Gradio)

A web-based alternative to tripo_gui.py.

Usage:
    python tripo_web.py

    # With custom port
    python tripo_web.py --port 7860

    # Public share link (temporary)
    python tripo_web.py --share

Requirements:
    pip install gradio requests
"""

import os
import sys
import argparse
import tempfile
from pathlib import Path

try:
    import gradio as gr
except ImportError:
    print("Gradio not installed. Run: pip install gradio")
    sys.exit(1)

# Import the client from tripo_generate
from tripo_generate import TripoClient, TASK_TEXT_TO_MODEL, TASK_IMAGE_TO_MODEL


def generate_from_image(image_path, output_format, api_key, progress=gr.Progress()):
    """Generate 3D model from a single image."""
    if not api_key:
        return None, "❌ Error: API key required"
    
    if not image_path:
        return None, "❌ Error: Please upload an image"
    
    try:
        client = TripoClient(api_key)
        
        # Upload image
        progress(0.1, desc="Uploading image...")
        image_token = client.upload_image(image_path)
        
        # Create task
        progress(0.2, desc="Creating task...")
        params = {
            "file": {"type": "image_token", "file_token": image_token},
        }
        task_id = client.create_task(TASK_IMAGE_TO_MODEL, params)
        
        # Poll for completion
        progress(0.3, desc="Generating 3D model...")
        task_data = poll_with_progress(client, task_id, progress, start=0.3, end=0.9)
        
        # Download
        progress(0.9, desc="Downloading model...")
        output_path = tempfile.mktemp(suffix=f".{output_format}")
        client.download_model(task_data, output_path, output_format)
        
        progress(1.0, desc="Done!")
        return output_path, f"✅ Success! Generated {Path(output_path).name}"
    
    except Exception as e:
        return None, f"❌ Error: {str(e)}"


def generate_from_text(prompt, output_format, api_key, progress=gr.Progress()):
    """Generate 3D model from text prompt."""
    if not api_key:
        return None, "❌ Error: API key required"
    
    if not prompt or not prompt.strip():
        return None, "❌ Error: Please enter a prompt"
    
    try:
        client = TripoClient(api_key)
        
        # Create task
        progress(0.1, desc="Creating task...")
        params = {"prompt": prompt.strip()}
        task_id = client.create_task(TASK_TEXT_TO_MODEL, params)
        
        # Poll for completion
        progress(0.2, desc="Generating 3D model...")
        task_data = poll_with_progress(client, task_id, progress, start=0.2, end=0.9)
        
        # Download
        progress(0.9, desc="Downloading model...")
        output_path = tempfile.mktemp(suffix=f".{output_format}")
        client.download_model(task_data, output_path, output_format)
        
        progress(1.0, desc="Done!")
        return output_path, f"✅ Success! Generated {Path(output_path).name}"
    
    except Exception as e:
        return None, f"❌ Error: {str(e)}"


def generate_from_multiview(front, back, left, right, output_format, api_key, progress=gr.Progress()):
    """Generate 3D model from 4 views."""
    if not api_key:
        return None, "❌ Error: API key required"
    
    images = [front, back, left, right]
    if not all(images):
        return None, "❌ Error: All 4 views required (front, back, left, right)"
    
    try:
        client = TripoClient(api_key)
        
        # Upload all images
        progress(0.1, desc="Uploading images...")
        tokens = []
        for i, img_path in enumerate(images):
            progress(0.1 + (i * 0.1), desc=f"Uploading image {i+1}/4...")
            token = client.upload_image(img_path)
            tokens.append(token)
        
        # Create multiview task
        progress(0.5, desc="Creating multiview task...")
        params = {
            "files": [
                {"type": "image_token", "file_token": t} for t in tokens
            ],
        }
        task_id = client.create_task("multiview_to_model", params)
        
        # Poll for completion
        progress(0.6, desc="Generating 3D model...")
        task_data = poll_with_progress(client, task_id, progress, start=0.6, end=0.9)
        
        # Download
        progress(0.9, desc="Downloading model...")
        output_path = tempfile.mktemp(suffix=f".{output_format}")
        client.download_model(task_data, output_path, output_format)
        
        progress(1.0, desc="Done!")
        return output_path, f"✅ Success! Generated {Path(output_path).name}"
    
    except Exception as e:
        return None, f"❌ Error: {str(e)}"


def poll_with_progress(client, task_id, progress, start=0.2, end=0.9, poll_interval=3, timeout=600):
    """Poll task with Gradio progress updates."""
    import time
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise TimeoutError(f"Task timed out after {timeout}s")
        
        resp = client.session.get(f"https://api.tripo3d.ai/v2/openapi/task/{task_id}")
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") != 0:
            raise RuntimeError(f"Poll failed: {data.get('message', data)}")
        
        task_data = data["data"]
        status = task_data.get("status")
        task_progress = task_data.get("progress", 0)
        
        # Map task progress (0-100) to our progress range (start-end)
        mapped_progress = start + (end - start) * (task_progress / 100)
        progress(mapped_progress, desc=f"Generating... {task_progress}%")
        
        if status == "success":
            return task_data
        
        if status in ("failed", "cancelled", "unknown"):
            raise RuntimeError(f"Task {status}: {task_data.get('message', 'no details')}")
        
        time.sleep(poll_interval)


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
        
        # Output format (shared)
        output_format = gr.Radio(
            choices=["glb", "fbx", "obj", "stl", "usdz"],
            value="glb",
            label="Output Format",
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
                
                image_btn.click(
                    generate_from_image,
                    inputs=[image_input, output_format, api_key],
                    outputs=[image_output, image_status],
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
                
                text_btn.click(
                    generate_from_text,
                    inputs=[prompt_input, output_format, api_key],
                    outputs=[text_output, text_status],
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
                
                multi_btn.click(
                    generate_from_multiview,
                    inputs=[front_img, back_img, left_img, right_img, output_format, api_key],
                    outputs=[multi_output, multi_status],
                )
        
        gr.Markdown("""
        ---
        **Tips:**
        - GLB format is best for web/game engines
        - Single image works well for simple objects
        - Multiview gives better geometry for complex shapes
        - Get your API key at [tripo3d.ai](https://tripo3d.ai)
        """)
    
    return demo


def main():
    parser = argparse.ArgumentParser(description="Tripo Web Interface")
    parser.add_argument("--port", type=int, default=7860, help="Port to run on")
    parser.add_argument("--share", action="store_true", help="Create public share link")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()
    
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
