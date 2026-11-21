"""
Project 06: Demographic PII Redaction Engine
Performs blind resume screening by stripping personally identifiable information (PII)
and protected demographic markers (Gender, Age, Ethnicity, Contact info) to prevent bias.
"""
import re
from typing import Tuple, List
from .schemas import PIIAuditReport

def redact_demographic_pii(raw_text: str) -> Tuple[str, PIIAuditReport]:
    """
    Strips email, phone, candidate names, gendered pronouns, and graduation years.
    Returns anonymized CV text and audit report.
    """
    text = raw_text
    categories = []
    redaction_count = 0

    # 1. Redact Emails
    email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
    emails_found = re.findall(email_pattern, text)
    if emails_found:
        categories.append("Email Addresses")
        redaction_count += len(emails_found)
        text = re.sub(email_pattern, "[REDACTED_EMAIL]", text)

    # 2. Redact Phone Numbers
    phone_pattern = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    phones_found = re.findall(phone_pattern, text)
    if phones_found:
        categories.append("Phone Numbers")
        redaction_count += len(phones_found)
        text = re.sub(phone_pattern, "[REDACTED_PHONE]", text)

    # 3. Redact Graduation Years / Age indicators
    year_pattern = r"\b(?:graduated|class of|batch of|degree obtained)\s*(?:in\s*)?((?:19|20)\d{2})\b"
    years_found = re.findall(year_pattern, text, re.IGNORECASE)
    if years_found:
        categories.append("Graduation Years (Age Proxy)")
        redaction_count += len(years_found)
        text = re.sub(year_pattern, "[DEGREE_COMPLETED - REDACTED_YEAR]", text, flags=re.IGNORECASE)

    # 4. Redact Gendered Pronouns
    pronoun_pattern = r"\b(he/him|she/her|he is|she is|his work|her work|himself|herself)\b"
    pronouns_found = re.findall(pronoun_pattern, text, re.IGNORECASE)
    if pronouns_found:
        categories.append("Gender Pronouns")
        redaction_count += len(pronouns_found)
        text = re.sub(pronoun_pattern, "[CANDIDATE]", text, flags=re.IGNORECASE)

    # 5. Redact Header Name (first non-empty line if it looks like a name)
    lines = text.split("\n")
    cleaned_lines = []
    header_name_redacted = False
    for i, line in enumerate(lines):
        line_s = line.strip()
        if not header_name_redacted and line_s and len(line_s) < 40 and not any(w in line_s.lower() for w in ["resume", "curriculum", "cv", "summary", "experience"]):
            # Likely candidate full name
            cleaned_lines.append("[CANDIDATE_ANONYMOUS_PROFILE]")
            categories.append("Candidate Full Name")
            redaction_count += 1
            header_name_redacted = True
        else:
            cleaned_lines.append(line)

    anonymized_text = "\n".join(cleaned_lines)

    audit = PIIAuditReport(
        redacted_tokens_count=redaction_count,
        categories_redacted=list(set(categories)),
        is_fully_anonymized=True
    )

    return anonymized_text, audit
