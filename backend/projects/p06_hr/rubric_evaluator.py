"""
Project 06: Objective Rubric Evaluator
Evaluates anonymized resumes strictly against competency-based criteria:
- Technical Competencies (0 - 40 pts)
- System Architecture & Engineering (0 - 30 pts)
- Quantified Business Impact (0 - 30 pts)
Compares candidate skills to role-specific requirements.
"""
import re
from typing import Tuple, List, Optional
from .schemas import RubricBreakdown

ROLE_SKILL_REQUIREMENTS = {
    "frontend": {
        "required": ["react", "typescript", "javascript", "css", "html", "tailwind", "next.js", "vue", "frontend", "ui"],
        "architecture": ["spa", "web performance", "dom", "browser", "state management", "responsive design", "ui/ux"]
    },
    "backend": {
        "required": ["python", "fastapi", "django", "postgresql", "sql", "sqlite", "docker", "pydantic", "rest api"],
        "architecture": ["distributed", "microservices", "redis", "caching", "ci/cd", "concurrency", "scalability", "cloud", "aws"]
    },
    "ml_ai": {
        "required": ["python", "pytorch", "tensorflow", "machine learning", "ml", "llm", "rag", "embeddings", "vector"],
        "architecture": ["distributed", "gpu", "inference", "training", "pipeline", "model serving", "cloud"]
    }
}

IMPACT_PATTERNS = [
    r"\b(?:reduced|decreased|cut|improved|increased|boosted|saved|grew|scaled|supported)\b[\w\s\$]{0,35}?\b(?:\d+%(?:\s+or\s+more)?|\d+x|\$\d+[kmb]?|\d+[kmb]?\s+(?:users|requests|qps|transactions|messages))\b",
    r"\bled\s+(?:a\s+)?team\s+of\s+\d+\b"
]

def evaluate_candidate_rubric(anonymized_cv: str, job_role: Optional[str] = None) -> Tuple[RubricBreakdown, str, List[str], List[str], Optional[str]]:
    """
    Computes objective scores comparing candidate skills to specific job requirements.
    """
    text_lower = anonymized_cv.lower()
    role_lower = (job_role or "Senior Full-Stack / AI Engineer").lower()
    strengths = []
    growth_areas = []

    # 1. Check for Role Mismatch (e.g. Python/ML candidate on Frontend role)
    is_frontend_role = "frontend" in role_lower or "front-end" in role_lower or "ui" in role_lower

    if is_frontend_role:
        req_frontend = ROLE_SKILL_REQUIREMENTS["frontend"]["required"]
        frontend_matches = [k for k in req_frontend if k in text_lower]
        has_ml_python = any(k in text_lower for k in ["python", "machine learning", "ml", "pytorch", "tensorflow"])

        if len(frontend_matches) == 0:
            # Complete mismatch: Python/ML on Frontend role
            tech_score = 0
            arch_score = 15 if any(k in text_lower for k in ["distributed", "cloud", "aws", "gcp", "architecture"]) else 5
            impact_matches = [pat for pat in IMPACT_PATTERNS if re.findall(pat, text_lower)]
            impact_score = min(15, len(impact_matches) * 8)
            total_score = tech_score + arch_score + impact_score

            if has_ml_python:
                strengths.append("Strong background in Python and Machine Learning engineering")
            growth_areas.append("Role requires React/CSS/TypeScript; candidate background is focused on Python/ML backend")

            rubric = RubricBreakdown(
                technical_skills=tech_score,
                system_architecture=arch_score,
                impact_and_metrics=impact_score,
                total_score=total_score
            )
            recommendation = "REJECT" if total_score < 25 else "HOLD_FOR_REVIEW"
            return rubric, recommendation, strengths, growth_areas, None

    # 2. Select Keywords Based on Role
    if is_frontend_role:
        tech_keywords = ["react", "typescript", "javascript", "css", "html", "tailwind", "next.js", "vue", "redux", "frontend", "ui"]
        arch_keywords = ["responsive design", "web performance", "dom", "browser", "spa", "ui/ux", "components", "accessibility"]
    else:
        tech_keywords = [
            "python", "fastapi", "typescript", "react", "pydantic", "sqlite",
            "postgresql", "docker", "llm", "rag", "embeddings", "rest api", "vector",
            "pytorch", "sql"
        ]
        arch_keywords = [
            "distributed", "microservices", "redis", "caching", "ci/cd", "event-driven",
            "sse", "websocket", "cloud", "aws", "gcp", "scalability", "concurrency",
            "kubernetes", "platform"
        ]
    tech_hits = [k for k in tech_keywords if k in text_lower]
    if tech_hits:
        tech_score = min(40, len(tech_hits) * 8)
        strengths.append(f"Strong tech stack alignment ({', '.join(tech_hits[:4])})")
    else:
        tech_score = 0
        growth_areas.append("Zero explicit mention of required core technologies")

    arch_hits = [k for k in arch_keywords if k in text_lower]
    if arch_hits:
        arch_score = min(30, len(arch_hits) * 7)
        strengths.append(f"Architectural depth in distributed systems & cloud ({', '.join(arch_hits[:3])})")
    else:
        arch_score = 0
        growth_areas.append("Lacks demonstration of distributed scale or architectural ownership")

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
    elif total_score >= 15:
        recommendation = "HOLD_FOR_REVIEW"
        scheduled_slot = None
    else:
        recommendation = "REJECT"
        scheduled_slot = None

    return rubric, recommendation, strengths, growth_areas, scheduled_slot
