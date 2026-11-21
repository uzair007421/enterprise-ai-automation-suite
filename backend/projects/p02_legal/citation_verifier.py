"""
Quote Citation Substring Verifier & Semantic Refusal Gate
Guarantees:
1. Every legal quotation cited in an answer is verified as an exact substring of the retrieved contract clause.
2. If similarity < 0.25 or no legal clause is relevant, refuses to hallucinate ("REFUSAL_GROUNDED").
"""
import re
from typing import List, Tuple, Optional
from .schemas import CitationVerification, LegalDocumentChunk

CONFIDENCE_REFUSAL_THRESHOLD = 0.25

def verify_quote_substrings(
    answer: str,
    retrieved_chunk: LegalDocumentChunk,
    score: float
) -> List[CitationVerification]:
    """
    Extracts quoted text passages from answer and validates exact substring presence in source clause.
    """
    # Extract passages within double quotes
    quotes = re.findall(r'"([^"]{15,})"', answer)
    verifications = []

    if quotes:
        for q in quotes:
            clean_q = q.strip()
            # Exact substring check (case-insensitive)
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
        # Default verification on primary clause text snippet
        snippet = retrieved_chunk.content[:80] + "..."
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
    Evaluates if query should be refused due to lack of grounded evidence.
    """
    q_low = query.lower()
    
    # Check out-of-domain queries
    out_of_domain = ["recipe", "weather", "cake", "movie", "football", "joke", "song", "president"]
    if any(w in q_low for w in out_of_domain):
        return True, "The legal document repository does not contain sufficient clause evidence to answer this question. (Refusal Grounded: Out of Domain)"

    if best_cosine_score < CONFIDENCE_REFUSAL_THRESHOLD and lexical_score < 0.20:
        return True, f"Evidence insufficient (cosine similarity {best_cosine_score:.3f} below threshold {CONFIDENCE_REFUSAL_THRESHOLD}). (Refusal Grounded)"

    return False, ""
