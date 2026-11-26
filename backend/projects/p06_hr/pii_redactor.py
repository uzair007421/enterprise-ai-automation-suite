"""
Project 06: Demographic PII & Bias Redaction Engine
Performs blind resume screening by stripping personally identifiable information (PII)
and protected demographic markers by category, followed by a mandatory second-pass
residual detector that fails closed if any identifiable token or category survives.
"""
import re
from typing import Tuple, List, Set, Dict
from .schemas import PIIAuditReport

EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
OBFUSCATED_EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+\s*(?:\[at\]|\(at\))\s*[A-Za-z0-9.-]+\s*(?:\[dot\]|\(dot\))\s*[A-Za-z]{2,}\b"
PHONE_PATTERN = r"(?:\+?\d{1,4}[-.\s]*)?(?:\(?\d{2,4}\)?[-.\s]*)?\b\d{3,4}[-.\s]?\d{4}\b"
URL_AND_HANDLE_PATTERN = (
    r"(?:https?://[^\s<>\"')]+|www\.[^\s<>\"')]+|"
    r"\b(?:linkedin\.com/(?:in|pub)|github\.com|gitlab\.com|twitter\.com|x\.com|"
    r"instagram\.com|facebook\.com|tiktok\.com|youtube\.com|medium\.com|t\.me)/[^\s<>\"')]+|"
    r"(?<!\S)@[A-Za-z0-9_.\-]{2,32}\b)"
)

NAME_LABEL_PATTERN = r"(?i)\b(?:Name|Candidate(?:\s+Name)?|Full\s+Name|Applicant(?:\s+Name)?|Resume\s+of|Curriculum\s+Vitae\s+(?:for|of))\s*:\s*([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){1,3})"
HONORIFIC_NAME_PATTERN = r"\b(?:Dr|Mr|Mrs|Ms|Miss|Mx|Prof)\.?\s+([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){1,2})\b"

DOB_PATTERN = (
    r"(?i)\b(?:date\s+of\s+birth|d\.?o\.?b\.?|dob|birth\s*date|birthdate|born(?:\s+(?:in|on))?)\b"
    r"\s*[:\-]?\s*(?:\d{1,2}[/\-\.]\d{1,2}[/\-\.](?:19|20)\d{2}|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2},?\s+(?:19|20)\d{2}|(?:19|20)\d{2})"
)
STANDALONE_DATE_PATTERN = r"\b(?:\d{1,2}[/\-\.](?:0?[1-9]|1[0-2])[/\-\.](?:19[5-9]\d|20[0-2]\d)|(?:19[5-9]\d|20[0-2]\d)[/\-\.](?:0?[1-9]|1[0-2])[/\-\.]\d{1,2})\b"
LABELED_YEAR_PATTERN = r"\b(?:graduated(?:\s+from\s+[^,\n]+?)?|class\s+of|batch\s+of|degree\s+obtained|mba|b\.?sc\.?|m\.?sc\.?|b\.?a\.?|m\.?a\.?|ph\.?d\.?|started\s+in|since)\s*(?:in\s*)?((?:19[5-9]\d|20[0-2]\d))\b"
STANDALONE_YEAR_PATTERN = r"\b(19[5-9]\d|20(?:[01]\d|2[0-6]))\b(?!\s*years?\b)"
DEMOGRAPHIC_AGE = r"\b(?:age\s*[:\-]?\s*\d{1,2}|\d{1,2}\s*(?:y/?o|y\.?o\.?|yrs?\s+old|years?\s+old|years?\s+of\s+age)|(?<=[,\s])(?:1[89]|[2-6]\d)(?=[,\s]))\b"

GENDER_TITLE_AND_PRONOUN_PATTERN = (
    r"\b(?:mr|mrs|ms|miss|mx)\.(?=\s)|\b(?:mr|mrs|ms|miss|mx)\b(?=\s+[A-Za-z])|"
    r"\b(?:he/him|she/her|they/them|he\s+is|she\s+is|his\s+work|her\s+work|"
    r"he|she|him|his|her|hers|himself|herself|"
    r"female|male|woman|man|gentleman|lady|non-binary|transgender|"
    r"gender\s*:\s*\w+|sex\s*:\s*\w+)\b"
)

_DEMONYMS = (
    "afghan|albanian|algerian|american|argentine|argentinian|australian|austrian|"
    "bangladeshi|belgian|brazilian|british|bulgarian|canadian|chilean|chinese|colombian|"
    "croatian|czech|danish|dutch|egyptian|emirati|ethiopian|filipino|finnish|french|"
    "german|ghanaian|greek|hungarian|indian|indonesian|iranian|iraqi|irish|israeli|italian|"
    "jamaican|japanese|jordanian|kenyan|korean|kuwaiti|lebanese|malaysian|mexican|moroccan|"
    "nepalese|nepali|nigerian|norwegian|omani|pakistani|palestinian|peruvian|polish|"
    "portuguese|qatari|romanian|russian|saudi|scottish|serbian|singaporean|south african|"
    "spanish|sri lankan|sudanese|swedish|swiss|syrian|taiwanese|thai|tunisian|turkish|"
    "ukrainian|uruguayan|venezuelan|vietnamese|welsh|yemeni|zimbabwean"
)
NATIONALITY_PATTERN = (
    rf"\b(?:{_DEMONYMS}|"
    r"nationality\s*:\s*[A-Za-z ]+|citizen(?:ship)?|national(?:ity)?|"
    r"passport(?:\s+(?:no|number|#))?|visa\s+status|work\s+permit|green\s+card|"
    r"permanent\s+resident|domicile|cnic)\b"
)

DEMOGRAPHIC_RELIGION = (
    r"\b(?:muslim|islam|islamic|sunni|shia|shiite|ahmadi|ahmadiyya|ismaili|wahhabi|salafi|deobandi|barelvi|"
    r"christian|christianity|catholic|protestant|orthodox|anglican|evangelical|baptist|lutheran|methodist|presbyterian|pentecostal|mormon|"
    r"hindu|hinduism|vaishnava|shaiva|sikh|sikhism|khalsa|buddhist|buddhism|theravada|mahayana|"
    r"jewish|judaism|hasidic|sephardic|ashkenazi|jain|jainism|zoroastrian|parsi|bahai|atheist|agnostic|"
    r"religion\s*:\s*\w+|sect\s*:\s*\w+)\b"
)

DEMOGRAPHIC_FAMILY = (
    r"\b(?:single\s+(?:mother|father|parent)|(?:mother|father|parent)\s+of\s+\w+|\d+\s+(?:kids|children|child|dependents)|"
    r"wife|husband|spouse|fiancee?|married|unmarried|divorced|separated|widow(?:er|ed)?|marital\s+status(?:\s*:\s*\w+)?|"
    r"kids|children|child|sons?|daughters?|mother|father|parents|dependents|pregnant|pregnancy|maternity|paternity)\b|"
    r"\bsingle\b(?!\-)"
)

DEMOGRAPHIC_LOCATION = (
    r"\b(?:lahore|karachi|islamabad|rawalpindi|peshawar|quetta|faisalabad|multan|"
    r"pakistan|india|dubai|uae|london|uk|united kingdom|united states|usa|new york|nyc|"
    r"california|austin|texas|seattle|toronto|canada|berlin|germany|paris|france|"
    r"tokyo|japan|beijing|shanghai|china|sydney|melbourne|australia|riyadh|jeddah)\b"
)

INSTITUTION_PATTERN = (
    r"\b(?:[A-Z][a-zA-Z'\-]*(?:\s+[A-Z][a-zA-Z'\-]*)*\s+(?:University|College|Institute|Academy|School)|"
    r"(?:University|College|Institute)\s+of\s+(?:the\s+)?[A-Z][a-zA-Z'\-]*(?:\s+[A-Z][a-zA-Z'\-]*)*|"
    r"LUMS|NUST|FAST(?:-NUCES)?|UET|GIKI|IBA|MIT|UCLA|NYU|USC|Stanford|Harvard|Oxford|Cambridge|Yale|Princeton)\b"
)

_NON_NAME_HEADER_WORDS = {
    "resume", "curriculum", "vitae", "cv", "summary", "experience", "profile", "contact",
    "engineer", "developer", "architect", "manager", "director", "analyst", "scientist",
    "designer", "consultant", "specialist", "lead", "senior", "junior", "staff", "principal",
    "full", "stack", "backend", "frontend", "software", "platform", "cloud", "systems",
    "skills", "education", "projects", "objective", "work", "history", "accomplishments",
}
_GENERIC_EMAIL_LOCALS = {"info", "contact", "admin", "mail", "support", "jobs", "careers", "resume", "email", "hello", "work"}

# Ordered category rules shared by redactor pass 1 and residual pass 2
_CATEGORY_RULES: List[Tuple[str, str, str, int]] = [
    ("Email Addresses", EMAIL_PATTERN, "[REDACTED_EMAIL]", 0),
    ("Email Addresses", OBFUSCATED_EMAIL_PATTERN, "[REDACTED_EMAIL]", re.IGNORECASE),
    ("URLs & Social Handles", URL_AND_HANDLE_PATTERN, "[REDACTED_URL]", re.IGNORECASE),
    ("Phone Numbers", PHONE_PATTERN, "[REDACTED_PHONE]", 0),
    ("Dates of Birth", DOB_PATTERN, "[REDACTED_DOB]", 0),
    ("Dates of Birth", STANDALONE_DATE_PATTERN, "[REDACTED_DOB]", 0),
    ("Graduation & Calendar Years", LABELED_YEAR_PATTERN, "[DEGREE_COMPLETED - REDACTED_YEAR]", re.IGNORECASE),
    ("Graduation & Calendar Years", STANDALONE_YEAR_PATTERN, "[REDACTED_YEAR]", 0),
    ("Protected Demographic: Age", DEMOGRAPHIC_AGE, "[REDACTED_AGE]", re.IGNORECASE),
    ("Protected Demographic: Nationality", NATIONALITY_PATTERN, "[REDACTED_NATIONALITY]", re.IGNORECASE),
    ("Protected Demographic: Religion", DEMOGRAPHIC_RELIGION, "[REDACTED_RELIGION]", re.IGNORECASE),
    ("Protected Demographic: Family & Marital Status", DEMOGRAPHIC_FAMILY, "[REDACTED_FAMILY_STATUS]", re.IGNORECASE),
    ("Protected Demographic: Gender & Pronouns", GENDER_TITLE_AND_PRONOUN_PATTERN, "[REDACTED_GENDER]", re.IGNORECASE),
    ("Protected Demographic: Location", DEMOGRAPHIC_LOCATION, "[REDACTED_LOCATION]", re.IGNORECASE),
    ("Protected Institutional Background", INSTITUTION_PATTERN, "[REDACTED_INSTITUTION]", 0),
]


def _extract_identifiers(raw_text: str) -> Tuple[Set[str], Set[str], Set[str]]:
    """Extracts candidate full names/tokens, email local parts, and phone digit cores prior to redaction."""
    detected_names: Set[str] = set()
    for m in re.findall(NAME_LABEL_PATTERN, raw_text):
        detected_names.add(m.strip())
    for m in re.findall(HONORIFIC_NAME_PATTERN, raw_text):
        detected_names.add(m.strip())

    non_empty_lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    for line in non_empty_lines[:3]:
        words_lower = set(re.findall(r"[a-z]+", line.lower()))
        if words_lower & _NON_NAME_HEADER_WORDS:
            continue
        m_name = re.match(r"^(?:(?:Dr|Mr|Ms|Mrs|Mx|Prof)\.?\s+)?([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){1,3})$", line)
        if m_name:
            detected_names.add(m_name.group(1))
            detected_names.add(line)

    email_tokens: Set[str] = set()
    for em in re.findall(EMAIL_PATTERN, raw_text):
        local = em.split("@", 1)[0]
        for tok in re.split(r"[._+\-]+", local):
            if len(tok) >= 4 and tok.lower() not in _GENERIC_EMAIL_LOCALS and tok.isalpha():
                email_tokens.add(tok)

    phone_digits: Set[str] = set()
    for ph in re.findall(PHONE_PATTERN, raw_text):
        digits = re.sub(r"\D", "", ph)
        if len(digits) >= 7:
            phone_digits.add(digits[-7:])

    return detected_names, email_tokens, phone_digits


def detect_residual_pii(
    redacted_text: str,
    detected_names: Set[str],
    email_tokens: Set[str],
    phone_digits: Set[str],
) -> List[str]:
    """Second-pass residual scanner. Returns any PII/demographic categories still present."""
    residuals: List[str] = []

    for cat_name, pattern, _, flags in _CATEGORY_RULES:
        if re.search(pattern, redacted_text, flags=flags):
            if cat_name not in residuals:
                residuals.append(cat_name)

    for full_name in detected_names:
        if re.search(rf"\b{re.escape(full_name)}\b", redacted_text, flags=re.IGNORECASE):
            if "Candidate Full Name" not in residuals:
                residuals.append("Candidate Full Name")
        for tok in full_name.split():
            if len(tok) >= 3 and tok.lower() not in _NON_NAME_HEADER_WORDS:
                if re.search(rf"\b{re.escape(tok)}\b", redacted_text, flags=re.IGNORECASE):
                    if "Candidate Name Token" not in residuals:
                        residuals.append("Candidate Name Token")

    for tok in email_tokens:
        if re.search(rf"\b{re.escape(tok)}\b", redacted_text, flags=re.IGNORECASE):
            if "Email Identifier Token" not in residuals:
                residuals.append("Email Identifier Token")

    text_digits = re.sub(r"\D", "", redacted_text)
    for d in phone_digits:
        if d in text_digits:
            if "Phone Digits" not in residuals:
                residuals.append("Phone Digits")

    return residuals


def redact_demographic_pii(raw_text: str) -> Tuple[str, PIIAuditReport]:
    """
    Redacts PII & protected demographic categories and runs a mandatory second-pass
    residual verification scan so `is_fully_anonymized` is never hardcoded.
    """
    text = raw_text
    categories: List[str] = []
    redaction_count = 0

    detected_names, email_tokens, phone_digits = _extract_identifiers(raw_text)

    # Pass 1a: Emails, URLs, Phones first (so handles/URLs containing names are caught before name split)
    for cat_name, pattern, replacement, flags in _CATEGORY_RULES[:4]:
        matches = re.findall(pattern, text, flags=flags)
        if matches:
            categories.append(cat_name)
            redaction_count += len(matches)
            text = re.sub(pattern, replacement, text, flags=flags)

    # Pass 1b: Candidate names (full names, then individual non-tech/non-role tokens)
    for name in sorted(detected_names, key=len, reverse=True):
        pat = rf"\b{re.escape(name)}\b"
        matches = re.findall(pat, text, flags=re.IGNORECASE)
        if matches:
            categories.append("Candidate Full Name")
            redaction_count += len(matches)
            text = re.sub(pat, "[REDACTED_NAME] [CANDIDATE_ANONYMOUS_PROFILE]", text, flags=re.IGNORECASE)

    for full_name in detected_names:
        for tok in full_name.split():
            if len(tok) >= 3 and tok.lower() not in _NON_NAME_HEADER_WORDS:
                pat = rf"\b{re.escape(tok)}\b"
                matches = re.findall(pat, text, flags=re.IGNORECASE)
                if matches:
                    categories.append("Candidate Name Token")
                    redaction_count += len(matches)
                    text = re.sub(pat, "[REDACTED_NAME]", text, flags=re.IGNORECASE)

    for tok in email_tokens:
        pat = rf"\b{re.escape(tok)}\b"
        matches = re.findall(pat, text, flags=re.IGNORECASE)
        if matches:
            categories.append("Email Identifier Token")
            redaction_count += len(matches)
            text = re.sub(pat, "[REDACTED_NAME]", text, flags=re.IGNORECASE)

    text = re.sub(
        r"(?i)\b(Name|Candidate(?:\s+Name)?|Full\s+Name|Applicant(?:\s+Name)?)\s*:\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+",
        r"\1: [REDACTED_NAME]",
        text,
    )

    # Pass 1c: Remaining demographic, DOB, year, location & institution categories
    for cat_name, pattern, replacement, flags in _CATEGORY_RULES[4:]:
        matches = re.findall(pattern, text, flags=flags)
        if matches:
            categories.append(cat_name)
            redaction_count += len(matches)
            text = re.sub(pattern, replacement, text, flags=flags)

    # Pass 2: Mandatory residual verification scan (fail-closed source of truth)
    residual_categories = detect_residual_pii(text, detected_names, email_tokens, phone_digits)

    audit = PIIAuditReport(
        redacted_tokens_count=redaction_count,
        categories_redacted=sorted(set(categories)),
        is_fully_anonymized=(len(residual_categories) == 0),
        residual_categories=residual_categories,
    )
    return text, audit
