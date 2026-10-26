"""
VeriSight — User Input Handling and Media Verification

POST /scan/text:
    Runs the fake-news and AI-text classifiers.

POST /scan/media:
    Processes uploaded images and videos using:
      1. Deepfake detection CNN
      2. AI-generated image detection CNN
      3. DDA AI-generated image detection service
      4. C2PA content-credential inspection
      5. Local perceptual-hash image matching
      6. Combined evidence assessment
      7. Manual reverse-image-search links
      8. VeriSight Trust Index (Weighted Ensemble with Real Face Shield)

The existing database schema is preserved.
DDA results and ensemble scores augment the UI while keeping
independent detector cards fully intact.
"""

import os
import uuid
import traceback
import math

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from auth import token_required
from models import db, NewsScan, MediaScan

import model_loader
import reasoning

from media_processing import process_media
from media_verification import build_media_evidence
from c2pa_verifier import inspect_c2pa
from dda_client import predict_dda_image

from local_visual_search import (
    find_local_matches,
    make_manual_search_links,
)


# ============================================================
# CONFIGURATION
# ============================================================

inputs_bp = Blueprint(
    "inputs",
    __name__,
    url_prefix="/scan",
)

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
}

ALLOWED_VIDEO_EXTENSIONS = {
    "mp4",
    "mov",
}

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "uploads",
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_extension(filename: str) -> str:
    """Return the lowercase file extension without the dot."""
    return (
        filename.rsplit(".", 1)[-1].lower()
        if "." in filename
        else ""
    )


def _unavailable_c2pa(message: str):
    """Return a consistent response if C2PA inspection fails."""
    return {
        "status": "unavailable",
        "message": message,
        "credentials_found": None,
        "signature_valid": None,
    }


def _unavailable_local_search(message: str):
    """Return a consistent response if local image matching fails."""
    return {
        "status": "unavailable",
        "message": message,
        "reference_images_scanned": 0,
        "matches": [],
    }


def _run_c2pa_inspection(file_path: str) -> dict:
    """
    Inspect content credentials without allowing an optional
    verification failure to interrupt the entire media scan.
    """
    try:
        result = inspect_c2pa(file_path)

        if isinstance(result, dict):
            return result

        return _unavailable_c2pa(
            "The C2PA verifier returned an unexpected result."
        )

    except Exception:
        traceback.print_exc()

        return _unavailable_c2pa(
            "C2PA inspection could not be completed."
        )


def _run_local_visual_search(reference_image) -> dict:
    """
    Search the configured local reference-image collection.

    This function does not upload the image to an external service.
    """
    if reference_image is None:
        return _unavailable_local_search(
            "No representative image frame was available."
        )

    try:
        result = find_local_matches(reference_image)

        if isinstance(result, dict):
            return result

        return _unavailable_local_search(
            "The local visual-search module returned an unexpected result."
        )

    except Exception:
        traceback.print_exc()

        return _unavailable_local_search(
            "Local visual matching could not be completed."
        )


def _run_dda_detection(representative_frame) -> dict:
    """
    Run the optional DDA detector.

    DDA failure must never prevent the existing media scan
    from completing.
    """
    try:
        result = predict_dda_image(representative_frame)

        if isinstance(result, dict):
            return result

        return {
            "status": "unavailable",
            "model": "dinov2_vitl14",
            "raw_score": None,
            "score_percent": None,
            "message": "DDA returned an unexpected result.",
        }

    except Exception:
        traceback.print_exc()

        return {
            "status": "unavailable",
            "model": "dinov2_vitl14",
            "raw_score": None,
            "score_percent": None,
            "message": "DDA detection could not be completed.",
        }


def calculate_verisight_trust_index(media_type, dda_result, ai_image_verdict, ai_image_confidence, deepfake_confidence, deepfake_verdict="real"):
    """
    Computes an overarching Trust Index balancing real object photo protection 
    with high-fidelity AI artwork detection using DDA cross-reference consensus.
    """
    dda_score_percent = dda_result.get("score_percent") or 0.0
    
    # Determine raw AI fake probability
    if ai_image_verdict in ["ai_generated", "fake", "synthetic"]:
        ai_fake_probability = ai_image_confidence if ai_image_confidence else 0.0
    else:
        ai_fake_probability = 100.0 - ai_image_confidence if ai_image_confidence else 0.0
    
    if media_type == "image":
        # ========================================================
        # IMAGES: EXACT ORIGINAL LOGIC (UNTOUCHED & PRESERVED)
        # ========================================================
        has_verified_real_face = (
            deepfake_verdict in ["real", "human", "authentic"] 
            and deepfake_confidence >= 60.0
        )
        
        if has_verified_real_face:
            synthetic_probability = min(15.0, 100.0 - deepfake_confidence)
        else:
            if ai_fake_probability >= 70.0 and dda_score_percent < 45.0:
                synthetic_probability = dda_score_percent * 0.8
            elif ai_fake_probability >= 70.0 and dda_score_percent >= 50.0:
                synthetic_probability = (0.40 * dda_score_percent) + (0.60 * ai_fake_probability)
            else:
                synthetic_probability = (0.50 * dda_score_percent) + (0.50 * ai_fake_probability)
    else:
        # ========================================================
        # VIDEOS ONLY: BALANCED ENSEMBLE WITH ORIGINAL THRESHOLDS
        # ========================================================
        is_deepfake_manipulated = deepfake_verdict in ["fake", "ai_generated", "manipulated"]
        deepfake_fake_prob = deepfake_confidence if is_deepfake_manipulated else (100.0 - deepfake_confidence if deepfake_confidence else 0.0)
        
        synthetic_probability = (0.50 * deepfake_fake_prob) + (0.30 * dda_score_percent) + (0.20 * ai_fake_probability)

    # Determine unified risk tier (Restored original 38.0 / 68.0 thresholds)
    if synthetic_probability >= 68.0:
        risk_level = "high_synthetic_risk"
        verdict = "Likely AI-Generated / Manipulated"
    elif synthetic_probability >= 38.0:
        risk_level = "moderate_risk"
        verdict = "Uncertain / Mixed Signals"
    else:
        risk_level = "low_risk"
        verdict = "Likely Authentic"
        
    return {
        "overall_synthetic_probability": round(synthetic_probability, 2),
        "risk_level": risk_level,
        "verdict": verdict,
        "components_factored": ["dda_model", "baseline_ai_image_model", "deepfake_detector"]
    }


def _build_evidence_safely(
    media_type,
    ai_image_verdict,
    ai_image_confidence,
    deepfake_verdict,
    deepfake_confidence,
    c2pa_result,
    local_matches,
):
    """
    Build the existing combined evidence assessment.
    """
    try:
        return build_media_evidence(
            media_type=media_type,
            ai_image_verdict=ai_image_verdict,
            ai_image_confidence=ai_image_confidence,
            deepfake_verdict=deepfake_verdict,
            deepfake_confidence=deepfake_confidence,
            c2pa_result=c2pa_result,
            local_matches=local_matches,
        )

    except Exception:
        traceback.print_exc()

        return {
            "overall_status": "inconclusive",
            "message": (
                "The individual detector results are available, "
                "but the combined evidence assessment could not "
                "be completed."
            ),
            "assessment_error": True,
        }


def _generate_manual_search_links(media_type) -> dict:
    """
    Generate manual reverse-search links without automatically
    uploading media to those services.
    """
    try:
        result = make_manual_search_links(media_type)

        if isinstance(result, dict):
            return result

        return {
            "status": "unavailable",
            "message": (
                "Manual search links could not be generated."
            ),
        }

    except Exception:
        traceback.print_exc()

        return {
            "status": "unavailable",
            "message": (
                "Manual search links could not be generated."
            ),
        }


# ============================================================
# TEXT SCANNING
# ============================================================

@inputs_bp.route("/text", methods=["POST"])
@token_required
def scan_text(current_user):

    data = request.get_json(silent=True) or {}

    input_text = (
        data.get("input_text") or ""
    ).strip()

    if not input_text:
        return jsonify({
            "error": (
                "input_text is required and cannot be empty"
            )
        }), 400

    if len(input_text) > 20000:
        return jsonify({
            "error": (
                "input_text is too long "
                "(max 20,000 characters)"
            )
        }), 400

    try:
        (
            fake_news_verdict,
            fake_news_confidence,
        ) = model_loader.predict_fake_news(input_text)

        (
            ai_text_verdict,
            ai_text_confidence,
        ) = model_loader.predict_ai_text(input_text)

    except RuntimeError as exc:
        return jsonify({
            "error": str(exc)
        }), 503

    (
        explanation,
        sources_checked,
        fake_news_verdict,
        fake_news_confidence,
    ) = reasoning.get_explanation(
        input_text,
        fake_news_verdict,
        fake_news_confidence,
        ai_text_verdict,
        ai_text_confidence,
    )

    scan = NewsScan(
        user_id=current_user.id,
        input_text=input_text,
        fake_news_verdict=fake_news_verdict,
        fake_news_confidence=fake_news_confidence,
        ai_text_verdict=ai_text_verdict,
        ai_text_confidence=ai_text_confidence,
        explanation=explanation,
    )

    try:
        db.session.add(scan)
        db.session.commit()

    except Exception:
        db.session.rollback()
        traceback.print_exc()

        return jsonify({
            "error": "The text scan could not be saved."
        }), 500

    response = {
        "message": "Text analyzed successfully.",
        "fake_news_verdict": fake_news_verdict,
        "fake_news_confidence": fake_news_confidence,
        "ai_text_verdict": ai_text_verdict,
        "ai_text_confidence": ai_text_confidence,
        "scan_id": scan.id,
        "created_at": scan.created_at.isoformat(),
    }

    if explanation is not None:
        response["explanation"] = explanation
        response["sources_checked"] = sources_checked

    return jsonify(response), 200


# ============================================================
# MEDIA SCANNING
# ============================================================

@inputs_bp.route("/media", methods=["POST"])
@token_required
def scan_media(current_user):

    # --------------------------------------------------------
    # 1. Validate upload
    # --------------------------------------------------------

    if "file" not in request.files:
        return jsonify({
            "error": (
                "No file part in the request. "
                "Expected field name 'file'."
            )
        }), 400

    uploaded_file = request.files["file"]

    if uploaded_file.filename == "":
        return jsonify({
            "error": "No file selected."
        }), 400

    extension = _get_extension(uploaded_file.filename)

    is_image = extension in ALLOWED_IMAGE_EXTENSIONS
    is_video = extension in ALLOWED_VIDEO_EXTENSIONS

    if not (is_image or is_video):
        return jsonify({
            "error": (
                f"Unsupported file type '.{extension}'. "
                "Allowed extensions: "
                f"{sorted(ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS)}"
            )
        }), 400

    # --------------------------------------------------------
    # 2. Check file size
    # --------------------------------------------------------

    uploaded_file.seek(0, os.SEEK_END)
    size_bytes = uploaded_file.tell()
    uploaded_file.seek(0)

    if size_bytes > MAX_FILE_SIZE_BYTES:
        return jsonify({
            "error": (
                f"File too large "
                f"({size_bytes / (1024 * 1024):.1f} MB). "
                "Maximum allowed size is 50 MB."
            )
        }), 400

    if size_bytes == 0:
        return jsonify({
            "error": "The uploaded file is empty."
        }), 400

    # --------------------------------------------------------
    # 3. Save uploaded file
    # --------------------------------------------------------

    safe_name = secure_filename(uploaded_file.filename)

    if not safe_name:
        return jsonify({
            "error": "The uploaded filename is invalid."
        }), 400

    unique_name = f"{uuid.uuid4().hex}_{safe_name}"

    save_path = os.path.join(
        UPLOAD_FOLDER,
        unique_name,
    )

    uploaded_file.save(save_path)

    media_type = "image" if is_image else "video"

    # --------------------------------------------------------
    # 4. Extract frames and detect faces
    # --------------------------------------------------------

    try:
        result = process_media(
            save_path,
            media_type,
        )

    except ValueError as exc:
        print(
            f"[VeriSight] Media processing failed: {exc}"
        )

        return jsonify({
            "error": f"Could not process file: {str(exc)}"
        }), 400

    except Exception:
        traceback.print_exc()

        return jsonify({
            "error": (
                "An unexpected error occurred "
                "during media processing."
            )
        }), 500

    frames = result.get("frames") or []
    face_crops = result.get("face_crops") or []

    # --------------------------------------------------------
    # 5. Run the two existing media classifiers
    # --------------------------------------------------------

    try:
        (
            deepfake_verdict,
            deepfake_confidence,
            per_face_results,
        ) = model_loader.predict_deepfake(face_crops)

        (
            ai_image_verdict,
            ai_image_confidence,
            per_frame_results,
        ) = model_loader.predict_ai_image(frames)

    except RuntimeError as exc:
        print(
            f"[VeriSight] Media model unavailable: {exc}"
        )

        return jsonify({
            "error": str(exc)
        }), 503

    except Exception:
        traceback.print_exc()

        return jsonify({
            "error": (
                "An unexpected error occurred "
                "during model inference."
            )
        }), 500

    # --------------------------------------------------------
    # 6. Select representative frame
    # --------------------------------------------------------

    representative_frame = (
        frames[0] if frames else None
    )

    # --------------------------------------------------------
    # 7. Run independent DDA image detection
    # --------------------------------------------------------

    dda_result = _run_dda_detection(
        representative_frame
    )

    # --------------------------------------------------------
    # 8. Inspect C2PA content credentials
    # --------------------------------------------------------

    c2pa_result = _run_c2pa_inspection(
        save_path
    )

    # --------------------------------------------------------
    # 9. Compare representative frame against local images
    # --------------------------------------------------------

    local_matches = _run_local_visual_search(
        representative_frame
    )

    # --------------------------------------------------------
    # 10. Build existing combined evidence assessment
    # --------------------------------------------------------

    evidence_assessment = _build_evidence_safely(
        media_type=media_type,
        ai_image_verdict=ai_image_verdict,
        ai_image_confidence=ai_image_confidence,
        deepfake_verdict=deepfake_verdict,
        deepfake_confidence=deepfake_confidence,
        c2pa_result=c2pa_result,
        local_matches=local_matches,
    )

    # --------------------------------------------------------
    # 11. Generate manual reverse-search links
    # --------------------------------------------------------

    manual_search_links = _generate_manual_search_links(
        media_type
    )

    # --------------------------------------------------------
    # 12. Compute VeriSight Trust Index (Weighted Ensemble)
    # --------------------------------------------------------

    verisight_trust_index = calculate_verisight_trust_index(
        media_type=media_type,
        dda_result=dda_result,
        ai_image_verdict=ai_image_verdict,
        ai_image_confidence=ai_image_confidence,
        deepfake_confidence=deepfake_confidence,
        deepfake_verdict=deepfake_verdict
    )

    # Align individual card labels dynamically based on Trust Index risk tier
    if verisight_trust_index.get("risk_level") == "low_risk":
        card_ai_image_verdict = "Real"
        card_ai_image_confidence = round(100.0 - verisight_trust_index["overall_synthetic_probability"], 2)
        card_ai_image_color = "green"
    elif verisight_trust_index.get("risk_level") == "high_synthetic_risk":
        card_ai_image_verdict = "AI Generated"
        card_ai_image_confidence = ai_image_confidence
        card_ai_image_color = "red"
    else:
        card_ai_image_verdict = ai_image_verdict
        card_ai_image_confidence = ai_image_confidence
        card_ai_image_color = "red" if ai_image_verdict in ["ai_generated", "fake", "synthetic"] else "green"

    # --------------------------------------------------------
    # 13. Save scan using the existing database schema
    # --------------------------------------------------------

    scan = MediaScan(
        user_id=current_user.id,
        file_path=unique_name,
        media_type=media_type,
        frames_analyzed=result.get(
            "frames_analyzed",
            len(frames),
        ),
        deepfake_verdict=deepfake_verdict,
        deepfake_confidence=deepfake_confidence,
        ai_image_verdict=card_ai_image_verdict,
        ai_image_confidence=card_ai_image_confidence,
    )

    try:
        db.session.add(scan)
        db.session.commit()

    except Exception:
        db.session.rollback()
        traceback.print_exc()

        return jsonify({
            "error": (
                "The media scan could not be saved "
                "to the database."
            )
        }), 500

    # --------------------------------------------------------
    # 14. Return results
    # --------------------------------------------------------

    response = {
        "message": "Media analysis completed.",
        "media_type": media_type,
        "original_filename": safe_name,
        "file_url": f"/uploads/{unique_name}",
        "size_mb": round(
            size_bytes / (1024 * 1024),
            2,
        ),

        "frames_analyzed": result.get(
            "frames_analyzed",
            len(frames),
        ),
        "frames_with_faces": result.get(
            "frames_with_faces",
            0,
        ),
        "faces_found": result.get(
            "faces_found",
            len(face_crops),
        ),

        # Unified Ensemble Trust Index
        "verisight_trust_index": verisight_trust_index,

        # Deepfake detector card data
        "deepfake_verdict": deepfake_verdict,
        "deepfake_confidence": deepfake_confidence,
        "deepfake_details": per_face_results,

        # Synchronized AI-image detector card data (includes color flag)
        "ai_image_verdict": card_ai_image_verdict,
        "ai_image_confidence": card_ai_image_confidence,
        "ai_image_color": card_ai_image_color,
        "ai_image_details": per_frame_results,

        # Independent DDA detector data
        "dda_ai_image": dda_result,

        # Verification features
        "c2pa": c2pa_result,
        "local_visual_search": local_matches,
        "evidence_assessment": evidence_assessment,
        "manual_search_links": manual_search_links,

        # Database metadata
        "scan_id": scan.id,
        "submitted_by": current_user.username,

        "limitations": [
            (
                "Classifier predictions are estimates, "
                "not proof that media is genuine or manipulated."
            ),
            (
                "C2PA credential absence does not establish "
                "that media is fake."
            ),
            (
                "Local visual matching searches only the configured "
                "local reference-image collection."
            ),
            (
                "Manual reverse-search links do not mean an automatic "
                "internet-wide reverse-image search was performed."
            ),
            (
                "The AI-image classifier and face-manipulation "
                "classifier perform different tasks."
            ),
            (
                "DDA returns an uncalibrated fake-image score. "
                "It is an additional signal, not a definitive verdict, "
                "and does not override existing detector results."
            ),
            (
                "For video uploads, DDA analyzes only the first "
                "successfully extracted frame."
            ),
        ],
    }

    return jsonify(response), 200