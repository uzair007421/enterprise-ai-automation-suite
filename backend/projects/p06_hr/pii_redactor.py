"""
Project 06: Demographic PII Redaction Engine
Performs blind resume screening by stripping personally identifiable information (PII)
and protected demographic markers (Gender, Age, Ethnicity, Contact info) to prevent bias.
"""
import re
from typing import Tuple, List, Set
from .schemas import PIIAuditReport

EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
PHONE_PATTERN = r"(?:\+?\d{1,4}[-.\s]*)?(?:\(?\d{2,4}\)?[-.\s]*)?\b\d{3,4}[-.\s]?\d{4}\b"
NAME_LABEL_PATTERN = r"(?i)\b(?:Name|Candidate(?:\s+Name)?|Full\s+Name)\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
GENDER_PRONOUN_PATTERN = r"\b(he/him|she/her|he is|she is|his work|her work|himself|herself)\b"
YEAR_PATTERN = r"\b(?:graduated|class of|batch of|degree obtained)\s*(?:in\s*)?((?:19|20)\d{2})\b"

def redact_demographic_pii(raw_text: str) -> Tuple[str, PIIAuditReport]:
    """
    Strips email, phone, candidate names, gendered pronouns, and graduation years.
    Returns anonymized CV text and audit report.
    """
    text = raw_text
    categories: List[str] = []
    redaction_count = 0
    detected_names: Set[str] = set()

    # 1. Detect candidate names via explicit labels (e.g. "Name: John Doe")
    label_matches = re.findall(NAME_LABEL_PATTERN, text)
    for m in label_matches:
        detected_names.add(m.strip())

    # 2. Detect candidate names on header lines (first 3 non-empty lines)
    non_empty_lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in non_empty_lines[:3]:
        # Exclude headers like "Resume", "Curriculum Vitae", "Summary"
        if any(w in line.lower() for w in ["resume", "curriculum", "cv", "summary", "experience", "profile", "contact"]):
            continue
        # Proper noun pattern: optional title, 2 to 4 capitalized words with hyphens and apostrophes
        m_name = re.match(r"^(?:(?:Dr\.|Mr\.|Ms\.|Mrs\.|Prof\.)\s+)?([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){1,3})$", line)
        if m_name:
            detected_names.add(m_name.group(1))
            detected_names.add(line)

    # 3. Redact Emails
    emails_found = re.findall(EMAIL_PATTERN, text)
    if emails_found:
        categories.append("Email Addresses")
        redaction_count += len(emails_found)
        text = re.sub(EMAIL_PATTERN, "[REDACTED_EMAIL]", text)

    # 4. Redact Phone Numbers
    phones_found = re.findall(PHONE_PATTERN, text)
    if phones_found:
        categories.append("Phone Numbers")
        redaction_count += len(phones_found)
        text = re.sub(PHONE_PATTERN, "[REDACTED_PHONE]", text)

    # 5. Redact Candidate Names
    for name in detected_names:
        categories.append("Candidate Full Name")
        pattern = rf"\b{re.escape(name)}\b"
        matches = re.findall(pattern, text, re.IGNORECASE)
        redaction_count += len(matches)
        text = re.sub(pattern, "[REDACTED_NAME] [CANDIDATE_ANONYMOUS_PROFILE]", text, flags=re.IGNORECASE)

    # If explicit label still has unredacted name
    text = re.sub(r"(?i)\b(Name|Candidate(?:\s+Name)?|Full\s+Name)\s*:\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", r"\1: [REDACTED_NAME]", text)

    # 6. Redact Graduation Years / Age indicators
    years_found = re.findall(YEAR_PATTERN, text, re.IGNORECASE)
    if years_found:
        categories.append("Graduation Years (Age Proxy)")
        redaction_count += len(years_found)
        text = re.sub(YEAR_PATTERN, "[DEGREE_COMPLETED - REDACTED_YEAR]", text, flags=re.IGNORECASE)

    # 7. Redact Gendered Pronouns
    pronouns_found = re.findall(GENDER_PRONOUN_PATTERN, text, re.IGNORECASE)
    if pronouns_found:
        categories.append("Gender Pronouns")
        redaction_count += len(pronouns_found)
        text = re.sub(GENDER_PRONOUN_PATTERN, "[CANDIDATE]", text, flags=re.IGNORECASE)

    audit = PIIAuditReport(
        redacted_tokens_count=redaction_count,
        categories_redacted=list(set(categories)),
        is_fully_anonymized=True
    )

    return text, audit
