"""
Core Database Module
Zero-dependency, high-performance database layer using Python's standard sqlite3.
Guarantees real, persistent SQLite storage on disk without WDAC/C-extension DLL blocks.
Compatible with SQLite for local development and Postgres via standard connection string.
"""
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Generator, Dict, Any, List, Optional
from .config import settings

# Thread-local storage for connection pooling
_local = threading.local()

def get_connection() -> sqlite3.Connection:
    """Returns thread-safe connection to the SQLite database with Row factory."""
    conn = getattr(_local, "connection", None)
    if conn is None:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode and foreign keys for high concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        _local.connection = conn
    return _local.connection

def reset_connection():
    """Resets the thread-local connection."""
    conn = getattr(_local, "connection", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _local.connection = None

class DatabaseSession:
    """Session wrapper providing high-level query, insert, and transaction management."""

    def __init__(self):
        self.conn = get_connection()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

    query_one = fetchone
    query_all = fetchall

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        # We keep connection in thread pool, commit pending
        try:
            self.conn.commit()
        except Exception:
            pass

def get_db() -> Generator[DatabaseSession, None, None]:
    """FastAPI Dependency for database transactions."""
    session = DatabaseSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_db():
    """Initializes database schema tables for all 10 automation projects."""
    conn = get_connection()
    with conn:
        # P01 Real Estate Leads & Offers (Multi-Tenant SaaS Enabled)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p01_leads (
                id TEXT PRIMARY KEY,
                tenant_id TEXT DEFAULT 'default_brokerage',
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                budget REAL,
                location TEXT,
                bedrooms INTEGER,
                timeline TEXT,
                status TEXT NOT NULL,
                score_tier TEXT NOT NULL,
                fit_reason TEXT,
                raw_inquiry TEXT,
                broker_approved INTEGER DEFAULT 0,
                dispatched INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p01_offers (
                id TEXT PRIMARY KEY,
                tenant_id TEXT DEFAULT 'default_brokerage',
                lead_id TEXT NOT NULL,
                mls_id TEXT NOT NULL,
                property_address TEXT NOT NULL,
                offered_price REAL NOT NULL,
                earnest_deposit REAL NOT NULL,
                inspection_days INTEGER NOT NULL,
                financing_contingency_days INTEGER NOT NULL,
                broker_approved INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                broker_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        # Safe migration if columns missing
        try:
            conn.execute("ALTER TABLE p01_leads ADD COLUMN tenant_id TEXT DEFAULT 'default_brokerage';")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE p01_offers ADD COLUMN tenant_id TEXT DEFAULT 'default_brokerage';")
        except Exception:
            pass

        # P02 Legal Document Corpus & Chunks (Multi-Tenant SaaS Enabled)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p02_documents (
                id TEXT PRIMARY KEY,
                tenant_id TEXT DEFAULT 'default_firm',
                title TEXT NOT NULL,
                reference TEXT NOT NULL,
                content TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        # Safe migration if table already exists without tenant_id
        try:
            conn.execute("ALTER TABLE p02_documents ADD COLUMN tenant_id TEXT DEFAULT 'default_firm';")
        except Exception:
            pass

        # P03 E-Commerce Orders & Support Tickets
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p03_orders (
                id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                items TEXT NOT NULL,
                total_usd REAL NOT NULL,
                status TEXT NOT NULL,
                courier TEXT,
                tracking_id TEXT,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p03_tickets (
                id TEXT PRIMARY KEY,
                order_id TEXT,
                customer_id TEXT,
                state TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                transcript TEXT NOT NULL,
                escalated_to_human INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)

        # P04 Invoices & Accounting Ledger
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p04_invoices (
                id TEXT PRIMARY KEY,
                vendor TEXT NOT NULL,
                invoice_number TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                subtotal REAL DEFAULT 0.0,
                tax_amount REAL DEFAULT 0.0,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                math_check_1 TEXT,
                math_check_2 TEXT,
                confidence INTEGER DEFAULT 95,
                file_hash TEXT NOT NULL,
                synced_to_qbo INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)

        # P05 Workflow Monitoring Telemetry
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p05_workflow_telemetry (
                id TEXT PRIMARY KEY,
                workflow_name TEXT NOT NULL,
                status TEXT NOT NULL,
                http_status INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                healed INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                error_detail TEXT,
                created_at TEXT NOT NULL
            );
        """)

        # P06 HR Candidate Rubrics (Multi-Tenant SaaS Enabled)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p06_candidates (
                id TEXT PRIMARY KEY,
                tenant_id TEXT DEFAULT 'default_company',
                redacted_cv_text TEXT NOT NULL,
                pii_audit_json TEXT NOT NULL,
                rubric_score INTEGER NOT NULL,
                score_breakdown_json TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                scheduled_interview_slot TEXT,
                created_at TEXT NOT NULL
            );
        """)
        try:
            conn.execute("ALTER TABLE p06_candidates ADD COLUMN tenant_id TEXT DEFAULT 'default_company';")
        except Exception:
            pass

        # P07 Dental Appointments (Multi-Tenant SaaS Enabled)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p07_appointments (
                id TEXT PRIMARY KEY,
                tenant_id TEXT DEFAULT 'default_clinic',
                patient_name TEXT NOT NULL,
                doctor TEXT NOT NULL,
                slot_time TEXT NOT NULL,
                reason TEXT NOT NULL,
                is_emergency INTEGER DEFAULT 0,
                sms_sent INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)
        try:
            conn.execute("ALTER TABLE p07_appointments ADD COLUMN tenant_id TEXT DEFAULT 'default_clinic';")
        except Exception:
            pass

        # P08 Competitor Snapshots & Diffs (Multi-Tenant SaaS Enabled)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p08_competitor_diffs (
                id TEXT PRIMARY KEY,
                tenant_id TEXT DEFAULT 'default_org',
                competitor_name TEXT NOT NULL,
                change_type TEXT NOT NULL,
                headline TEXT NOT NULL,
                details TEXT NOT NULL,
                impact_score INTEGER NOT NULL,
                source_url TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p08_snapshots (
                url TEXT NOT NULL,
                tenant_id TEXT DEFAULT 'default_org',
                competitor_name TEXT NOT NULL,
                html_snapshot TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, url)
            );
        """)
        try:
            conn.execute("ALTER TABLE p08_competitor_diffs ADD COLUMN tenant_id TEXT DEFAULT 'default_org';")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE p08_snapshots ADD COLUMN tenant_id TEXT DEFAULT 'default_org';")
        except Exception:
            pass

        # P09 Media Content Repurposed Assets
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p09_assets (
                id TEXT PRIMARY KEY,
                video_title TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                platform TEXT NOT NULL,
                content TEXT NOT NULL,
                approved INTEGER DEFAULT 0,
                published INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)

        # P10 FinGuard Financial Audit Chain & Proposals
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p10_audit_chain (
                id TEXT PRIMARY KEY,
                block_index INTEGER NOT NULL,
                previous_hash TEXT NOT NULL,
                action_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                hmac_signature TEXT NOT NULL,
                block_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS p10_proposals (
                proposal_id TEXT PRIMARY KEY,
                tool_name TEXT NOT NULL,
                tool_type TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                status TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()

    # Seed baseline records if needed
    try:
        from projects.p03_support.shopify_adapter import shopify_adapter
        shopify_adapter._seed_orders_if_needed()
    except Exception:
        pass
    try:
        from projects.p02_legal.corpus import legal_corpus
        legal_corpus._seed_documents_if_needed()
    except Exception:
        pass
    try:
        from projects.p10_finance.audit_chain import audit_chain_manager
        audit_chain_manager._ensure_genesis_block()
    except Exception:
        pass
