"""
Bidirectional PII Interceptor.

Input  (pre-LLM):  anonymize PII in user prompts before forwarding.
Output (post-LLM): hard-block responses that contain raw PII.
"""
import re
from typing import Tuple

PII_PATTERNS: dict[str, str] = {
    "EMAIL":       r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    "PHONE":       r"\b(?:\+\d{1,3}[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b",
    "CREDIT_CARD": r"\b(?:\d{4}[\s\-]?){3}\d{4}\b",
    "SSN":         r"\b(?:\d{3}-\d{2}-\d{4}|\d{9})\b",
    "IP_ADDRESS":  r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "PASSPORT":    r"\b[A-Z]{1,2}\d{6,9}\b",
    "PHI_MRN":     r"\b(?:MRN|mrn|Patient ID)[\s:#\-]*\d{5,10}\b",
}


def scan_and_anonymize(text: str) -> Tuple[bool, list[str], str]:
    """
    Scan text for PII and replace matches with typed placeholders.

    Returns:
        has_pii      — True if any PII was detected.
        detected     — List of PII type names found.
        clean_text   — Text with PII replaced by <TYPE> tokens.
    """
    detected: list[str] = []
    clean = text

    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, clean):
            detected.append(pii_type)
            clean = re.sub(pattern, f"<{pii_type}>", clean)

    return bool(detected), detected, clean


def output_contains_pii(text: str) -> Tuple[bool, list[str]]:
    """
    Check LLM output for raw PII without anonymizing (output is not forwarded).

    Returns:
        has_pii  — True if PII is present.
        detected — List of PII type names found.
    """
    detected = [
        pii_type
        for pii_type, pattern in PII_PATTERNS.items()
        if re.search(pattern, text)
    ]
    return bool(detected), detected
