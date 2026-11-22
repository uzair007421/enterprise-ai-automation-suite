"""
Enterprise Legal Document Corpus & Indexer
Stores high-stakes commercial legal clauses in SQLite table `p02_documents`.
Each clause is embedded into 128-D dense vector space.
"""
import json
import logging
from typing import List, Dict, Any
from core.db import DatabaseSession
from .schemas import LegalDocumentChunk
from .vector_engine import generate_dense_embedding

logger = logging.getLogger("p02_legal.corpus")

DEFAULT_LEGAL_CLAUSES = [
    {
        "id": "DOC-MSA-SEC8.2",
        "title": "Master Services Agreement (Cloud SaaS)",
        "reference": "Section 8.2 (Limitation of Liability)",
        "clause_type": "LIABILITY_CAP",
        "content": (
            "Except for willful misconduct, gross negligence, or indemnification obligations under Section 9, "
            "in no event shall either party's aggregate cumulative liability arising out of or related to this Agreement "
            "exceed the total fees actually paid or payable by Customer in the twelve (12) months preceding the incident. "
            "Neither party shall be liable for any lost profits, loss of business, or indirect, consequential, or punitive damages."
        )
    },
    {
        "id": "DOC-NDA-SEC3.1",
        "title": "Mutual Non-Disclosure Agreement",
        "reference": "Section 3.1 (Term & Confidentiality Period)",
        "clause_type": "CONFIDENTIALITY_TERM",
        "content": (
            "The Receiving Party shall safeguard the Disclosing Party's Confidential Information with at least the degree of care "
            "it uses for its own proprietary data, but no less than reasonable care. "
            "The confidentiality obligations under this Agreement shall survive termination and remain in full force and effect "
            "for a period of five (5) years following initial disclosure, provided that trade secrets shall remain protected in perpetuity."
        )
    },
    {
        "id": "DOC-EMP-SEC6.2",
        "title": "Executive Employment Agreement",
        "reference": "Section 6.2 (Post-Termination Non-Compete & Severance)",
        "clause_type": "RESTRICTIVE_COVENANT",
        "content": (
            "During employment and for twelve (12) months post-termination within a 50-mile geographical radius, "
            "Executive shall not directly or indirectly engage in, manage, operate, or join any competing artificial intelligence enterprise. "
            "In the event of termination without Cause, Employer shall provide six (6) months of base salary severance and health benefits."
        )
    },
    {
        "id": "DOC-LEASE-SEC14",
        "title": "Commercial Real Estate Lease",
        "reference": "Section 14 (Events of Default & Cure Period)",
        "clause_type": "LEASE_DEFAULT",
        "content": (
            "In the event Tenant fails to pay base rent or operating expenses when due, Landlord shall provide written notice of default. "
            "Tenant shall have a mandatory grace period of thirty (30) days from receipt of written notice to cure any monetary or operational default "
            "before Landlord may initiate lease termination or reentry proceedings."
        )
    },
    {
        "id": "DOC-DPA-SEC4.3",
        "title": "Global Data Processing Addendum (GDPR/CCPA)",
        "reference": "Section 4.3 (Personal Data Breach Notification)",
        "clause_type": "DATA_BREACH_SLA",
        "content": (
            "Processor shall notify Controller in writing without undue delay and, in any event, within seventy-two (72) hours "
            "of becoming aware of any confirmed or reasonably suspected Personal Data Breach affecting Controller's customer data. "
            "Such notification shall describe the nature of the security incident, categories of data subjects impacted, and proposed mitigation measures."
        )
    },
    {
        "id": "DOC-REFUND-SEC2.1",
        "title": "Commercial Terms of Sale & Refund Policy",
        "reference": "Section 2.1 (Refund Eligibility & Return Window)",
        "clause_type": "REFUND_WINDOW",
        "content": (
            "Customer may request a full refund within fourteen (14) calendar days of initial purchase date, "
            "provided that no more than ten percent (10%) of the allocated monthly API usage quotas have been consumed. "
            "Refund requests submitted after fourteen (14) calendar days are strictly non-refundable."
        )
    }
]

class LegalCorpusManager:

    def __init__(self):
        self._seed_documents_if_needed()

    def _seed_documents_if_needed(self):
        """Seeds SQLite table `p02_documents` with 128-D embedded legal chunks."""
        db = DatabaseSession()
        try:
            for doc in DEFAULT_LEGAL_CLAUSES:
                existing = db.fetchone("SELECT id FROM p02_documents WHERE id = ?", (doc["id"],))
                if not existing:
                    full_text = f"{doc['title']} {doc['reference']}: {doc['content']}"
                    vec = generate_dense_embedding(full_text)
                    db.execute(
                        """
                        INSERT INTO p02_documents 
                        (id, title, reference, content, vector_json, created_at)
                        VALUES (?, ?, ?, ?, ?, datetime('now'))
                        """,
                        (doc["id"], doc["title"], doc["reference"], doc["content"], json.dumps(vec))
                    )
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to seed legal corpus: {e}")
        finally:
            db.close()

    def get_all_chunks(self) -> List[LegalDocumentChunk]:
        """Loads all indexed chunks with dense embeddings from SQLite."""
        db = DatabaseSession()
        try:
            rows = db.fetchall("SELECT * FROM p02_documents")
            chunks = []
            for r in rows:
                vec = json.loads(r["vector_json"]) if r.get("vector_json") else []
                chunks.append(LegalDocumentChunk(
                    id=r["id"],
                    title=r["title"],
                    reference=r["reference"],
                    clause_type=r["id"].split("-")[1],
                    content=r["content"],
                    embedding=vec
                ))
            return chunks
        finally:
            db.close()

legal_corpus = LegalCorpusManager()
