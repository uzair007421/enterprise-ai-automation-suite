"""
Project 02: Legal Document Vector Search & Grounded RAG Test Suite
Verifies:
- 128-dimensional vector embeddings
- Pure mathematical vector cosine similarity
- Exact substring quote citation verification
- Principled semantic refusal gate on out-of-corpus queries (cricket, out-of-domain)
- Grounded commercial clause retrieval (MSA, Non-compete, Royalty & IP)
- SaaS multi-tenant document isolation and dynamic ingestion
"""
import pytest
import math
from projects.p02_legal.schemas import LegalQueryRequest, LegalDocumentIngestRequest
from projects.p02_legal.vector_engine import (
    generate_dense_embedding,
    compute_cosine_similarity
)
from projects.p02_legal.router import execute_legal_query, list_corpus_documents, ingest_legal_document
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

def test_cricket_world_cup_query_refused():
    """Audit Fix: Non-legal sports question must NOT return an employment contract answer."""
    req = LegalQueryRequest(query="Who won the cricket world cup in 2011?")
    resp = execute_legal_query(req)
    assert resp.status in ("REFUSAL_GROUNDED", "NOT_FOUND_IN_CORPUS")
    assert "Employment Agreement" not in resp.answer
    assert len(resp.citations) == 0

def test_royalty_rate_and_audit_penalty_query():
    """Audit Fix: Royalty query must retrieve the Software IP clause, not the Employment agreement."""
    req = LegalQueryRequest(query="What is the royalty rate and audit penalty?")
    resp = execute_legal_query(req)
    assert resp.status == "ANSWERED"
    assert "Royalty" in resp.answer or "Licensee" in resp.answer
    assert "4.0%" in resp.answer or "four percent" in resp.answer
    assert "15%" in resp.answer
    assert "Employment Agreement" not in resp.answer
    for cit in resp.citations:
        assert cit.is_verified_substring is True

def test_worldwide_noncompete_and_fee_limit_queries():
    """Audit Fix: Non-compete and fee limit queries match correct legal clauses, NOT Refund Policy."""
    req_nc = LegalQueryRequest(query="Is the worldwide non-compete enforceable?")
    resp_nc = execute_legal_query(req_nc)
    assert resp_nc.status == "ANSWERED"
    assert "Employment Agreement" in resp_nc.answer or "Non-Compete" in resp_nc.answer
    assert "Refund Policy" not in resp_nc.answer

    req_fee = LegalQueryRequest(query="Can the company be sued for more than the fees?")
    resp_fee = execute_legal_query(req_fee)
    assert resp_fee.status == "ANSWERED"
    assert "Limitation of Liability" in resp_fee.answer or "Master Services Agreement" in resp_fee.answer
    assert "Refund Policy" not in resp_fee.answer

def test_saas_multi_tenant_partitioning():
    """SaaS Feature: Verify tenant data isolation and custom clause ingestion."""
    # Ingest private clause under tenant_law_firm_a
    ingest_req = LegalDocumentIngestRequest(
        tenant_id="tenant_law_firm_a",
        title="Project Apex Exclusive Joint Venture",
        reference="Section 2.1 (Profit Distribution)",
        content="Profits shall be split eighty percent (80%) to Founder and twenty percent (20%) to Investor.",
        clause_type="PROFIT_SHARING"
    )
    ingest_resp = ingest_legal_document(ingest_req)
    assert ingest_resp.status == "INDEXED_AND_READY"

    # Query from tenant_law_firm_a -> MUST FIND IT
    req_a = LegalQueryRequest(
        tenant_id="tenant_law_firm_a",
        query="What is the profit distribution split for Project Apex?"
    )
    resp_a = execute_legal_query(req_a)
    assert resp_a.status == "ANSWERED"
    assert "Project Apex" in resp_a.answer

    # Query from tenant_law_firm_b -> MUST NOT FIND IT (isolated partition)
    req_b = LegalQueryRequest(
        tenant_id="tenant_law_firm_b",
        query="What is the profit distribution split for Project Apex?"
    )
    resp_b = execute_legal_query(req_b)
    assert resp_b.status == "NOT_FOUND_IN_CORPUS"
