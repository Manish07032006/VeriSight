"""
VeriSight DDA Inference Service
================================

Runs the Dual-Data-Alignment (DDA) AI-generated image detector
as a persistent, local-only HTTP service.

Environment:
    D:\\PROJECT\\venv\\Scripts\\python.exe

Checkpoint:
    D:\\PROJECT\\Dual-Data-Alignment\\pretrained\\DDA_ckpt.pth

Service:
    http://127.0.0.1:8765

Endpoints:
    GET  /health
    POST /predict

Security:
    - Binds only to 127.0.0.1.
    - Accepts image inference requests only.
    - Limits image upload size.
    - Does not save uploaded images.
    - Does not expose the service to other network devices.
"""

import io
import os
import sys
import threading
import traceback

import torch
from flask import Flask, jsonify, request
from PIL import Image, UnidentifiedImageError
from torchvision import transforms


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(BASE_DIR)

CHECKPOINT_PATH = os.path.join(
    REPO_DIR,
    "pretrained",
    "DDA_ckpt.pth",
)

HOST = "127.0.0.1"
PORT = 8765

MAX_IMAGE_BYTES = 20 * 1024 * 1024

MODEL_NAME = "dinov2_vitl14"
LORA_RANK = 8
LORA_ALPHA = 1

DEVICE = torch.device(
    "cuda:0" if torch.cuda.is_available() else "cpu"
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_BYTES

_model = None
_model_lock = threading.Lock()


# ============================================================
# IMAGE PREPROCESSING
# Must match the official DDA inference transform.
# ============================================================

image_transform = transforms.Compose([
    transforms.CenterCrop(336),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.48145466, 0.4578275, 0.40821073],
        std=[0.26862954, 0.26130258, 0.27577711],
    ),
])


# ============================================================
# MODEL LOADING
# ============================================================

def load_model():
    """
    Load the DDA model and checkpoint exactly once.

    Subsequent calls reuse the already-loaded model.
    """
    global _model

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        if not os.path.isfile(CHECKPOINT_PATH):
            raise FileNotFoundError(
                f"DDA checkpoint not found: {CHECKPOINT_PATH}"
            )

        # Add the DDA Inference directory to the import path.
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)

        from models.dinov2_models_lora import (
            DINOv2ModelWithLoRA,
        )

        print("[DDA] Initializing DINOv2 ViT-L/14 with LoRA...")

        model = DINOv2ModelWithLoRA(
            name=MODEL_NAME,
            lora_rank=LORA_RANK,
            lora_alpha=LORA_ALPHA,
            lora_targets=None,
        )

        print(f"[DDA] Loading checkpoint: {CHECKPOINT_PATH}")

        # Load checkpoint tensors on CPU first
        checkpoint = torch.load(
            CHECKPOINT_PATH,
            map_location="cpu",
            weights_only=True,
        )

        if not isinstance(checkpoint, dict):
            raise RuntimeError(
                "Unexpected DDA checkpoint format."
            )

        state_dict = checkpoint.get("model")

        if not isinstance(state_dict, dict):
            raise RuntimeError(
                "The DDA checkpoint has no valid 'model' state dictionary."
            )

        model.load_state_dict(
            state_dict,
            strict=True,
        )

        del state_dict
        del checkpoint

        model.to(DEVICE)
        model.eval()

        _model = model

        print(f"[DDA] Model loaded successfully on {DEVICE}.")

        if torch.cuda.is_available():
            print(
                "[DDA] GPU:",
                torch.cuda.get_device_name(0),
            )

        return _model


# ============================================================
# ERROR HANDLING
# ============================================================

@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({
        "status": "error",
        "error": "Image exceeds the 20 MB upload limit.",
    }), 413


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    """
    Return service status without triggering model loading.
    """
    return jsonify({
        "service": "VeriSight DDA",
        "status": "ok",
        "model_loaded": _model is not None,
        "device": str(DEVICE),
        "cuda_available": torch.cuda.is_available(),
    }), 200


# ============================================================
# IMAGE INFERENCE
# ============================================================

@app.route("/predict", methods=["POST"])
def predict():
    """
    Accept an image in multipart/form-data under the field 'file'.

    Returns the adjusted sigmoid score for the fake-image class.
    """

    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "error": (
                "Missing image file. "
                "Expected multipart field named 'file'."
            ),
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "status": "error",
            "error": "No image was supplied.",
        }), 400

    image_bytes = uploaded_file.read(
        MAX_IMAGE_BYTES + 1
    )

    if not image_bytes:
        return jsonify({
            "status": "error",
            "error": "The uploaded image is empty.",
        }), 400

    if len(image_bytes) > MAX_IMAGE_BYTES:
        return jsonify({
            "status": "error",
            "error": "Image exceeds the 20 MB upload limit.",
        }), 413

    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            source.load()
            image = source.convert("RGB")

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        return jsonify({
            "status": "error",
            "error": "The uploaded file is not a valid image.",
        }), 400

    del image_bytes

    try:
        model = load_model()

        tensor = image_transform(image)
        tensor = tensor.unsqueeze(0).to(DEVICE)

        with _model_lock:
            with torch.inference_mode():
                logits = model(tensor)
                base_score = torch.sigmoid(logits).flatten()[0].item()

        # Invert score mapping so high value maps to AI-Generated / Fake probability
        score = float(1.0 - base_score)

        if not 0.0 <= score <= 1.0:
            raise RuntimeError(
                "DDA returned a score outside the expected range."
            )

        return jsonify({
            "status": "available",
            "raw_score": score,
            "score_percent": round(score * 100.0, 2),
            "interpretation": (
                "Calibrated sigmoid score for the fake-image "
                "class. Higher percentages indicate higher likelihood "
                "of AI generation."
            ),
            "model": MODEL_NAME,
            "device": str(DEVICE),
        }), 200

    except Exception as exc:
        print(f"[DDA] Inference failed: {exc}")
        traceback.print_exc()

        return jsonify({
            "status": "error",
            "error": "DDA inference failed.",
        }), 503


# ============================================================
# START SERVICE
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("VeriSight DDA Inference Service")
    print("=" * 60)

    print(f"[DDA] Repository: {REPO_DIR}")
    print(f"[DDA] Checkpoint: {CHECKPOINT_PATH}")
    print(f"[DDA] Device: {DEVICE}")

    if torch.cuda.is_available():
        print(
            f"[DDA] GPU: {torch.cuda.get_device_name(0)}"
        )
    else:
        print(
            "[DDA] WARNING: CUDA is unavailable. "
            "Inference will use the CPU."
        )

    print(f"[DDA] Service URL: http://{HOST}:{PORT}")

    try:
        load_model()

    except Exception:
        print("[DDA] Model initialization failed.")
        traceback.print_exc()
        raise SystemExit(1)

    print("[DDA] Service is ready.")

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        threaded=True,
        use_reloader=False,
    )
    