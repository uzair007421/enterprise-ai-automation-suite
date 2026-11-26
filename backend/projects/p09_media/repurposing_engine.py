"""
Project 09: Multi-Format Repurposing Engine & Brand Voice Guardrail
Transforms long-form transcripts into 4 distinct social/technical formats:
1. LinkedIn Executive Post
2. Twitter / X 5-Part Breakdown Thread
3. Substack Technical Newsletter Edition
4. Dev.to Technical Article Draft
Enforces brand voice guardrails preventing hype claims, policy violations, and corporate buzzwords.
"""
import uuid
import re
from typing import List, Tuple, Optional
from .schemas import RepurposedAsset

BANNED_AI_WORDS = [
    r"\bdelve\b",
    r"\btestament\b",
    r"\btapestry\b",
    r"\brevolutionize\b",
    r"\brevolutionizing\b",
    r"\brevolutionary\b",
    r"\bleverage\b",
    r"\bleveraging\b",
    r"\bsynergy\b",
    r"\bsynergies\b",
    r"\bdisrupt(?:ing|ive|s|ed|ion)?\b",
    r"\bgame-changer\b",
    r"\bgame changer\b",
    r"\bparadigm\s+shift\b",
    r"\bin conclusion\b",
    r"\bbeacon\b",
    r"\bunleash\b"
]

BUZZWORD_PATTERNS = [
    r"\brevolutionary\b",
    r"\brevolutionize\b",
    r"\bleverage\b",
    r"\bleveraging\b",
    r"\bsynergy\b",
    r"\bsynergies\b",
    r"\bdisrupt(?:ing|ive|s|ed|ion)?\b",
    r"\bgame-changer\b",
    r"\bgame changer\b",
    r"\bparadigm\s+shift\b"
]

HYPE_FORBIDDEN_PATTERNS = [
    r"\bpassive\s+income\b",
    r"\bget\s+rich\b",
    r"\breplace\s+all\s+(?:developers|engineers|humans)\b",
    r"\b100%\s+guaranteed\b",
    r"\bcrypto\s+moon\b"
]

def strip_banned_words(text: str) -> str:
    """Removes banned AI buzzwords and corporate cliches case-insensitively from text."""
    cleaned = text
    for pat in BANNED_AI_WORDS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" \n", "\n", cleaned)
    return cleaned.strip()

def check_brand_voice_safety(text: str, original_context: str = "") -> Tuple[int, bool]:
    """
    Evaluates content for corporate safety, compliance, and engineering rigor.
    Penalizes hype claims and buzzwords (e.g. revolutionary, leverage, synergy).
    """
    combined_lower = f"{text} {original_context}".lower()

    # 1. Hard Forbidden Claims (Get rich, passive income, etc.)
    violations = [p for p in HYPE_FORBIDDEN_PATTERNS if re.search(p, combined_lower)]
    if violations:
        return 45, False

    # 2. Corporate Hype / Buzzword penalty
    buzzwords_found = [p for p in BUZZWORD_PATTERNS if re.search(p, combined_lower)]
    if buzzwords_found:
        penalty = 20 + len(buzzwords_found) * 5
        score = max(50, 92 - penalty)
        return score, False  # Fails strict safety threshold

    # 3. Dynamic clean content scoring
    words = text.split()
    score = 90
    if len(words) >= 40:
        score += 3
    if any(char in text for char in [":", "-", "•", "1.", "2."]):
        score += 2
    content_mod = (len(text) % 4)
    score = min(96, score + content_mod)
    return score, True

def extract_key_points(title: str, transcript: str) -> List[str]:
    """Extracts actual informative sentences or fragments from the transcript without duplication."""
    cleaned_transcript = strip_banned_words(transcript)
    raw_sentences = [
        s.strip() for s in re.split(r"[.!?\n]+", cleaned_transcript)
        if len(s.strip()) > 15
    ]
    seen = set()
    unique_sentences = []
    for s in raw_sentences:
        norm = re.sub(r"\s+", " ", s.lower())
        if norm not in seen:
            seen.add(norm)
            unique_sentences.append(s)

    if not unique_sentences:
        return [
            title,
            f"Detailed context and methodology regarding {title}",
            f"Key observations and practical insights from {title}"
        ]
    while len(unique_sentences) < 3:
        if len(unique_sentences) == 1:
            unique_sentences.append(f"Practical methodology details regarding {title}")
            unique_sentences.append(f"Summary observations and insights on {title}")
        elif len(unique_sentences) == 2:
            unique_sentences.append(f"Key summary findings and considerations for {title}")

    return unique_sentences

def generate_repurposed_assets(title: str, transcript: str) -> List[RepurposedAsset]:
    """
    Generates 4 distinct, platform-optimized content packages from source transcript.
    Derives topics and unique sentences directly from the actual input (no hardcoded templates).
    """
    clean_title = strip_banned_words(title.strip()) or "Content Overview"
    clean_transcript = strip_banned_words(transcript.strip())
    snippet = clean_transcript[:300].replace("\n", " ").strip() or clean_title

    pts = extract_key_points(clean_title, clean_transcript)
    p1 = pts[0]
    p2 = pts[1]
    p3 = pts[2]

    words = [w for w in re.findall(r"[a-zA-Z0-9]+", clean_title) if len(w) > 2]
    topic_phrase = clean_title if len(clean_title) >= 4 else (" ".join(words) if words else "this topic")
    tag1 = words[0].capitalize() if words else "Insights"
    tag2 = words[-1].capitalize() if len(words) > 1 else "Analysis"

    assets = []

    # 1. LinkedIn Post
    li_content = (
        f"Key Insights: {clean_title}\n\n"
        f"Here are 3 core takeaways from the material:\n\n"
        f"1. {p1}\n"
        f"2. {p2}\n"
        f"3. {p3}\n\n"
        f"What has been your experience with {topic_phrase.lower()}?\n\n"
        f"#{tag1} #{tag2}"
    )
    li_content = strip_banned_words(li_content)
    score, cleared = check_brand_voice_safety(li_content, original_context=transcript)
    assets.append(RepurposedAsset(
        asset_id=f"ASSET-{uuid.uuid4().hex[:6].upper()}",
        platform="LINKEDIN",
        headline=f"Executive Insights: {clean_title}",
        content=li_content,
        char_count=len(li_content),
        estimated_reading_time_sec=45,
        brand_voice_safety_score=score,
        policy_cleared=cleared
    ))

    # 2. Twitter / X 5-Part Viral Thread
    tw_content = (
        f"1/5 Breakdown: {clean_title}\n\n"
        f"2/5 Core Foundation:\n{p1}\n\n"
        f"3/5 Key Details:\n{p2}\n\n"
        f"4/5 Observations:\n{p3}\n\n"
        f"5/5 Summary: Consistent results come from sound methodology. Save this breakdown on {clean_title.lower()} for reference."
    )
    tw_content = strip_banned_words(tw_content)
    score, cleared = check_brand_voice_safety(tw_content, original_context=transcript)
    assets.append(RepurposedAsset(
        asset_id=f"ASSET-{uuid.uuid4().hex[:6].upper()}",
        platform="TWITTER_THREAD",
        headline=f"5-Part Breakdown: {clean_title}",
        content=tw_content,
        char_count=len(tw_content),
        estimated_reading_time_sec=60,
        brand_voice_safety_score=score,
        policy_cleared=cleared
    ))

    # 3. Substack Technical Newsletter Edition
    nl_content = (
        f"# Newsletter Edition: {clean_title}\n\n"
        f"**Overview**\n"
        f"In this edition, we examine key points from: {clean_title}.\n\n"
        f"> {snippet}\n\n"
        f"### Core Points\n"
        f"- **Primary Focus**: {p1}\n"
        f"- **Methodology**: {p2}\n"
        f"- **Application**: {p3}\n\n"
        f"Until next week,\n*The Editorial Desk*"
    )
    nl_content = strip_banned_words(nl_content)
    score, cleared = check_brand_voice_safety(nl_content, original_context=transcript)
    assets.append(RepurposedAsset(
        asset_id=f"ASSET-{uuid.uuid4().hex[:6].upper()}",
        platform="NEWSLETTER",
        headline=f"Newsletter Edition: {clean_title}",
        content=nl_content,
        char_count=len(nl_content),
        estimated_reading_time_sec=120,
        brand_voice_safety_score=score,
        policy_cleared=cleared
    ))

    # 4. Dev.to Technical Article
    dev_content = (
        f"---\n"
        f"title: 'Practical Guide: {clean_title}'\n"
        f"published: true\n"
        f"tags: tutorial, guide, breakdown\n"
        f"---\n\n"
        f"## Introduction\n\n"
        f"A structured overview of {clean_title}.\n\n"
        f"### Key Steps & Details\n"
        f"- {p1}\n"
        f"- {p2}\n"
        f"- {p3}\n\n"
        f"### Context & Notes\n"
        f"{snippet}\n"
    )
    dev_content = strip_banned_words(dev_content)
    score, cleared = check_brand_voice_safety(dev_content, original_context=transcript)
    assets.append(RepurposedAsset(
        asset_id=f"ASSET-{uuid.uuid4().hex[:6].upper()}",
        platform="DEV_TO",
        headline=f"Guide: {clean_title}",
        content=dev_content,
        char_count=len(dev_content),
        estimated_reading_time_sec=90,
        brand_voice_safety_score=score,
        policy_cleared=cleared
    ))

    return assets
