"""
Model loader for VeriSight (GPU Optimized).

Text classifiers:
    - Fake-news detection: pretrained Hugging Face RoBERTa
    - AI-text detection: pretrained Hugging Face RoBERTa

Media classifiers:
    - Deepfake detection: existing project CNN checkpoint
    - AI-generated image detection: pretrained Hugging Face ViT model (capcheck/ai-image-detection)
"""

import os
import torch
from PIL import Image
from transformers import pipeline

from deepfake_model import ScratchCNNClassifier
from deepfake_dataset import build_transforms


# ============================================================
# CONFIGURATION
# ============================================================

CHECKPOINT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "checkpoints",
)

FAKE_NEWS_MODEL_ID = "akanbrown/AI-Fake_News_Detection_Roberta"
AI_TEXT_MODEL_ID = "Hello-SimpleAI/chatgpt-detector-roberta"
AI_IMAGE_MODEL_ID = "capcheck/ai-image-detection"

# Automatically detect RTX 3050 GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_fake_news_classifier = None
_ai_text_classifier = None
_deepfake_model = None
_ai_image_classifier = None

_deepfake_transform = build_transforms(train=False)


# ============================================================
# MODEL INITIALIZATION
# ============================================================

def load_all_models():
    """Load text classifiers, deepfake CNN, and Hugging Face AI-image classifier."""
    global _fake_news_classifier
    global _ai_text_classifier
    global _deepfake_model
    global _ai_image_classifier

    print(f"[model_loader] Active inference device: {device}")

    # Load Fake-News Classifier
    try:
        print("[model_loader] Loading fake-news classifier...")
        _fake_news_classifier = pipeline(
            "text-classification",
            model=FAKE_NEWS_MODEL_ID,
            tokenizer="jy46604790/Fake-News-Bert-Detect",
            device=-1,
        )
    except Exception as exc:
        _fake_news_classifier = None
        raise RuntimeError(f"Could not load fake-news model: {exc}") from exc

    # Load AI-Text Classifier
    try:
        print("[model_loader] Loading AI-text classifier...")
        _ai_text_classifier = pipeline(
            "text-classification",
            model=AI_TEXT_MODEL_ID,
            device=-1,
        )
    except Exception as exc:
        _ai_text_classifier = None
        raise RuntimeError(f"Could not load AI-text model: {exc}") from exc

    # Load Pretrained AI-Image Classifier on GPU
    try:
        print(f"[model_loader] Loading Hugging Face AI-image model '{AI_IMAGE_MODEL_ID}'...")
        _ai_image_classifier = pipeline(
            "image-classification",
            model=AI_IMAGE_MODEL_ID,
            device=0 if torch.cuda.is_available() else -1,
        )
    except Exception as exc:
        _ai_image_classifier = None
        raise RuntimeError(f"Could not load AI-image model '{AI_IMAGE_MODEL_ID}': {exc}") from exc

    # Load Legacy Deepfake Checkpoint
    _deepfake_model = _load_deepfake_model()

    print("[model_loader] Model initialization completed successfully.")


# ============================================================
# TEXT CLASSIFICATION HELPERS
# ============================================================

def _run_text_classifier(classifier, text, model_name):
    if classifier is None:
        raise RuntimeError(f"{model_name} is not loaded.")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Input text must be a non-empty string.")

    result = classifier(text, truncation=True, max_length=512)
    prediction = result[0]
    confidence = float(prediction["score"])
    
    return str(prediction["label"]).strip().lower(), round(confidence * 100, 2)


def predict_fake_news(text: str):
    label, confidence = _run_text_classifier(_fake_news_classifier, text, "Fake-news classifier")
    verdict = "real" if label in ("real", "true", "label_0") else "fake"
    return verdict, confidence


def predict_ai_text(text: str):
    label, confidence = _run_text_classifier(_ai_text_classifier, text, "AI-text classifier")
    verdict = "human" if label in ("human", "label_0") else "ai_generated"
    return verdict, confidence


# ============================================================
# DEEPFAKE DETECTION (LEGACY CNN)
# ============================================================

def _load_deepfake_model():
    checkpoint_path = os.path.join(CHECKPOINT_DIR, "deepfake_best.pt")
    if not os.path.isfile(checkpoint_path):
        print(f"[model_loader] WARNING: Checkpoint not found: {checkpoint_path}")
        return None

    try:
        checkpoint = torch.load(checkpoint_path, map_location=device)
        model = ScratchCNNClassifier(num_classes=2)
        model.load_state_dict(checkpoint["model_state"], strict=True)
        model.to(device)
        model.eval()
        return model
    except Exception as exc:
        raise RuntimeError(f"Could not load deepfake checkpoint: {exc}") from exc


def predict_deepfake_single(face_image: Image.Image):
    if _deepfake_model is None:
        raise RuntimeError("Deepfake model is not loaded.")

    tensor = _deepfake_transform(face_image.convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = _deepfake_model(tensor)
        probs = torch.softmax(logits, dim=1)[0].detach().cpu().tolist()

    predicted_class = int(probs[1] > probs[0])
    confidence = round(probs[predicted_class] * 100, 2)
    verdict = "real" if predicted_class == 1 else "manipulated"

    return verdict, confidence


def predict_deepfake(face_crops: list):
    if not face_crops:
        return "no_face_detected", 0.0, []

    per_face_results = [predict_deepfake_single(face) for face in face_crops]
    manipulated_count = sum(1 for verdict, _ in per_face_results if verdict == "manipulated")
    real_count = sum(1 for verdict, _ in per_face_results if verdict == "real")

    final_verdict = "manipulated" if manipulated_count >= real_count else "real"
    agreeing = [conf for v, conf in per_face_results if v == final_verdict]
    final_confidence = round(sum(agreeing) / len(agreeing), 2) if agreeing else 0.0

    return final_verdict, final_confidence, per_face_results


# ============================================================
# PRETRAINED HUGGING FACE AI-IMAGE DETECTION
# ============================================================

def predict_ai_image_single(frame: Image.Image):
    """Predict using capcheck/ai-image-detection pipeline on GPU."""
    if _ai_image_classifier is None:
        raise RuntimeError("AI-image classifier is not loaded.")

    try:
        results = _ai_image_classifier(frame.convert("RGB"))
        top_prediction = results[0]

        raw_label = str(top_prediction["label"]).strip().lower()
        confidence = round(float(top_prediction["score"]) * 100, 2)

        verdict = "ai_generated" if raw_label in ["fake", "ai", "label_1"] else "authentic"
        return verdict, confidence
    except Exception as exc:
        raise RuntimeError(f"AI-image inference failed: {exc}") from exc


def predict_ai_image(frames: list):
    """Run AI-image detection across extracted frames."""
    if not frames:
        return "no_frames_available", 0.0, []

    per_frame_results = [predict_ai_image_single(frame) for frame in frames]

    ai_count = sum(1 for v, _ in per_frame_results if v == "ai_generated")
    authentic_count = sum(1 for v, _ in per_frame_results if v == "authentic")

    final_verdict = "ai_generated" if ai_count >= authentic_count else "authentic"
    agreeing = [conf for v, conf in per_frame_results if v == final_verdict]
    final_confidence = round(sum(agreeing) / len(agreeing), 2) if agreeing else 0.0

    return final_verdict, final_confidence, per_frame_results