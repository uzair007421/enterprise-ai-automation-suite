"""
Project 02: Legal Document Vector Search Schemas
Strict contracts for dense 128-D vector embeddings, mathematical cosine similarity,
quote citation substring verification, and grounded refusal gates.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class LegalDocumentChunk(BaseModel):
    id: str
    title: str
    reference: str
    clause_type: str
    content: str
    embedding: List[float] = Field(default_factory=list)

class LegalQueryRequest(BaseModel):
    query: str = Field(description="Legal inquiry (e.g. 'What is the liability cap under the MSA?')")
    top_k: int = Field(default=3, ge=1, le=10)
    session_id: Optional[str] = "demo_session"

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
    status: str  # "ANSWERED" | "REFUSAL_GROUNDED"
    confidence_score: float
    dense_cosine_score: float
    lexical_bm25_score: float
    citations: List[CitationVerification]
    execution_time_ms: float
