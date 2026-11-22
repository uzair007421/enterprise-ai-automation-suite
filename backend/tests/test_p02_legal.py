"""
Project 02: Legal Document Vector Search & Cosine RAG Test Suite
Verifies:
- 128-dimensional vector embeddings
- Pure mathematical vector cosine similarity
- Exact substring quote citation verification
- Strict semantic refusal gate on out-of-corpus queries
"""
import pytest
import math
from projects.p02_legal.schemas import LegalQueryRequest
from projects.p02_legal.vector_engine import (
    generate_dense_embedding,
    compute_cosine_similarity
)
from projects.p02_legal.router import execute_legal_query, list_corpus_documents
from projects.p02_legal.corpus import legal_corpus

def test_dense_vector_dimensions_and_unit_norm():
    """Verify 128-D vector generation with Euclidean unit length normalization."""
    vec = generate_dense_embedding("Limitation of liability under SaaS agreement.")
    assert len(vec) == 128
    # L2 norm must equal 1.0 (+/- tolerance)
    l2_norm = math.sqrt(sum(x * x for x in vec))
    assert abs(l2_norm - 1.0) < 0.01

def test_pure_mathematical_cosine_similarity():
    """Verify true mathematical vector cosine similarity properties."""
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]

    # Identical vectors -> cos = 1.0
    sim_identical = compute_cosine_similarity(vec_a, vec_b)
    assert sim_identical == 1.0

    # Orthogonal vectors -> cos = 0.0
    sim_orthogonal = compute_cosine_similarity(vec_a, vec_c)
    assert sim_orthogonal == 0.0

def test_quote_citation_exact_substring_verification():
    """Audit Fix: Verify all cited quotes in legal answer are exact substrings of source contracts."""
    req = LegalQueryRequest(query="What is the liability cap under the MSA?")
    resp = execute_legal_query(req)
    assert resp.status == "ANSWERED"
    assert resp.dense_cosine_score > 0.0
    assert len(resp.citations) >= 1

    # Every single citation MUST be a mathematically verified substring
    for cit in resp.citations:
        assert cit.is_verified_substring is True, f"Unverified citation hallucinated: {cit.quoted_substring}"

def test_data_breach_sla_query_retrieval():
    """Verify GDPR DPA 72-hour breach notification clause retrieval and citation."""
    req = LegalQueryRequest(query="How quickly must we report a personal data breach under GDPR DPA?")
    resp = execute_legal_query(req)
    assert resp.status == "ANSWERED"
    assert "72" in resp.answer or "seventy-two" in resp.answer
    assert any(c.is_verified_substring for c in resp.citations)

def test_semantic_refusal_gate_on_ungrounded_query():
    """Audit Fix: Completely unrelated inquiries must trigger REFUSAL_GROUNDED."""
    req = LegalQueryRequest(query="What is the secret recipe for baking chocolate cookies?")
    resp = execute_legal_query(req)
    assert resp.status == "REFUSAL_GROUNDED"
    assert "Refusal Grounded" in resp.answer
    assert len(resp.citations) == 0
