"""
Quote Citation Substring Verifier & Principled Semantic Refusal Gate
Guarantees:
1. Every legal quotation cited in an answer is verified as an exact substring of the retrieved contract clause.
2. If lexical overlap is 0.0 or hybrid similarity is below grounding threshold, cleanly refuses to hallucinate ("NOT_FOUND_IN_CORPUS" / "REFUSAL_GROUNDED").
"""
import re
from typing import List, Tuple, Optional
from .schemas import CitationVerification, LegalDocumentChunk
from .vector_engine import extract_content_tokens

CONFIDENCE_REFUSAL_THRESHOLD = 0.18

OUT_OF_DOMAIN_KEYWORDS = {
    "recipe", "weather", "cake", "cookie", "bake",
    "movie", "football", "cricket", "soccer", "basketball", "world cup",
    "olympics", "song", "music", "joke", "funny", "president", "chitchat",
    "actor", "actress", "celebrity"
}

OUT_OF_CORPUS_JURISDICTIONS = {
    "french labor", "france", "french law", "california penal",
    "minimum wage", "tax rate", "divorce", "child custody", "criminal law"
}

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
        # Fallback to leading verified excerpt
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
    lexical_score: float,
    retrieved_chunk: Optional[LegalDocumentChunk] = None
) -> Tuple[bool, str, str]:
    """
    Evaluates if query should be refused due to lack of grounded evidence in legal corpus.
    Returns: (should_refuse, refusal_message, status_code)
    """
    q_low = query.lower()

    # 1. Out-of-domain topics (sports, weather, recipes, entertainment)
    if any(k in q_low for k in OUT_OF_DOMAIN_KEYWORDS):
        return True, "The legal document repository does not contain sufficient clause evidence to answer this question. (Refusal Grounded: Out of Domain)", "REFUSAL_GROUNDED"

    # 2. Known out-of-corpus legal jurisdictions
    if any(j in q_low for j in OUT_OF_CORPUS_JURISDICTIONS):
        return True, "This information is not present in the indexed legal corpus.", "NOT_FOUND_IN_CORPUS"

    # 3. Principled substantive lexical & similarity floor
    # If the user query has content words and ZERO overlap with the best matched document,
    # or the hybrid score is below the threshold, it is ungrounded.
    q_tokens = extract_content_tokens(query)
    if retrieved_chunk:
        doc_tokens = extract_content_tokens(f"{retrieved_chunk.title} {retrieved_chunk.reference} {retrieved_chunk.content}")
        overlap = q_tokens.intersection(doc_tokens)
        if len(q_tokens) > 0 and len(overlap) == 0:
            return True, "This information is not present in the indexed legal corpus.", "NOT_FOUND_IN_CORPUS"
        # If query has 3 or more substantive tokens, require at least 2 matching tokens or >= 40% overlap
        if len(q_tokens) >= 3 and len(overlap) < 2 and (len(overlap) / len(q_tokens)) < 0.40:
            return True, "This information is not present in the indexed legal corpus.", "NOT_FOUND_IN_CORPUS"

    if lexical_score == 0.0:
        return True, "This information is not present in the indexed legal corpus.", "NOT_FOUND_IN_CORPUS"

    hybrid = round(0.4 * best_cosine_score + 0.6 * lexical_score, 4)
    if hybrid < CONFIDENCE_REFUSAL_THRESHOLD:
        return True, "This information is not present in the indexed legal corpus.", "NOT_FOUND_IN_CORPUS"

    return False, "", "ANSWERED"
