"""
VeriSight - Local Visual Search

Features:
    1. Compare uploaded images against a local reference library using pHash.
    2. Generate manual online visual-search links.
    3. Never upload images to external search providers automatically.

Important:
    - Local matching is not internet-wide reverse-image search.
    - Similarity does not prove that two images share the same origin.
    - No local match does not prove authenticity.
"""

from pathlib import Path

from PIL import Image, UnidentifiedImageError


# Supported image formats
EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
}

# Local reference library
REFERENCE_DIR = Path(__file__).resolve().parent / "reference_images"

# Limit the number of reference files inspected per request.
# Increase this after testing performance with your library.
MAX_REFERENCE_FILES = 5000


def _result(status, message, scanned=0, matches=None):
    """Return a consistent result structure."""
    return {
        "status": status,
        "message": message,
        "reference_images_scanned": scanned,
        "matches": matches or [],
    }


def _load_image(image):
    """
    Load an image as RGB.

    Accepts:
        - PIL.Image.Image
        - String file path
        - pathlib.Path

    Returns:
        PIL RGB image, or None if loading fails.
    """
    if image is None:
        return None

    try:
        if isinstance(image, Image.Image):
            return image.convert("RGB")

        if isinstance(image, (str, Path)):
            with Image.open(image) as opened_image:
                opened_image.load()
                return opened_image.convert("RGB")

    except (OSError, ValueError, UnidentifiedImageError):
        return None

    return None


def find_local_matches(
    image,
    reference_dir=None,
    max_distance=10,
    limit=10,
):
    """
    Search a local image library using perceptual hashing.

    Returns:
        status
        message
        reference_images_scanned
        matches
    """

    # 1. Validate query image
    query_image = _load_image(image)

    if query_image is None:
        return _result(
            "unavailable",
            "No valid image or frame was supplied.",
        )

    # 2. Load ImageHash
    try:
        import imagehash
    except ImportError:
        return _result(
            "unavailable",
            "ImageHash is not installed. Run: pip install ImageHash",
        )

    # 3. Validate parameters
    try:
        max_distance = int(max_distance)
        limit = int(limit)
    except (TypeError, ValueError):
        return _result(
            "unavailable",
            "max_distance and limit must be integers.",
        )

    if not 0 <= max_distance <= 64:
        return _result(
            "unavailable",
            "max_distance must be between 0 and 64.",
        )

    if not 1 <= limit <= 100:
        return _result(
            "unavailable",
            "limit must be between 1 and 100.",
        )

    # 4. Locate reference library
    try:
        root = (
            Path(reference_dir).expanduser().resolve()
            if reference_dir is not None
            else REFERENCE_DIR.resolve()
        )

        if not root.exists():
            return _result(
                "no_reference_library",
                f"No reference folder was found: {root}",
            )

        if not root.is_dir():
            return _result(
                "unavailable",
                "The reference path is not a directory.",
            )

    except (OSError, ValueError, TypeError):
        return _result(
            "unavailable",
            "The reference directory could not be accessed.",
        )

    # 5. Calculate query hash
    try:
        query_hash = imagehash.phash(query_image)
    except Exception:
        return _result(
            "unavailable",
            "Could not calculate the query image hash.",
        )

    matches = []
    scanned = 0
    inspected = 0

    # 6. Compare against local reference images
    try:
        for image_path in root.rglob("*"):
            if not image_path.is_file():
                continue

            if image_path.suffix.lower() not in EXTS:
                continue

            # Avoid excessively long scans.
            if inspected >= MAX_REFERENCE_FILES:
                break

            inspected += 1

            try:
                with Image.open(image_path) as reference_image:
                    reference_image.load()
                    reference_rgb = reference_image.convert("RGB")
                    reference_hash = imagehash.phash(reference_rgb)

                scanned += 1
                distance = int(query_hash - reference_hash)

                if distance <= max_distance:
                    try:
                        relative_path = str(
                            image_path.relative_to(root)
                        )
                    except ValueError:
                        relative_path = image_path.name

                    matches.append({
                        "filename": image_path.name,
                        "relative_path": relative_path,
                        "phash_distance": distance,
                    })

            except (
                OSError,
                ValueError,
                UnidentifiedImageError,
            ):
                # Ignore unreadable or invalid reference images.
                continue

    except OSError:
        return _result(
            "unavailable",
            "The reference library could not be read completely.",
            scanned,
            matches,
        )

    # 7. Rank closest matches first
    matches.sort(
        key=lambda item: item["phash_distance"]
    )

    matches = matches[:limit]

    # 8. Return assessment
    if matches:
        return _result(
            "matches_found",
            (
                "Possible similar images were found in the local "
                "reference library. Similarity does not prove origin "
                "or authenticity."
            ),
            scanned,
            matches,
        )

    message = (
        "No matching image was found in the local reference library. "
        "This does not establish whether the uploaded media is authentic."
    )

    if inspected >= MAX_REFERENCE_FILES:
        message += (
            " The scan reached its configured file limit, so not every "
            "reference image may have been inspected."
        )

    return _result(
        "no_local_matches",
        message,
        scanned,
        [],
    )


def make_manual_search_links(media_type="image"):
    """
    Generate manual online visual-search links.

    Images are not automatically uploaded to external providers.
    For videos, users must manually select a representative frame.
    """

    normalized_type = str(media_type).strip().lower()

    if normalized_type not in {"image", "video"}:
        normalized_type = "unknown"

    if normalized_type == "video":
        instructions = (
            "Capture a representative video frame, then manually "
            "select that image on the search provider's website."
        )
    elif normalized_type == "image":
        instructions = (
            "Open the search provider and manually select the image."
        )
    else:
        instructions = (
            "Manually select a supported image on the search provider's website."
        )

    return {
        "status": "manual_search_only",
        "message": (
            "These links open external visual-search services. "
            "VeriSight does not automatically upload images, search "
            "these providers, or scrape their results."
        ),
        "media_type": normalized_type,
        "search_pages": [
            {
                "provider": "Google Lens",
                "url": "https://lens.google.com/",
                "instructions": instructions,
            },
            {
                "provider": "Bing Visual Search",
                "url": "https://www.bing.com/visualsearch",
                "instructions": instructions,
            },
        ],
    }