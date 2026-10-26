"""
VeriSight DDA Client
--------------------
Calls the independent local DDA inference service.

DDA is an additional detection signal. Its score is not a
calibrated probability or a definitive authenticity verdict.

If DDA is unavailable, the remaining VeriSight media scan
continues normally.
"""

import io
import os

import requests
from PIL import Image


DDA_SERVICE_URL = os.getenv(
    "DDA_SERVICE_URL",
    "http://127.0.0.1:8765",
).rstrip("/")

DDA_TIMEOUT_SECONDS = 60
MAX_IMAGE_BYTES = 20 * 1024 * 1024


def _unavailable(message):
    return {
        "status": "unavailable",
        "model": "dinov2_vitl14",
        "device": None,
        "raw_score": None,
        "score_percent": None,
        "interpretation": (
            "DDA did not provide a usable result. "
            "Other VeriSight detectors can still run."
        ),
        "message": message,
    }


def predict_dda_image(image):
    """
    Analyze a representative PIL image using the DDA service.

    Args:
        image: PIL.Image.Image or None.

    Returns:
        Dictionary containing the DDA result or unavailable status.
    """

    if image is None:
        return _unavailable(
            "No representative image frame was available."
        )

    try:
        if not isinstance(image, Image.Image):
            return _unavailable(
                "The representative frame is not a PIL image."
            )

        # Encode in memory; do not create another image file.
        buffer = io.BytesIO()

        image.convert("RGB").save(
            buffer,
            format="JPEG",
            quality=95,
        )

        image_bytes = buffer.getvalue()
        buffer.close()

        if not image_bytes:
            return _unavailable(
                "Could not encode the representative image."
            )

        if len(image_bytes) > MAX_IMAGE_BYTES:
            return _unavailable(
                "The encoded image exceeds the DDA service's 20 MB limit."
            )

        response = requests.post(
            f"{DDA_SERVICE_URL}/predict",
            files={
                "file": (
                    "verisight_frame.jpg",
                    image_bytes,
                    "image/jpeg",
                )
            },
            timeout=DDA_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            return _unavailable(
                f"DDA service returned HTTP {response.status_code}."
            )

        try:
            result = response.json()
        except ValueError:
            return _unavailable(
                "DDA service returned an invalid JSON response."
            )

        # Accept both "available" and "success" status keys from the microservice
        service_status = result.get("status")
        if service_status not in ("available", "success"):
            return _unavailable(
                result.get(
                    "error",
                    "DDA inference was unavailable.",
                )
            )

        score = result.get("raw_score")

        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not 0.0 <= score <= 1.0
        ):
            return _unavailable(
                "DDA returned an invalid score."
            )

        return {
            "status": "available",
            "model": result.get(
                "model",
                "dinov2_vitl14",
            ),
            "device": result.get("device"),
            "raw_score": float(score),
            "score_percent": round(
                float(score) * 100.0,
                2,
            ),
            "interpretation": result.get(
                "interpretation",
                (
                    "Uncalibrated sigmoid score for the fake-image "
                    "class. This is not a calibrated probability "
                    "or definitive authenticity verdict."
                ),
            ),
        }

    except requests.Timeout:
        return _unavailable(
            "DDA inference timed out."
        )

    except requests.ConnectionError:
        return _unavailable(
            "Could not connect to the local DDA service."
        )

    except requests.RequestException:
        return _unavailable(
            "The DDA HTTP request failed."
        )

    except Exception:
        return _unavailable(
            "An unexpected error occurred during DDA inference."
        )