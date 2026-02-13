"""
Tripo Tools — Image-to-3D and Text-to-3D generation via Tripo AI.

Usage:
    from tripo_tools import TripoClient
    
    client = TripoClient("tsk_your_key")
    client.image_to_3d("photo.png", "model.glb")
"""

from .client import TripoClient

__version__ = "0.1.0"
__all__ = ["TripoClient"]
