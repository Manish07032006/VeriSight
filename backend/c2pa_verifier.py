"""
VeriSight - C2PA Content Credentials Inspector

Uses c2patool CLI to inspect media provenance.

Important:
    - Missing C2PA credentials do not mean media is fake.
    - A valid signature does not prove depicted content is true.
    - Signature/content integrity and signer trust are separate.
    - CLI output formats may differ between c2patool versions.
"""

import json
import os
import shutil
import subprocess


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_C2PATOOL_PATH = (
    r"D:\PROJECT\tools\c2patool\c2patool.exe"
)


# ============================================================
# RESULT HELPERS
# ============================================================

def _base_result(status, message):
    """Create a consistent base response."""

    return {
        "status": status,
        "message": message,
        "credentials_found": None,
        "signature_valid": None,
        "signer_trusted": None,
    }


def _find_executable():
    """
    Find c2patool using this priority:

    1. C2PATOOL_PATH environment variable.
    2. Configured default Windows path.
    3. Executable available on PATH.
    """

    configured = os.getenv("C2PATOOL_PATH")

    if configured:
        configured = configured.strip().strip('"')

        if os.path.isfile(configured):
            return configured

        # If the configured value is a command name, search PATH.
        return shutil.which(configured)

    if os.path.isfile(DEFAULT_C2PATOOL_PATH):
        return DEFAULT_C2PATOOL_PATH

    return shutil.which("c2patool")


# ============================================================
# OUTPUT PARSING
# ============================================================

def _parse_tool_output(raw_output):
    """
    Parse JSON output when available.

    Returns:
        (payload, text_output)

    payload is a dictionary/list when JSON parsing succeeds.
    text_output contains unparsed text otherwise.
    """

    raw_output = (raw_output or "").strip()

    if not raw_output:
        return None, None

    try:
        return json.loads(raw_output), None

    except json.JSONDecodeError:
        return None, raw_output


def _extract_json_payload(stdout, stderr):
    """
    Prefer JSON from stdout, then attempt stderr.

    Diagnostics are preserved separately by inspect_c2pa().
    """

    for output in (stdout, stderr):
        payload, text_output = _parse_tool_output(output)

        if isinstance(payload, dict):
            return payload

    return None


# ============================================================
# VALIDATION RESULT EXTRACTION
# ============================================================

def _validation_entries(payload):
    """
    Extract validation entries from c2patool detailed JSON.

    Expected structure:

        validation_results.activeManifest.success
        validation_results.activeManifest.failure
        validation_results.activeManifest.informational
    """

    if not isinstance(payload, dict):
        return [], [], []

    results = payload.get("validation_results")

    if not isinstance(results, dict):
        return [], [], []

    active = results.get("activeManifest")

    if not isinstance(active, dict):
        return [], [], []

    def normalize(items):
        if not isinstance(items, list):
            return []

        return [
            item
            for item in items
            if isinstance(item, dict)
        ]

    return (
        normalize(active.get("success", [])),
        normalize(active.get("failure", [])),
        normalize(active.get("informational", [])),
    )


# ============================================================
# CREDENTIAL PRESENCE
# ============================================================

def _contains_recognizable_credentials(payload):
    """
    Detect likely manifest structures without relying on generic
    text matches.

    Returns True only when a recognized manifest field is present.
    """

    if not isinstance(payload, dict):
        return False

    active_manifest = payload.get("active_manifest")
    manifests = payload.get("manifests")

    if isinstance(active_manifest, str) and active_manifest.strip():
        return True

    if isinstance(active_manifest, dict) and active_manifest:
        return True

    if isinstance(manifests, dict) and manifests:
        return True

    # Accommodate alternative output field names.
    for key in ("activeManifest", "manifest"):
        value = payload.get(key)

        if isinstance(value, (dict, list)) and value:
            return True

        if isinstance(value, str) and value.strip():
            return True

    return False


# ============================================================
# VALIDATION CLASSIFICATION
# ============================================================

def _classify_validation(payload):
    """
    Classify integrity and signer trust separately.

    Returns:
        status
        message
        signature_valid
        signer_trusted
        validation_successes
        validation_failures
        validation_informational
    """

    success, failure, informational = _validation_entries(
        payload
    )

    success_codes = {
        str(item.get("code", "")).strip().lower()
        for item in success
    }

    failure_codes = {
        str(item.get("code", "")).strip().lower()
        for item in failure
    }

    # --------------------------------------------------------
    # 1. Detect explicit integrity failures
    # --------------------------------------------------------

    integrity_failure_tokens = (
        "claimsignature.mismatch",
        "claimsignature.invalid",
        "claimsignature.missing",
        "assertion.datahash.mismatch",
        "assertion.datahash.invalid",
        "assertion.hasheduri.mismatch",
        "assertion.hasheduri.invalid",
        "manifest.datahash.mismatch",
        "manifest.datahash.invalid",
    )

    integrity_failed = any(
        token in code
        for code in failure_codes
        for token in integrity_failure_tokens
    )

    # --------------------------------------------------------
    # 2. Check claim signature validation
    # --------------------------------------------------------

    signature_validated = any(
        code in success_codes
        for code in (
            "claimsignature.validated",
            "claimsignature.valid",
        )
    )

    # --------------------------------------------------------
    # 3. Check content hash validation
    # --------------------------------------------------------

    data_hash_validated = any(
        code in success_codes
        for code in (
            "assertion.datahash.match",
            "assertion.datahash.valid",
            "manifest.datahash.match",
        )
    )

    # --------------------------------------------------------
    # 4. Evaluate signer trust separately
    # --------------------------------------------------------

    untrusted_tokens = (
        "signingcredential.untrusted",
        "signingcredential.invalid",
        "signingcredential.revoked",
        "signingcredential.expired",
    )

    signer_untrusted = any(
        token in code
        for code in failure_codes
        for token in untrusted_tokens
    )

    trusted_tokens = (
        "signingcredential.trusted",
        "signingcredential.valid",
        "signingcredential.chain.valid",
    )

    signer_trusted_success = any(
        token in code
        for code in success_codes
        for token in trusted_tokens
    )

    if signer_untrusted:
        signer_trusted = False

    elif signer_trusted_success:
        signer_trusted = True

    else:
        signer_trusted = None

    # --------------------------------------------------------
    # 5. Preserve validation details
    # --------------------------------------------------------

    success_details = [
        {
            "code": item.get("code"),
            "explanation": item.get("explanation"),
        }
        for item in success
    ]

    failure_details = [
        {
            "code": item.get("code"),
            "explanation": item.get("explanation"),
        }
        for item in failure
    ]

    informational_details = [
        {
            "code": item.get("code"),
            "explanation": item.get("explanation"),
        }
        for item in informational
    ]

    # --------------------------------------------------------
    # 6. Determine final status
    # --------------------------------------------------------

    if integrity_failed:
        status = "credentials_invalid"

        message = (
            "C2PA credentials were found, but signature or "
            "content-integrity validation reported a failure."
        )

        signature_valid = False

    elif signature_validated and data_hash_validated:
        signature_valid = True

        if signer_trusted is False:
            status = "credentials_untrusted"

            message = (
                "The claim signature and content data hash "
                "validated, but the signing certificate is "
                "untrusted or failed a certificate requirement."
            )

        elif signer_trusted is True:
            status = "credentials_valid"

            message = (
                "The claim signature, content data hash, and "
                "recognized signer-trust checks passed."
            )

        else:
            status = "credentials_found_validation_unclear"

            message = (
                "The claim signature and content data hash "
                "validated, but signer trust could not be "
                "determined."
            )

    else:
        status = "credentials_found_validation_unclear"

        signature_valid = None

        message = (
            "C2PA credentials were found, but the available "
            "validation details do not establish both claim "
            "signature and content-hash validity."
        )

    return {
        "status": status,
        "message": message,
        "signature_valid": signature_valid,
        "signer_trusted": signer_trusted,
        "validation_successes": success_details,
        "validation_failures": failure_details,
        "validation_informational": informational_details,
    }


# ============================================================
# MAIN INSPECTION FUNCTION
# ============================================================

def inspect_c2pa(file_path, timeout_seconds=20):
    """
    Inspect an image or other supported asset using c2patool.

    Returns structured information about:

        - Credential presence
        - Signature/content integrity
        - Signer trust
        - Validation diagnostics

    This function does not decide whether media is fake.
    """

    # --------------------------------------------------------
    # 1. Validate input path
    # --------------------------------------------------------

    if not isinstance(file_path, (str, os.PathLike)):
        return _base_result(
            "error",
            "A valid file path must be provided.",
        )

    file_path = os.fspath(file_path)

    if not os.path.isfile(file_path):
        return _base_result(
            "error",
            "File not found.",
        )

    # --------------------------------------------------------
    # 2. Validate timeout
    # --------------------------------------------------------

    try:
        timeout_seconds = float(timeout_seconds)

        if timeout_seconds <= 0:
            raise ValueError

    except (TypeError, ValueError):
        return _base_result(
            "error",
            "timeout_seconds must be a positive number.",
        )

    # --------------------------------------------------------
    # 3. Locate c2patool
    # --------------------------------------------------------

    executable = _find_executable()

    if not executable:
        return _base_result(
            "unavailable",
            (
                "c2patool could not be located. Check "
                "C2PATOOL_PATH and the executable installation."
            ),
        )

    # --------------------------------------------------------
    # 4. Execute c2patool
    # --------------------------------------------------------

    try:
        process = subprocess.run(
            [
                executable,
                file_path,
                "--detailed",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

    except subprocess.TimeoutExpired:
        return _base_result(
            "unavailable",
            "C2PA inspection timed out.",
        )

    except OSError as exc:
        result = _base_result(
            "unavailable",
            (
                "Could not execute c2patool. Check its "
                "installation and executable path."
            ),
        )

        result["diagnostic"] = str(exc)

        return result

    # --------------------------------------------------------
    # 5. Collect stdout and stderr
    # --------------------------------------------------------

    stdout = (process.stdout or "").strip()
    stderr = (process.stderr or "").strip()

    combined_output = "\n".join(
        part
        for part in (stdout, stderr)
        if part
    )

    if not combined_output:
        result = _base_result(
            "inspection_error",
            "c2patool returned no output.",
        )

        result["tool_return_code"] = process.returncode

        return result

    # --------------------------------------------------------
    # 6. Handle the known no-claim result
    # --------------------------------------------------------

    if "no claim found" in combined_output.lower():
        result = _base_result(
            "not_found_or_unavailable",
            (
                "No C2PA content credentials were found in this "
                "file. This does not mean the image is fake "
                "or authentic."
            ),
        )

        result["credentials_found"] = False
        result["tool_return_code"] = process.returncode
        result["diagnostic"] = combined_output

        return result

    # --------------------------------------------------------
    # 7. Parse JSON output
    # --------------------------------------------------------

    payload = _extract_json_payload(
        stdout,
        stderr,
    )

    # A nonzero return code with no recognized JSON indicates
    # an inspection failure, unless it was the no-claim case.
    if process.returncode != 0 and payload is None:
        result = _base_result(
            "inspection_error",
            (
                "c2patool could not complete the inspection. "
                "Review the diagnostic output."
            ),
        )

        result["tool_return_code"] = process.returncode
        result["raw_tool_output"] = stdout or None

        if stderr:
            result["diagnostic"] = stderr

        return result

    # --------------------------------------------------------
    # 8. Handle unrecognized output
    # --------------------------------------------------------

    if payload is None:
        result = _base_result(
            "inspection_error",
            (
                "c2patool output was not recognized as "
                "structured JSON. Credential presence and "
                "validation could not be determined reliably."
            ),
        )

        result["raw_tool_output"] = stdout or stderr
        result["tool_return_code"] = process.returncode

        return result

    # --------------------------------------------------------
    # 9. Check whether a recognizable manifest exists
    # --------------------------------------------------------

    if not _contains_recognizable_credentials(payload):
        result = _base_result(
            "not_found_or_unavailable",
            (
                "No recognizable C2PA manifest was found. "
                "This does not mean the media is fake."
            ),
        )

        result["credentials_found"] = False
        result["raw_tool_output"] = payload
        result["tool_return_code"] = process.returncode

        return result

    # --------------------------------------------------------
    # 10. Classify validation evidence
    # --------------------------------------------------------

    classification = _classify_validation(
        payload
    )

    result = {
        **classification,
        "credentials_found": True,
        "raw_tool_output": payload,
        "tool_return_code": process.returncode,
    }

    return result