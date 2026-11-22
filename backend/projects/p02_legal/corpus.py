"""
Enterprise Legal Document Corpus & Indexer
Stores high-stakes commercial legal clauses in table `p02_documents` with multi-tenant SaaS partitioning.
Each clause is embedded into 128-D normalized feature vector space.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from core.db import DatabaseSession
from .schemas import LegalDocumentChunk
from .vector_engine import generate_dense_embedding

logger = logging.getLogger("p02_legal.corpus")

DEFAULT_LEGAL_CLAUSES = [
    {
        "id": "DOC-MSA-SEC8.2",
        "title": "Master Services Agreement (MSA / Cloud SaaS)",
        "reference": "Section 8.2 (Limitation of Liability & Liability Cap)",
        "clause_type": "LIABILITY_CAP",
        "content": (
            "Except for willful misconduct, gross negligence, or indemnification obligations under Section 9, "
            "in no event shall either party's aggregate cumulative liability arising out of or related to this Agreement "
            "exceed the total fees actually paid or payable by Customer in the twelve (12) months preceding the incident. "
            "Neither party may be sued or held liable for any amount exceeding total fees paid, "
            "nor for any lost profits, loss of business, or indirect, consequential, or punitive damages."
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
            "Worldwide non-compete restrictions are void and unenforceable under applicable state employment law. "
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
    },
    {
        "id": "DOC-IP-SEC5.1",
        "title": "Software License, IP Rights & Royalty Agreement",
        "reference": "Section 5.1 (Royalty Rates, Records & Audit Penalties)",
        "clause_type": "IP_ROYALTY_AUDIT",
        "content": (
            "Licensee shall pay a royalty rate of four percent (4.0%) on net sales derived from licensed software products. "
            "Licensor reserves the right to conduct an annual audit of licensee books and accounting records upon thirty (30) days notice. "
            "In the event an underpayment exceeding five percent (5%) is discovered during audit, Licensee shall pay an audit penalty of fifteen percent (15%) "
            "of the total underpaid amount plus all reasonable third-party accounting and legal expenses incurred."
        )
    },
    {
        "id": "DOC-TERM-SEC11.2",
        "title": "Master Services Agreement (Enterprise Cloud)",
        "reference": "Section 11.2 (Termination for Cause & Convenience)",
        "clause_type": "TERMINATION_RIGHTS",
        "content": (
            "Either party may terminate this Agreement for convenience upon sixty (60) days prior written notice to the other party. "
            "Either party may terminate immediately for cause if the other party commits a material breach and fails to cure such breach "
            "within thirty (30) days of receiving formal written notification."
        )
    },
    {
        "id": "DOC-SLA-SEC3.2",
        "title": "Cloud Service Level Agreement (SLA)",
        "reference": "Section 3.2 (Service Availability & Uptime Credits)",
        "clause_type": "SLA_UPTIME_CREDIT",
        "content": (
            "Provider warrants monthly service availability of at least ninety-nine and nine-tenths percent (99.9%), "
            "excluding scheduled maintenance windows. If availability falls below 99.9% in any calendar month, "
            "Customer shall be entitled to a ten percent (10%) service credit applied against future subscription invoices."
        )
    },
    {
        "id": "DOC-DISPUTE-SEC15.1",
        "title": "Commercial Partnership Agreement",
        "reference": "Section 15.1 (Dispute Resolution & Binding Arbitration)",
        "clause_type": "DISPUTE_ARBITRATION",
        "content": (
            "Any dispute, claim, or controversy arising out of or relating to this Agreement shall be resolved through final and binding arbitration "
            "administered by the American Arbitration Association (AAA) under its Commercial Arbitration Rules. "
            "The arbitration seat shall be Wilmington, Delaware, and proceedings shall be conducted in English before a single arbitrator."
        )
    },
    {
        "id": "DOC-FORCE-SEC16.4",
        "title": "Master Commercial Agreement",
        "reference": "Section 16.4 (Force Majeure & Excusable Delay)",
        "clause_type": "FORCE_MAJEURE",
        "content": (
            "Neither party shall be liable for delay or default in performing contractual obligations if caused by an act of God, war, "
            "acts of terrorism, pandemic, embargo, civil disturbance, or government order beyond reasonable control, "
            "provided prompt written notice is delivered within five (5) business days of the triggering event."
        )
    },
    {
        "id": "DOC-NONSOLICIT-SEC7.3",
        "title": "Professional Services Consulting Agreement",
        "reference": "Section 7.3 (Customer & Personnel Non-Solicitation)",
        "clause_type": "NON_SOLICITATION",
        "content": (
            "During the term and for a period of twelve (12) months following contract termination, neither party shall directly or indirectly "
            "solicit, recruit, or hire any employee, independent contractor, or key customer of the other party without prior written consent."
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
            # Ensure tenant_id column exists
            try:
                db.execute("ALTER TABLE p02_documents ADD COLUMN tenant_id TEXT DEFAULT 'default_firm';")
                db.commit()
            except Exception:
                pass

            for doc in DEFAULT_LEGAL_CLAUSES:
                existing = db.fetchone("SELECT id, title, content FROM p02_documents WHERE id = ?", (doc["id"],))
                full_text = f"{doc['title']} {doc['reference']}: {doc['content']}"
                vec = generate_dense_embedding(full_text)
                if not existing:
                    db.execute(
                        """
                        INSERT INTO p02_documents 
                        (id, tenant_id, title, reference, content, vector_json, created_at)
                        VALUES (?, 'default_firm', ?, ?, ?, ?, datetime('now'))
                        """,
                        (doc["id"], doc["title"], doc["reference"], doc["content"], json.dumps(vec))
                    )
                elif existing["title"] != doc["title"] or existing["content"] != doc["content"]:
                    db.execute(
                        """
                        UPDATE p02_documents 
                        SET title = ?, reference = ?, content = ?, vector_json = ?
                        WHERE id = ?
                        """,
                        (doc["title"], doc["reference"], doc["content"], json.dumps(vec), doc["id"])
                    )
            db.commit()
        except Exception as e:
            if "no such table" not in str(e).lower():
                logger.warning(f"Failed to seed legal corpus: {e}")
        finally:
            db.close()

    def get_all_chunks(self, tenant_id: str = "default_firm") -> List[LegalDocumentChunk]:
        """Loads indexed chunks with dense embeddings from DB filtered by tenant partition."""
        db = DatabaseSession()
        try:
            # Multi-tenant partitioning: Return tenant-specific clauses + shared default_firm templates
            if tenant_id and tenant_id != "default_firm":
                rows = db.fetchall(
                    "SELECT * FROM p02_documents WHERE tenant_id = ? OR tenant_id = 'default_firm' ORDER BY tenant_id DESC",
                    (tenant_id,)
                )
            else:
                rows = db.fetchall("SELECT * FROM p02_documents WHERE tenant_id = 'default_firm' OR tenant_id IS NULL")

            chunks = []
            for r in rows:
                vec = json.loads(r["vector_json"]) if r.get("vector_json") else []
                chunks.append(LegalDocumentChunk(
                    id=r["id"],
                    tenant_id=r.get("tenant_id") or "default_firm",
                    title=r["title"],
                    reference=r["reference"],
                    clause_type=r["id"].split("-")[1] if "-" in r["id"] else "GENERAL",
                    content=r["content"],
                    embedding=vec
                ))
            return chunks
        finally:
            db.close()

    def add_chunk(self, tenant_id: str, title: str, reference: str, content: str, clause_type: str = "GENERAL") -> LegalDocumentChunk:
        """Ingests a custom contract chunk into the tenant's private vector corpus."""
        import uuid
        chunk_id = f"DOC-CUSTOM-{uuid.uuid4().hex[:8].upper()}"
        full_text = f"{title} {reference}: {content}"
        vec = generate_dense_embedding(full_text)

        db = DatabaseSession()
        try:
            db.execute(
                """
                INSERT INTO p02_documents (id, tenant_id, title, reference, content, vector_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (chunk_id, tenant_id, title, reference, content, json.dumps(vec))
            )
            db.commit()
        finally:
            db.close()

        return LegalDocumentChunk(
            id=chunk_id,
            tenant_id=tenant_id,
            title=title,
            reference=reference,
            clause_type=clause_type,
            content=content,
            embedding=vec
        )

legal_corpus = LegalCorpusManager()
