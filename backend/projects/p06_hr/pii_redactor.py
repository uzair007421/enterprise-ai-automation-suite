"""
Project 06: Demographic PII & Bias Redaction Engine
Performs blind resume screening by stripping personally identifiable information (PII)
and protected demographic markers (Gender, Age, Ethnicity, Religion, Family Status, Location, University)
to enforce unbiased merit-based hiring.
"""
import re
from typing import Tuple, List, Set
from .schemas import PIIAuditReport

EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
PHONE_PATTERN = r"(?:\+?\d{1,4}[-.\s]*)?(?:\(?\d{2,4}\)?[-.\s]*)?\b\d{3,4}[-.\s]?\d{4}\b"
NAME_LABEL_PATTERN = r"(?i)\b(?:Name|Candidate(?:\s+Name)?|Full\s+Name)\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
GENDER_PRONOUN_PATTERN = r"\b(he/him|she/her|he is|she is|his work|her work|himself|herself)\b"
YEAR_PATTERN = r"\b(?:graduated(?:\s+from\s+[^,\n]+?)?|class\s+of|batch\s+of|degree\s+obtained)\s*(?:in\s*)?((?:19|20)\d{2})\b"

DEMOGRAPHIC_GENDER = r"\b(female|male|woman|man|non-binary)\b"
DEMOGRAPHIC_FAMILY = r"\b(?:single\s+(?:mother|father|parent)|(?:mother|father|parent)\s+of\s+\w+|\d+\s+(?:kids|children|child|dependents)|kids|children|child|dependents|pregnant|maternity|paternity)\b"
DEMOGRAPHIC_MARITAL = r"\b(married|single|divorced|widowed|marital\s+status\s*:\s*\w+)\b"
DEMOGRAPHIC_RELIGION = r"\b(muslim|islamic|islam|christian|christianity|hindu|hinduism|sikh|sikhism|jewish|judaism|buddhist|buddhism|catholic|protestant)\b"
DEMOGRAPHIC_LOCATION = r"\b(lahore|karachi|islamabad|rawalpindi|peshawar|quetta|faisalabad|multan|pakistan|india|dubai|uae|london|uk|new york|nyc|california|austin|texas|seattle|toronto|canada)\b"
DEMOGRAPHIC_AGE = r"\b(?:age\s*[:\s]*\s*\d{1,2}|\d{1,2}\s*(?:yo|y\.o\.|years\s+old)|(?<=[,\s])(?:1[8-9]|[2-6]\d)(?=[,\s]))\b"

INSTITUTION_PATTERN = r"\b(?:[A-Z][a-zA-Z'\-]*(?:\s+[A-Z][a-zA-Z'\-]*)*\s+(?:University|College|Institute|Academy|School)|(?:University|College|Institute)\s+of\s+(?:the\s+)?[A-Z][a-zA-Z'\-]*(?:\s+[A-Z][a-zA-Z'\-]*)*|LUMS|NUST|FAST(?:-NUCES)?|UET|GIKI|IBA|MIT|UCLA|NYU|USC|Stanford|Harvard|Oxford|Cambridge|Yale|Princeton)\b"

def redact_demographic_pii(raw_text: str) -> Tuple[str, PIIAuditReport]:
    """
    Strips email, phone, candidate names, gendered pronouns, graduation years,
    and protected demographic data (Gender, Age, Marital, Family, Religion, Location, University).
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
        if any(w in line.lower() for w in ["resume", "curriculum", "cv", "summary", "experience", "profile", "contact"]):
            continue
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

    # 7. Redact Gendered Pronouns & Demographic Gender
    pronouns_found = re.findall(GENDER_PRONOUN_PATTERN, text, re.IGNORECASE)
    if pronouns_found:
        categories.append("Gender Pronouns")
        redaction_count += len(pronouns_found)
        text = re.sub(GENDER_PRONOUN_PATTERN, "[CANDIDATE]", text, flags=re.IGNORECASE)

    gender_found = re.findall(DEMOGRAPHIC_GENDER, text, re.IGNORECASE)
    if gender_found:
        categories.append("Protected Demographic: Gender")
        redaction_count += len(gender_found)
        text = re.sub(DEMOGRAPHIC_GENDER, "[REDACTED_GENDER]", text, flags=re.IGNORECASE)

    # 8. Redact Protected Religion
    religion_found = re.findall(DEMOGRAPHIC_RELIGION, text, re.IGNORECASE)
    if religion_found:
        categories.append("Protected Demographic: Religion")
        redaction_count += len(religion_found)
        text = re.sub(DEMOGRAPHIC_RELIGION, "[REDACTED_RELIGION]", text, flags=re.IGNORECASE)

    # 9. Redact Family & Marital Status (Prioritize multi-word family status e.g. 'single mother' over single marital)
    family_found = re.findall(DEMOGRAPHIC_FAMILY, text, re.IGNORECASE)
    if family_found:
        categories.append("Protected Demographic: Family Status")
        redaction_count += len(family_found)
        text = re.sub(DEMOGRAPHIC_FAMILY, "[REDACTED_FAMILY_STATUS]", text, flags=re.IGNORECASE)

    marital_found = re.findall(DEMOGRAPHIC_MARITAL, text, re.IGNORECASE)
    if marital_found:
        categories.append("Protected Demographic: Marital Status")
        redaction_count += len(marital_found)
        text = re.sub(DEMOGRAPHIC_MARITAL, "[REDACTED_MARITAL_STATUS]", text, flags=re.IGNORECASE)

    # 10. Redact Age & Geographic Location
    age_found = re.findall(DEMOGRAPHIC_AGE, text, re.IGNORECASE)
    if age_found:
        categories.append("Protected Demographic: Age")
        redaction_count += len(age_found)
        text = re.sub(DEMOGRAPHIC_AGE, "[REDACTED_AGE]", text, flags=re.IGNORECASE)

    loc_found = re.findall(DEMOGRAPHIC_LOCATION, text, re.IGNORECASE)
    if loc_found:
        categories.append("Protected Demographic: Location")
        redaction_count += len(loc_found)
        text = re.sub(DEMOGRAPHIC_LOCATION, "[REDACTED_LOCATION]", text, flags=re.IGNORECASE)

    # 11. Redact Educational Institutions (Prevent university pedigree bias)
    inst_found = re.findall(INSTITUTION_PATTERN, text)
    if inst_found:
        categories.append("Protected Institutional Background")
        redaction_count += len(inst_found)
        text = re.sub(INSTITUTION_PATTERN, "[REDACTED_INSTITUTION]", text)

    audit = PIIAuditReport(
        redacted_tokens_count=redaction_count,
        categories_redacted=list(set(categories)),
        is_fully_anonymized=redaction_count > 0
    )

    return text, audit
