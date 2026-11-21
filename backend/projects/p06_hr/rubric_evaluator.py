"""
Project 06: Objective Rubric Evaluator
Evaluates anonymized resumes strictly against competency-based criteria:
- Technical Competencies (0 - 40 pts)
- System Architecture & Engineering (0 - 30 pts)
- Quantified Business Impact (0 - 30 pts)
Demographic information is guaranteed absent prior to evaluation.
"""
import re
from typing import Tuple, List
from .schemas import RubricBreakdown

TECHNICAL_KEYWORDS = [
    "python", "fastapi", "typescript", "react", "pydantic", "sqlite",
    "postgresql", "docker", "llm", "rag", "embeddings", "rest api", "vector",
    "pytorch", "sql"
]

ARCHITECTURE_KEYWORDS = [
    "distributed", "microservices", "redis", "caching", "ci/cd", "event-driven",
    "sse", "websocket", "cloud", "aws", "gcp", "scalability", "concurrency",
    "kubernetes", "platform"
]

IMPACT_PATTERNS = [
    r"\b(?:reduced|decreased|cut|improved|increased|boosted|saved|grew|scaled|supported)\b[\w\s\$]{0,35}?\b(?:\d+%(?:\s+or\s+more)?|\d+x|\$\d+[kmb]?|\d+[kmb]?\s+(?:users|requests|qps|transactions|messages))\b",
    r"\bled\s+(?:a\s+)?team\s+of\s+\d+\b"
]

def evaluate_candidate_rubric(anonymized_cv: str) -> Tuple[RubricBreakdown, str, List[str], List[str], str]:
    """
    Computes objective scores based on technical breadth, architectural complexity, and business metrics.
    """
    text_lower = anonymized_cv.lower()
    strengths = []
    growth_areas = []

    # 1. Technical Competencies (Max 40)
    tech_hits = [k for k in TECHNICAL_KEYWORDS if k in text_lower]
    if tech_hits:
        tech_score = min(40, len(tech_hits) * 8)
        strengths.append(f"Strong tech stack alignment ({', '.join(tech_hits[:4])})")
    else:
        tech_score = 0
        growth_areas.append("Zero explicit mention of core backend / AI frameworks")

    # 2. System Architecture (Max 30)
    arch_hits = [k for k in ARCHITECTURE_KEYWORDS if k in text_lower]
    if arch_hits:
        arch_score = min(30, len(arch_hits) * 7)
        strengths.append(f"Architectural depth in distributed systems & cloud ({', '.join(arch_hits[:3])})")
    else:
        arch_score = 0
        growth_areas.append("Lacks demonstration of distributed scale or architectural ownership")

    # 3. Quantified Impact (Max 30)
    impact_hits = []
    for pat in IMPACT_PATTERNS:
        matches = re.findall(pat, text_lower)
        if matches:
            impact_hits.extend(matches)

    if impact_hits:
        impact_score = min(30, len(impact_hits) * 12)
        strengths.append(f"Quantified engineering accomplishments ({len(impact_hits)} metric outcomes cited)")
    else:
        impact_score = 0
        growth_areas.append("Resume lacks measurable business KPIs and quantified metrics")

    total_score = tech_score + arch_score + impact_score
    rubric = RubricBreakdown(
        technical_skills=tech_score,
        system_architecture=arch_score,
        impact_and_metrics=impact_score,
        total_score=total_score
    )

    if total_score >= 40:
        recommendation = "ADVANCE_TO_INTERVIEW"
        scheduled_slot = "Thursday 2:00 PM EST (Technical Round)"
    elif total_score >= 8:
        recommendation = "HOLD_FOR_REVIEW"
        scheduled_slot = None
    else:
        recommendation = "REJECT"
        scheduled_slot = None

    return rubric, recommendation, strengths, growth_areas, scheduled_slot
