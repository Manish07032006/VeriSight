"""
VeriSight — Cautious Media Evidence Assessment.

Combines:
    1. AI-generated image detection
    2. Deepfake / face-manipulation detection
    3. C2PA content credentials
    4. Local visual matching

Important:
    - Detector scores are never averaged.
    - Model predictions are not proof of authenticity.
    - Missing C2PA credentials do not mean media is fake.
    - Local matches do not independently prove authenticity.
    - Image-generation detection and face-manipulation detection
      are different tasks.
"""

from typing import Any, Dict, Optional


# ============================================================
# DETECTOR CLASSIFICATION
# ============================================================

def _classify(
    verdict: Optional[str],
    confidence: Any,
    kind: str,
) -> Dict[str, Any]:
    """
    Convert a detector's verdict into a standardized evidence status.

    The original verdict and confidence are preserved.
    Confidence is not interpreted as a calibrated probability.
    """

    if verdict is None or not str(verdict).strip():
        return {
            "status": "unavailable",
            "verdict": None,
            "model_score": None,
            "score_interpretation": (
                "No detector result was available."
            ),
        }

    normalized_verdict = str(verdict).strip().lower()

    if kind == "ai":
        if normalized_verdict in {
            "ai_generated",
            "ai-generated",
            "generated",
            "fake",
            "synthetic",
        }:
            status = "supports_ai_generated"

        elif normalized_verdict in {
            "authentic",
            "real",
            "real_image",
            "natural",
        }:
            status = "supports_authentic"

        else:
            status = "inconclusive"

    elif kind == "deepfake":
        if normalized_verdict in {
            "manipulated",
            "deepfake",
            "fake",
            "fake_face",
            "synthetic_face",
        }:
            status = "supports_manipulation"

        elif normalized_verdict in {
            "real",
            "authentic",
            "genuine",
            "not_manipulated",
        }:
            status = "no_manipulation_detected"

        else:
            status = "inconclusive"

    else:
        status = "inconclusive"

    return {
        "status": status,
        "verdict": normalized_verdict,
        "model_score": confidence,
        "score_interpretation": (
            "Model-reported score; not necessarily a calibrated "
            "probability."
        ),
    }


# ============================================================
# OPTIONAL EVIDENCE NORMALIZATION
# ============================================================

def _normalize_c2pa(
    c2pa_result: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Preserve useful C2PA information without interpreting missing
    credentials as evidence of manipulation.
    """

    if not isinstance(c2pa_result, dict):
        c2pa_result = {
            "status": "unavailable",
            "message": "C2PA inspection was unavailable.",
        }

    return {
        "status": c2pa_result.get("status", "unavailable"),
        "message": c2pa_result.get("message"),
        "credentials_found": c2pa_result.get(
            "credentials_found"
        ),
        "signature_valid": c2pa_result.get(
            "signature_valid"
        ),
        "signer_trusted": c2pa_result.get(
            "signer_trusted"
        ),
    }


def _normalize_local_matches(
    local_matches: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Normalize local visual-search results.

    Matches are returned as evidence for further inspection.
    They do not independently determine the overall verdict.
    """

    if not isinstance(local_matches, dict):
        local_matches = {
            "status": "unavailable",
            "message": "Local visual matching was unavailable.",
            "reference_images_scanned": 0,
            "matches": [],
        }

    matches = local_matches.get("matches", [])

    if not isinstance(matches, list):
        matches = []

    scanned = local_matches.get(
        "reference_images_scanned",
        0,
    )

    try:
        scanned = max(0, int(scanned or 0))
    except (TypeError, ValueError):
        scanned = 0

    return {
        "status": local_matches.get(
            "status",
            "unavailable",
        ),
        "message": local_matches.get("message"),
        "reference_images_scanned": scanned,
        "matches": matches,
    }


# ============================================================
# OVERALL EVIDENCE ASSESSMENT
# ============================================================

def build_media_evidence(
    media_type,
    ai_image_verdict,
    ai_image_confidence,
    deepfake_verdict,
    deepfake_confidence,
    c2pa_result,
    local_matches,
):
    """
    Build a cautious, explainable assessment from independent evidence.

    The function does not average model scores.

    Overall statuses:

        potentially_synthetic_or_manipulated
            At least one visual detector flagged a concern.

        no_issue_detected_by_available_models
            Both relevant visual detectors returned recognized
            non-flagging verdicts.

        inconclusive
            Results are unavailable, ambiguous, or insufficient.

    A non-flagging result does not establish authenticity.
    """

    normalized_media_type = (
        str(media_type).strip().lower()
        if media_type is not None
        else "unknown"
    )

    # --------------------------------------------------------
    # 1. Normalize detector results
    # --------------------------------------------------------

    ai = _classify(
        ai_image_verdict,
        ai_image_confidence,
        "ai",
    )

    deepfake = _classify(
        deepfake_verdict,
        deepfake_confidence,
        "deepfake",
    )

    # --------------------------------------------------------
    # 2. Determine whether the available detector evidence
    #    raises a concern
    # --------------------------------------------------------

    ai_flagged = (
        ai["status"] == "supports_ai_generated"
    )

    deepfake_flagged = (
        deepfake["status"] == "supports_manipulation"
    )

    if ai_flagged or deepfake_flagged:
        overall_status = (
            "potentially_synthetic_or_manipulated"
        )

        explanation = (
            "At least one visual detector flagged a concern. "
            "This is a model-based indication, not proof that "
            "the media is synthetic or manipulated."
        )

    # Both detectors must return recognized non-flagging
    # results before this status is used.
    elif (
        ai["status"] == "supports_authentic"
        and deepfake["status"] == "no_manipulation_detected"
    ):
        overall_status = (
            "no_issue_detected_by_available_models"
        )

        explanation = (
            "Neither visual detector flagged a concern. "
            "This does not prove that the media is authentic."
        )

    else:
        overall_status = "inconclusive"

        explanation = (
            "The visual evidence is insufficient or ambiguous. "
            "One or both detectors may be unavailable, or their "
            "outputs may not map to a recognized verdict."
        )

    # --------------------------------------------------------
    # 3. Normalize independent provenance and matching evidence
    # --------------------------------------------------------

    provenance = _normalize_c2pa(c2pa_result)

    local_search = _normalize_local_matches(
        local_matches
    )

    # --------------------------------------------------------
    # 4. Build response
    # --------------------------------------------------------

    limitations = [
        (
            "Classifier predictions are estimates and do not "
            "guarantee authenticity or manipulation."
        ),
        (
            "AI-generated image detection and face-manipulation "
            "detection are different tasks."
        ),
        (
            "Missing C2PA credentials do not mean media is fake."
        ),
        (
            "A valid content-credential signature does not, by "
            "itself, prove that the depicted event is genuine."
        ),
        (
            "An untrusted signer does not automatically mean that "
            "the media has been manipulated."
        ),
        (
            "A local visual match is supporting evidence, not "
            "independent proof of authenticity."
        ),
        (
            "No local match is not proof of authenticity."
        ),
        (
            "Local visual matching does not automatically search "
            "the entire public internet."
        ),
    ]

    if normalized_media_type == "video":
        limitations.append(
            "Frame-based predictions may not represent every "
            "part of the video."
        )

    return {
        "media_type": normalized_media_type,
        "overall_status": overall_status,
        "explanation": explanation,
        "ai_image_detection": ai,
        "deepfake_detection": deepfake,
        "provenance": provenance,
        "local_visual_search": local_search,
        "limitations": limitations,
    }