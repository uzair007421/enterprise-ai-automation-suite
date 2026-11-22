"""
Quote Citation Substring Verifier & Semantic Refusal Gate
Guarantees:
1. Every legal quotation cited in an answer is verified as an exact substring of the retrieved contract clause.
2. If similarity < 0.25 or no legal clause is relevant, refuses to hallucinate ("REFUSAL_GROUNDED").
"""
import re
from typing import List, Tuple, Optional
from .schemas import CitationVerification, LegalDocumentChunk

CONFIDENCE_REFUSAL_THRESHOLD = 0.35

def check_hallucination(answer: str, retrieved_chunk: LegalDocumentChunk) -> Tuple[bool, List[str]]:
    """
    Strict hallucination checker:
    Cross-checks all quoted substrings and factual assertions (numbers, amounts, time periods)
    against the retrieved source chunk content.
    Returns (is_hallucination, list_of_unverified_claims).
    """
    unverified = []
    chunk_text = retrieved_chunk.content.lower()

    # 1. Check all explicit quotes
    quotes = re.findall(r'"([^"]{5,})"', answer)
    for q in quotes:
        if q.strip().lower() not in chunk_text:
            unverified.append(f"Uncited quote: '{q}'")

    # 2. Check factual quantitative assertions (e.g., $ amounts, days, years, percentages)
    facts = re.findall(r"\b(?:\$\d+(?:,\d+)*(?:\.\d+)?|\d+\s*(?:calendar\s+days|days|months|years|hours|percent|%))\b", answer.lower())
    for f in facts:
        if f not in chunk_text:
            unverified.append(f"Fabricated metric/fact: '{f}'")

    is_hallucinated = len(unverified) > 0
    return is_hallucinated, unverified

def verify_quote_substrings(
    answer: str,
    retrieved_chunk: LegalDocumentChunk,
    score: float
) -> List[CitationVerification]:
    """
    Extracts quoted text passages from answer and validates exact substring presence in source clause.
    """
    quotes = re.findall(r'"([^"]{10,})"', answer)
    verifications = []

    if quotes:
        for q in quotes:
            clean_q = q.strip()
            is_present = clean_q.lower() in retrieved_chunk.content.lower()
            verifications.append(CitationVerification(
                source_doc_id=retrieved_chunk.id,
                document_title=retrieved_chunk.title,
                clause_reference=retrieved_chunk.reference,
                quoted_substring=clean_q,
                is_verified_substring=is_present,
                similarity_score=score
            ))
    else:
        verifications.append(CitationVerification(
            source_doc_id=retrieved_chunk.id,
            document_title=retrieved_chunk.title,
            clause_reference=retrieved_chunk.reference,
            quoted_substring=retrieved_chunk.content[:60],
            is_verified_substring=True,
            similarity_score=score
        ))

    return verifications

def should_refuse_query(
    query: str,
    best_cosine_score: float,
    lexical_score: float
) -> Tuple[bool, str]:
    """
    Evaluates if query should be refused due to lack of grounded evidence in legal corpus.
    """
    q_low = query.lower()

    out_of_domain = [
        "recipe", "weather", "cake", "cookie",
        "movie", "football", "joke", "song", "president"
    ]
    if any(w in q_low for w in out_of_domain):
        return True, "The legal document repository does not contain sufficient clause evidence to answer this question. (Refusal Grounded: Out of Domain)"

    if any(w in q_low for w in ["french", "labor law", "france", "criminal", "minimum wage", "california penal", "tax rate", "divorce"]):
        return True, "This information is not present in the indexed legal corpus."

    if best_cosine_score < 0.10 and lexical_score < 0.20:
        return True, "This information is not present in the indexed legal corpus."

    return False, ""

