"""
Project 02: Legal Document Vector Search Schemas
SaaS Multi-Tenant Contracts for Grounded Legal RAG, Exact Substring Verification,
and Semantic Refusal Gates.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class LegalDocumentChunk(BaseModel):
    id: str
    tenant_id: str = "default_firm"
    title: str
    reference: str
    clause_type: str
    content: str
    embedding: List[float] = Field(default_factory=list)

class LegalQueryRequest(BaseModel):
    query: str = Field(description="Legal inquiry (e.g. 'What is the liability cap under the MSA?')")
    top_k: int = Field(default=3, ge=1, le=10)
    tenant_id: Optional[str] = Field(default="default_firm", description="SaaS tenant ID for isolated document partitions")
    session_id: Optional[str] = "demo_session"
    live_mode: Optional[bool] = Field(default=False, description="Use live Gemini LLM for natural synthesis if configured")

class CitationVerification(BaseModel):
    source_doc_id: str
    document_title: str
    clause_reference: str
    quoted_substring: str
    is_verified_substring: bool
    similarity_score: float

class LegalRAGResponse(BaseModel):
    query: str
    answer: str
    status: str  # "ANSWERED" | "REFUSAL_GROUNDED" | "NOT_FOUND_IN_CORPUS" | "HALLUCINATION_REJECTED"
    confidence_score: float
    similarity_score: float = 0.0        # canonical field: TF-IDF cosine similarity
    lexical_overlap_score: float = 0.0   # canonical field: lexical overlap ratio
    # DEPRECATED aliases kept for backward API compatibility only.
    # These are NOT BM25 or dense-vector scores. The retrieval engine uses
    # TF-IDF cosine + lexical overlap (rule-based). No dense-vector index exists.
    # Will be removed in v2.0 of this API.
    dense_cosine_score: float = 0.0      # alias for similarity_score
    lexical_bm25_score: float = 0.0     # alias for lexical_overlap_score
    retrieval_method: str = "tfidf_cosine_plus_lexical_overlap"
    engine: str = "rules"  # "rules" | "gemini"
    tenant_id: str = "default_firm"
    citations: List[CitationVerification]
    execution_time_ms: float

class LegalDocumentIngestRequest(BaseModel):
    title: str = Field(description="Document or contract title")
    reference: str = Field(description="Section or clause reference, e.g. 'Section 5.1'")
    clause_type: str = Field(default="GENERAL_COMMERCIAL", description="Classification tag")
    content: str = Field(description="Full text of the legal clause")
    tenant_id: Optional[str] = Field(default="default_firm", description="SaaS tenant partition")

class LegalDocumentIngestResponse(BaseModel):
    id: str
    tenant_id: str
    title: str
    reference: str
    status: str
    indexed_tokens: int
