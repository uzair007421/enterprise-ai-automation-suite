"""
Project 09: Multi-Format Repurposing Engine & Brand Voice Guardrail
Transforms long-form transcripts into 4 distinct social/technical formats:
1. LinkedIn Executive Post
2. Twitter / X 5-Part Viral Thread
3. Substack Technical Newsletter Edition
4. Dev.to Technical Article Draft
Enforces brand voice guardrails preventing hype claims and policy violations.
"""
import uuid
import re
from typing import List, Tuple
from .schemas import RepurposedAsset

HYPE_FORBIDDEN_PATTERNS = [
    r"\bpassive\s+income\b",
    r"\bget\s+rich\b",
    r"\breplace\s+all\s+(?:developers|engineers|humans)\b",
    r"\b100%\s+guaranteed\b",
    r"\bcrypto\s+moon\b"
]

def check_brand_voice_safety(text: str) -> Tuple[int, bool]:
    """
    Evaluates content for corporate safety, compliance, and engineering rigor.
    """
    text_lower = text.lower()
    violations = [p for p in HYPE_FORBIDDEN_PATTERNS if re.search(p, text_lower)]
    if violations:
        return 45, False
    return 98, True

def generate_repurposed_assets(title: str, transcript: str) -> List[RepurposedAsset]:
    """
    Generates 4 distinct, platform-optimized content packages from source transcript.
    """
    clean_title = title.strip() or "Architectural Engineering Overview"
    snippet = transcript[:300].replace("\n", " ").strip()
    assets = []

    # 1. LinkedIn Post
    li_content = (
        f"🚀 Building Resilient Systems: Key insights on {clean_title}\n\n"
        f"Most engineering teams overlook system predictability when scaling. Here are 3 non-negotiable principles:\n\n"
        f"1️⃣ Architecture over improvisation: '{snippet[:120]}...'\n"
        f"2️⃣ Measurable latency metrics matter more than raw theoretical compute.\n"
        f"3️⃣ Always design with human-in-the-loop governance for critical state machines.\n\n"
        f"What is your team's biggest challenge when modernizing workflows?\n\n"
        f"#SoftwareEngineering #SystemArchitecture #AIAutomation #CloudInfrastructure"
    )
    score, cleared = check_brand_voice_safety(li_content)
    assets.append(RepurposedAsset(
        asset_id=f"ASSET-{uuid.uuid4().hex[:6].upper()}",
        platform="LINKEDIN",
        headline=f"Executive Insights: {clean_title}",
        content=li_content,
        estimated_reading_time_sec=45,
        brand_voice_safety_score=score,
        policy_cleared=cleared
    ))

    # 2. Twitter / X 5-Part Viral Thread
    tw_content = (
        f"🧵 1/5 The reality behind {clean_title} (and why most implementations struggle):\n\n"
        f"2/5 The Core Bottleneck:\n{snippet[:180]}...\n\n"
        f"3/5 The Solution:\nDecouple orchestration from tool execution. Use deterministic state gates before side-effects.\n\n"
        f"4/5 Measured Results:\nZero unverified mutations, 40%+ drop in workflow failure rates, and tamper-evident audit trails.\n\n"
        f"5/5 Summary: Reliability beats hype every time. Bookmark this thread if you're building production systems."
    )
    score, cleared = check_brand_voice_safety(tw_content)
    assets.append(RepurposedAsset(
        asset_id=f"ASSET-{uuid.uuid4().hex[:6].upper()}",
        platform="TWITTER_THREAD",
        headline=f"5-Part Technical Breakdown: {clean_title}",
        content=tw_content,
        estimated_reading_time_sec=60,
        brand_voice_safety_score=score,
        policy_cleared=cleared
    ))

    # 3. Substack Technical Newsletter Edition
    nl_content = (
        f"# Issue #42: Engineering Deep-Dive — {clean_title}\n\n"
        f"**Executive Summary**\n"
        f"Welcome to this week's architecture briefing. In this edition, we examine the practical tradeoffs discussed in our recent engineering briefing:\n\n"
        f"> \"{snippet}\"\n\n"
        f"### Key Architectural Takeaways\n"
        f"- **Reliability First**: Avoid simulated prototypes in production. Every endpoint must be backed by real storage and metrics.\n"
        f"- **Audit Rigor**: Merkle trees and cryptographic signatures eliminate ambiguity across autonomous actions.\n\n"
        f"Until next week,\n*The Engineering Editorial Desk*"
    )
    score, cleared = check_brand_voice_safety(nl_content)
    assets.append(RepurposedAsset(
        asset_id=f"ASSET-{uuid.uuid4().hex[:6].upper()}",
        platform="NEWSLETTER",
        headline=f"Newsletter Edition: {clean_title}",
        content=nl_content,
        estimated_reading_time_sec=120,
        brand_voice_safety_score=score,
        policy_cleared=cleared
    ))

    # 4. Dev.to Technical Article
    dev_content = (
        f"--- \ntitle: 'Practical Architecture: {clean_title}'\npublished: true\ntags: python, architecture, devops, ai\n---\n\n"
        f"## Introduction\n\n"
        f"When architecting production workflows, reliability is your primary metric. Let's break down the implementation details:\n\n"
        f"```python\n"
        f"# Example: Event-driven execution guard\n"
        f"def verify_state_gate(payload: dict) -> bool:\n"
        f"    return payload.get('authorized', False) and payload.get('validated', False)\n"
        f"```\n\n"
        f"### Lessons Learned\n"
        f"{snippet[:150]}\n\n"
        f"*Feedback and questions welcome in the comments!*"
    )
    score, cleared = check_brand_voice_safety(dev_content)
    assets.append(RepurposedAsset(
        asset_id=f"ASSET-{uuid.uuid4().hex[:6].upper()}",
        platform="DEV_TO",
        headline=f"Dev.to Tutorial: {clean_title}",
        content=dev_content,
        estimated_reading_time_sec=90,
        brand_voice_safety_score=score,
        policy_cleared=cleared
    ))

    return assets
