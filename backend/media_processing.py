"""
VeriSight - Frame Extraction and Face Detection

Uses OpenCV for image/video processing and facenet-pytorch MTCNN
for face detection.

Returns:
    frames_analyzed
    faces_found
    frames_with_faces
    face_crops
    frames

Important:
    Face detection is not proof of a deepfake.
    Deepfake classification is performed by model_loader.py.
"""

import logging
import math
from pathlib import Path

import cv2
import torch
from PIL import Image, ImageOps
from facenet_pytorch import MTCNN


logger = logging.getLogger(__name__)

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

# Keep all faces found in a frame.
_mtcnn = MTCNN(
    keep_all=True,
    device=DEVICE,
)

# Video processing settings
FRAME_INTERVAL = 10
MAX_FRAMES = 20

# Face detection settings
FACE_MARGIN = 0.20
DEFAULT_MIN_CONFIDENCE = 0.95
MIN_BOX_AREA_RATIO = 0.001

# Resource protection
MAX_IMAGE_DIMENSION = 4096
MAX_FACE_CROPS = 100


def _validate_media_type(media_type):
    """Validate and normalize the media type."""
    normalized = str(media_type).strip().lower()

    if normalized not in {"image", "video"}:
        raise ValueError(
            "Unsupported media type. Expected 'image' or 'video'."
        )

    return normalized


def _load_image_file(file_path):
    """Read an image safely and return a PIL RGB image."""
    path = Path(file_path)

    if not path.is_file():
        raise ValueError(f"Image file does not exist: {path}")

    try:
        with Image.open(path) as source:
            source = ImageOps.exif_transpose(source)
            source.load()
            image = source.convert("RGB")

    except (OSError, ValueError) as exc:
        raise ValueError(
            f"Could not read image file: {path}"
        ) from exc

    if image.width <= 0 or image.height <= 0:
        raise ValueError("The image has invalid dimensions.")

    if (
        image.width > MAX_IMAGE_DIMENSION
        or image.height > MAX_IMAGE_DIMENSION
    ):
        image.thumbnail(
            (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
            Image.Resampling.LANCZOS,
        )

    return image


def extract_frames(file_path: str, media_type: str):
    """
    Extract RGB PIL frames.

    Images:
        Returns one RGB frame.

    Videos:
        Samples every FRAME_INTERVAL frames, up to MAX_FRAMES.
    """
    media_type = _validate_media_type(media_type)

    if media_type == "image":
        return [_load_image_file(file_path)]

    path = Path(file_path)

    if not path.is_file():
        raise ValueError(f"Video file does not exist: {path}")

    cap = cv2.VideoCapture(str(path))

    if not cap.isOpened():
        cap.release()
        raise ValueError(f"Could not open video file: {path}")

    frames = []
    frame_index = 0

    try:
        while len(frames) < MAX_FRAMES:
            success, bgr = cap.read()

            if not success:
                break

            if frame_index % FRAME_INTERVAL == 0:
                if bgr is not None and bgr.size > 0:
                    height, width = bgr.shape[:2]

                    if (
                        width > 0
                        and height > 0
                    ):
                        rgb = cv2.cvtColor(
                            bgr,
                            cv2.COLOR_BGR2RGB,
                        )

                        frame = Image.fromarray(rgb)

                        if (
                            frame.width > MAX_IMAGE_DIMENSION
                            or frame.height > MAX_IMAGE_DIMENSION
                        ):
                            frame.thumbnail(
                                (
                                    MAX_IMAGE_DIMENSION,
                                    MAX_IMAGE_DIMENSION,
                                ),
                                Image.Resampling.LANCZOS,
                            )

                        frames.append(frame)

            frame_index += 1

    finally:
        cap.release()

    if not frames:
        raise ValueError(
            "No readable frames could be extracted from the video."
        )

    return frames


def detect_faces(
    frame: Image.Image,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
):
    """
    Detect faces in one RGB image.

    Returns a list of cropped RGB PIL images.
    An empty list means no usable faces were detected.
    """
    if not isinstance(frame, Image.Image):
        raise ValueError("frame must be a PIL Image.")

    if not math.isfinite(float(min_confidence)):
        raise ValueError("min_confidence must be a finite number.")

    if not 0.0 <= float(min_confidence) <= 1.0:
        raise ValueError("min_confidence must be between 0 and 1.")

    frame = frame.convert("RGB")
    width, height = frame.size

    if width <= 0 or height <= 0:
        return []

    try:
        boxes, probabilities = _mtcnn.detect(frame)
    except Exception as exc:
        logger.warning("Face detection failed for a frame: %s", exc)
        return []

    if boxes is None or probabilities is None:
        return []

    min_box_area = width * height * MIN_BOX_AREA_RATIO
    face_crops = []

    for box, probability in zip(boxes, probabilities):
        if box is None or probability is None:
            continue

        try:
            probability = float(probability)

            if not math.isfinite(probability):
                continue

            if probability < min_confidence:
                continue

            x1, y1, x2, y2 = map(float, box)

        except (TypeError, ValueError):
            continue

        if not all(
            math.isfinite(value)
            for value in (x1, y1, x2, y2)
        ):
            continue

        box_width = x2 - x1
        box_height = y2 - y1

        if box_width <= 0 or box_height <= 0:
            continue

        if box_width * box_height < min_box_area:
            continue

        # Add padding around the face.
        left = max(
            0,
            int(x1 - box_width * FACE_MARGIN),
        )
        top = max(
            0,
            int(y1 - box_height * FACE_MARGIN),
        )
        right = min(
            width,
            int(x2 + box_width * FACE_MARGIN),
        )
        bottom = min(
            height,
            int(y2 + box_height * FACE_MARGIN),
        )

        if right <= left or bottom <= top:
            continue

        crop = frame.crop(
            (left, top, right, bottom)
        ).convert("RGB")

        face_crops.append(crop)

    return face_crops


def process_media(file_path: str, media_type: str):
    """
    Run the frame extraction and face detection pipeline.

    The output keys are compatible with the existing inputs.py:
        frames_analyzed
        faces_found
        frames_with_faces
        face_crops
        frames
    """
    media_type = _validate_media_type(media_type)

    frames = extract_frames(
        file_path,
        media_type,
    )

    all_face_crops = []
    frames_with_faces = 0

    for frame in frames:
        faces = detect_faces(frame)

        if faces:
            frames_with_faces += 1

            remaining = MAX_FACE_CROPS - len(all_face_crops)

            if remaining > 0:
                all_face_crops.extend(
                    faces[:remaining]
                )

    return {
        "frames_analyzed": len(frames),
        "faces_found": len(all_face_crops),
        "frames_with_faces": frames_with_faces,
        "face_crops": all_face_crops,
        "frames": frames,
    }