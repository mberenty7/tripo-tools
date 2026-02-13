"""
Tripo Tools CLI.

Usage:
    tripo --image photo.png --output model.glb
    tripo --prompt "a wooden barrel" --output barrel.glb
    tripo --multiview front.png back.png left.png right.png --output model.glb
    tripo --balance
"""

import argparse
import os
import sys
from pathlib import Path

from .client import TripoClient


def print_progress(progress, status):
    """Print progress bar to terminal."""
    bar_len = 30
    filled = int(bar_len * progress / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"\r[tripo] [{bar}] {progress}% — {status}", end="", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Tripo AI — Image-to-3D and Text-to-3D generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    tripo --image photo.png --output model.glb
    tripo --prompt "a wooden barrel" --output barrel.glb
    tripo --multiview f.png b.png l.png r.png --output model.glb
    tripo --balance
        """
    )

    # Input modes (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--image", "-i", help="Input image file path")
    input_group.add_argument("--prompt", "-p", help="Text prompt for 3D generation")
    input_group.add_argument("--multiview", "-m", nargs="+", 
                             help="Multiple view images (front back left right)")
    input_group.add_argument("--balance", "-b", action="store_true",
                             help="Check credit balance and exit")

    # Output
    parser.add_argument("--output", "-o", help="Output file path (e.g., model.glb)")
    parser.add_argument("--format", "-f", default="glb",
                        choices=["glb", "fbx", "obj", "stl", "usdz"],
                        help="Output format (default: glb)")

    # Options
    parser.add_argument("--api-key", "-k",
                        help="Tripo API key (or set TRIPO_API_KEY env var)")
    parser.add_argument("--timeout", "-t", type=int, default=600,
                        help="Max wait time in seconds (default: 600)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress progress output")
    parser.add_argument("--version", "-v", action="store_true",
                        help="Show version and exit")

    args = parser.parse_args()

    # Version
    if args.version:
        from . import __version__
        print(f"tripo-tools {__version__}")
        return 0

    # Get API key
    api_key = args.api_key or os.environ.get("TRIPO_API_KEY")
    if not api_key:
        print("[tripo] ERROR: No API key. Set TRIPO_API_KEY or use --api-key")
        return 1

    try:
        client = TripoClient(api_key)
    except ValueError as e:
        print(f"[tripo] ERROR: {e}")
        return 1

    # Balance check
    if args.balance:
        try:
            balance = client.get_balance()
            print(f"[tripo] Credits: {balance}")
            return 0
        except Exception as e:
            print(f"[tripo] ERROR: {e}")
            return 1

    # Validate input
    if not any([args.image, args.prompt, args.multiview]):
        parser.print_help()
        print("\n[tripo] ERROR: Specify --image, --prompt, or --multiview")
        return 1

    if not args.output:
        print("[tripo] ERROR: --output required")
        return 1

    # Validate input files exist
    if args.image and not os.path.isfile(args.image):
        print(f"[tripo] ERROR: Image not found: {args.image}")
        return 1

    if args.multiview:
        for img in args.multiview:
            if not os.path.isfile(img):
                print(f"[tripo] ERROR: Image not found: {img}")
                return 1

    # Ensure output has correct extension
    output_path = args.output
    expected_ext = f".{args.format}"
    if not output_path.lower().endswith(expected_ext):
        output_path = str(Path(output_path).with_suffix(expected_ext))

    # Progress callback
    callback = None if args.quiet else print_progress

    # Determine mode and run
    if args.image:
        mode = "Image → 3D"
    elif args.prompt:
        mode = "Text → 3D"
    else:
        mode = "Multiview → 3D"

    print(f"[tripo] Mode: {mode}")
    print(f"[tripo] Output: {output_path}")
    print()

    try:
        if args.image:
            client.image_to_3d(args.image, output_path, args.format, callback)
        elif args.prompt:
            client.text_to_3d(args.prompt, output_path, args.format, callback)
        else:
            client.multiview_to_3d(args.multiview, output_path, args.format, callback)

        print(f"\n[tripo] ✓ Done! Saved to {output_path}")
        return 0

    except KeyboardInterrupt:
        print("\n[tripo] Cancelled.")
        return 1
    except Exception as e:
        print(f"\n[tripo] ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
