"""
Standalone test for Module 9 — run this BEFORE touching inputs.py, so you
can visually confirm face cropping is accurate without debugging through
the full API/frontend chain.

Usage:
    python test_media_processing.py path/to/image.jpg image
    python test_media_processing.py path/to/video.mp4 video

Saves any detected face crops into a 'test_output/' folder so you can
open them and check they actually look like cropped faces.
"""

import sys
import os
from media_processing import process_media

if len(sys.argv) != 3:
    print("Usage: python test_media_processing.py <file_path> <image|video>")
    sys.exit(1)

file_path = sys.argv[1]
media_type = sys.argv[2]

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    sys.exit(1)

if media_type not in ("image", "video"):
    print("media_type must be 'image' or 'video'")
    sys.exit(1)

print(f"Processing {file_path} as {media_type}...")
result = process_media(file_path, media_type)

print(f"\nFrames analyzed: {result['frames_analyzed']}")
print(f"Frames with at least one face: {result['frames_with_faces']}")
print(f"Total faces found: {result['faces_found']}")

if result["faces_found"] == 0:
    print("\nNo faces detected. If your test file clearly contains a face, "
          "check image quality/lighting/angle, or that the file loaded correctly.")
else:
    os.makedirs("test_output", exist_ok=True)
    for i, face in enumerate(result["face_crops"]):
        out_path = os.path.join("test_output", f"face_{i}.jpg")
        face.save(out_path)
        print(f"Saved {out_path} ({face.size[0]}x{face.size[1]})")

    print(f"\nOpen the 'test_output' folder and check that these actually "
          f"look like cropped faces, not misaligned or empty crops.")