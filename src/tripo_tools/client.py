"""
Tripo AI API Client.

The core client for interacting with Tripo's 3D generation API.
"""

import os
import time
import requests

API_BASE = "https://api.tripo3d.ai/v2/openapi"

# Task types
TASK_IMAGE_TO_MODEL = "image_to_model"
TASK_TEXT_TO_MODEL = "text_to_model"
TASK_MULTIVIEW_TO_MODEL = "multiview_to_model"
TASK_REFINE_MODEL = "refine_model"

# Model versions
MODEL_VERSIONS = [
    "v2.5-20250123",
    "v2.0-20240919",
    "v1.4-20240625",
    "Turbo-v1.0-20250506",
]

# Texture options
TEXTURE_OPTIONS = ["no", "standard", "HD"]


class TripoClient:
    """Client for Tripo's 3D generation API."""

    def __init__(self, api_key=None):
        """
        Initialize the Tripo client.
        
        Args:
            api_key: Tripo API key. If not provided, reads from TRIPO_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("TRIPO_API_KEY")
        if not self.api_key:
            raise ValueError("API key required. Pass api_key or set TRIPO_API_KEY env var.")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
        })

    def upload_image(self, image_path):
        """Upload an image file and get an image token."""
        with open(image_path, "rb") as f:
            resp = self.session.post(
                f"{API_BASE}/upload",
                files={"file": (os.path.basename(image_path), f)},
            )

        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Upload failed: {data.get('message', data)}")

        return data["data"]["image_token"]

    def create_task(self, task_type, params):
        """Create a generation task."""
        body = {"type": task_type, **params}

        resp = self.session.post(
            f"{API_BASE}/task",
            json=body,
        )

        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Task creation failed: {data.get('message', data)}")

        return data["data"]["task_id"]

    def poll_task(self, task_id, poll_interval=3, timeout=600, callback=None):
        """
        Poll a task until completion or failure.
        
        Args:
            task_id: The task ID to poll
            poll_interval: Seconds between polls
            timeout: Max seconds to wait
            callback: Optional function(progress, status) called on each poll
        
        Returns:
            Task data dict on success
        """
        start = time.time()

        while True:
            elapsed = time.time() - start
            if elapsed > timeout:
                raise TimeoutError(f"Task {task_id} timed out after {timeout}s")

            resp = self.session.get(f"{API_BASE}/task/{task_id}")
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                raise RuntimeError(f"Poll failed: {data.get('message', data)}")

            task_data = data["data"]
            status = task_data.get("status")
            progress = task_data.get("progress", 0)

            if callback:
                callback(progress, status)

            if status == "success":
                return task_data

            if status in ("failed", "cancelled", "unknown"):
                raise RuntimeError(
                    f"Task {status}: {task_data.get('message', 'no details')}"
                )

            time.sleep(poll_interval)

    def download_model(self, task_data, output_path, fmt="glb"):
        """Download the generated model from completed task data."""
        output = task_data.get("output", {})

        # Try to get model URL
        model_url = output.get("model")
        if not model_url:
            for key in ["pbr_model", "base_model", "model"]:
                if key in output and output[key]:
                    model_url = output[key]
                    break

        if not model_url:
            raise RuntimeError("No model URL found in task output")

        resp = self.session.get(model_url, stream=True)
        resp.raise_for_status()

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path

    def get_balance(self):
        """Check remaining API credits."""
        resp = self.session.get(f"{API_BASE}/user/balance")
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Balance check failed: {data.get('message', data)}")
        return data["data"]

    # High-level convenience methods

    def image_to_3d(self, image_path, output_path, fmt="glb", callback=None,
                    model_version=None, texture="standard", pbr=True,
                    face_limit=None, seed=None, quad=False, auto_size=False):
        """
        Full pipeline: image → 3D model.
        
        Args:
            image_path: Path to input image
            output_path: Path for output model
            fmt: Output format (glb, fbx, obj, stl, usdz)
            callback: Optional progress callback(progress, status)
            model_version: Model version (e.g., 'v2.5-20250123')
            texture: Texture quality ('no', 'standard', 'HD')
            pbr: Generate PBR materials (True/False)
            face_limit: Max number of faces (None for auto)
            seed: Geometry generation seed (None for random)
            quad: Generate quad mesh (extra cost)
            auto_size: Scale to real-world dimensions
        
        Returns:
            Path to downloaded model
        """
        image_token = self.upload_image(image_path)
        
        params = {
            "file": {"type": "image_token", "file_token": image_token},
        }
        
        # Add optional parameters
        if model_version:
            params["model_version"] = model_version
        if texture:
            params["texture"] = texture
        params["pbr"] = pbr
        if face_limit is not None:
            params["face_limit"] = face_limit
        if seed is not None:
            params["seed"] = seed
        if quad:
            params["quad"] = True
        if auto_size:
            params["auto_size"] = True
        
        task_id = self.create_task(TASK_IMAGE_TO_MODEL, params)
        task_data = self.poll_task(task_id, callback=callback)
        return self.download_model(task_data, output_path, fmt)

    def text_to_3d(self, prompt, output_path, fmt="glb", callback=None,
                   model_version=None, texture="standard", pbr=True,
                   face_limit=None, seed=None, quad=False, auto_size=False):
        """
        Full pipeline: text prompt → 3D model.
        
        Args:
            prompt: Text description
            output_path: Path for output model
            fmt: Output format
            callback: Optional progress callback(progress, status)
            model_version: Model version (e.g., 'v2.5-20250123')
            texture: Texture quality ('no', 'standard', 'HD')
            pbr: Generate PBR materials (True/False)
            face_limit: Max number of faces (None for auto)
            seed: Geometry generation seed (None for random)
            quad: Generate quad mesh (extra cost)
            auto_size: Scale to real-world dimensions
        
        Returns:
            Path to downloaded model
        """
        params = {"prompt": prompt}
        
        # Add optional parameters
        if model_version:
            params["model_version"] = model_version
        if texture:
            params["texture"] = texture
        params["pbr"] = pbr
        if face_limit is not None:
            params["face_limit"] = face_limit
        if seed is not None:
            params["seed"] = seed
        if quad:
            params["quad"] = True
        if auto_size:
            params["auto_size"] = True
        
        task_id = self.create_task(TASK_TEXT_TO_MODEL, params)
        task_data = self.poll_task(task_id, callback=callback)
        return self.download_model(task_data, output_path, fmt)

    def multiview_to_3d(self, image_paths, output_path, fmt="glb", callback=None,
                        model_version=None, texture="standard", pbr=True,
                        face_limit=None, seed=None, quad=False, auto_size=False):
        """
        Full pipeline: multiple views → 3D model.
        
        Args:
            image_paths: List of image paths (front, back, left, right)
            output_path: Path for output model
            fmt: Output format
            callback: Optional progress callback(progress, status)
            model_version: Model version (e.g., 'v2.5-20250123')
            texture: Texture quality ('no', 'standard', 'HD')
            pbr: Generate PBR materials (True/False)
            face_limit: Max number of faces (None for auto)
            seed: Geometry generation seed (None for random)
            quad: Generate quad mesh (extra cost)
            auto_size: Scale to real-world dimensions
        
        Returns:
            Path to downloaded model
        """
        tokens = [self.upload_image(p) for p in image_paths]
        
        params = {
            "files": [{"type": "image_token", "file_token": t} for t in tokens],
        }
        
        # Add optional parameters
        if model_version:
            params["model_version"] = model_version
        if texture:
            params["texture"] = texture
        params["pbr"] = pbr
        if face_limit is not None:
            params["face_limit"] = face_limit
        if seed is not None:
            params["seed"] = seed
        if quad:
            params["quad"] = True
        if auto_size:
            params["auto_size"] = True
        
        task_id = self.create_task(TASK_MULTIVIEW_TO_MODEL, params)
        task_data = self.poll_task(task_id, callback=callback)
        return self.download_model(task_data, output_path, fmt)
