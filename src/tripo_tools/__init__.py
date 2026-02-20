"""
Tripo Tools — Image-to-3D and Text-to-3D generation via Tripo AI.

Usage:
    from tripo_tools import TripoClient
    
    client = TripoClient("tsk_your_key")
    client.image_to_3d("photo.png", "model.glb")
    
    # With options
    client.image_to_3d(
        "photo.png", "model.glb",
        model_version="v2.5-20250123",
        texture="HD",
        pbr=True,
        face_limit=10000
    )
"""

from .client import TripoClient, MODEL_VERSIONS, TEXTURE_OPTIONS

__version__ = "0.2.0"
__all__ = ["TripoClient", "MODEL_VERSIONS", "TEXTURE_OPTIONS"]
