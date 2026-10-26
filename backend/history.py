"""
Module 12 support: GET /history

Returns the logged-in user's own scan history (FR-19/FR-20), combining
NewsScan and MediaScan records into one chronological list. Each entry
carries only what that scan type actually has — the frontend renders
based on 'type'.
"""

from flask import Blueprint, jsonify
from auth import token_required
from models import NewsScan, MediaScan

history_bp = Blueprint("history", __name__, url_prefix="/history")


@history_bp.route("", methods=["GET"])
@token_required
def get_history(current_user):
    news_scans = NewsScan.query.filter_by(user_id=current_user.id).all()
    media_scans = MediaScan.query.filter_by(user_id=current_user.id).all()

    combined = []

    for scan in news_scans:
        combined.append({
            "id": f"news-{scan.id}",
            "type": "text",
            "preview": scan.input_text[:120] + ("..." if len(scan.input_text) > 120 else ""),
            "fake_news_verdict": scan.fake_news_verdict,
            "fake_news_confidence": scan.fake_news_confidence,
            "ai_text_verdict": scan.ai_text_verdict,
            "ai_text_confidence": scan.ai_text_confidence,
            "created_at": scan.created_at.isoformat(),
        })

    for scan in media_scans:
        combined.append({
            "id": f"media-{scan.id}",
            "type": scan.media_type,
            "preview": scan.file_path,
            "frames_analyzed": scan.frames_analyzed,
            "deepfake_verdict": scan.deepfake_verdict,
            "deepfake_confidence": scan.deepfake_confidence,
            "ai_image_verdict": scan.ai_image_verdict,
            "ai_image_confidence": scan.ai_image_confidence,
            "created_at": scan.created_at.isoformat(),
        })

    combined.sort(key=lambda x: x["created_at"], reverse=True)

    return jsonify({"history": combined, "total": len(combined)}), 200