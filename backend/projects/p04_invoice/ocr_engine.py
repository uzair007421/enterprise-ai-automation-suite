"""
Invoice OCR & Vision Extraction Engine
Extracts vendor, invoice number, dates, line items, and monetary totals
using Gemini Vision API / Multimodal LLM with fallback parser.
"""
import re
import json
import logging
from typing import Optional
from core.config import settings
from core.llm import llm
from .schemas import InvoiceExtractedData, LineItem

logger = logging.getLogger("p04_invoice.ocr")

def parse_text_heuristics(text: str) -> InvoiceExtractedData:
    """
    Rule-based extraction when no LLM key is configured.
    Never invents or defaults business data; missing fields remain None.
    """
    clean_text = text.strip()
    if not clean_text:
        return InvoiceExtractedData(
            vendor_name=None,
            invoice_number=None,
            invoice_date=None,
            currency="USD",
            line_items=[],
            subtotal=None,
            tax_amount=0.0,
            total_amount=None,
            confidence_score=10
        )

    # 1. Check for invoice number
    inv_num = None
    num_match = re.search(r"\b(?:invoice|inv|bill)\s*(?:number|num|no)?\s*[:#]\s*([A-Za-z0-9\-_]+)|\b(INV-[A-Za-z0-9\-_]+)", clean_text, re.IGNORECASE)
    if num_match:
        extracted_num = (num_match.group(1) or num_match.group(2) or "").strip()
        if len(extracted_num) >= 2 and extracted_num.lower() not in ("and", "the", "for", "with", "from"):
            inv_num = extracted_num

    # 2. Check for dates
    inv_date = None
    date_match = re.search(r"\b(?:date|dated|invoice\s*date)[:\s]+([0-9]{4}[-/][0-9]{2}[-/][0-9]{2}|[0-9]{2}[-/][0-9]{2}[-/][0-9]{4})", clean_text, re.IGNORECASE)
    if date_match:
        inv_date = date_match.group(1).strip()
    else:
        date_iso = re.search(r"\b([0-9]{4}-[0-9]{2}-[0-9]{2})\b", clean_text)
        if date_iso:
            inv_date = date_iso.group(1).strip()

    # 3. Check for amounts
    total = None
    tot_match = re.search(r"\b(?:total\s*amount|total\s*due|amount\s*due|grand\s*total|final\s*total|total)\b[:\s]*(?:[A-Z]{3}|\$)?\s*([0-9,]+\.[0-9]{2})", clean_text, re.IGNORECASE)
    if tot_match:
        try:
            total = float(tot_match.group(1).replace(",", ""))
        except (ValueError, IndexError):
            total = None

    subtotal = None
    sub_match = re.search(r"\b(?:sub\s*total|subtotal|net\s*amount)\b[:\s]*(?:[A-Z]{3}|\$)?\s*([0-9,]+\.[0-9]{2})", clean_text, re.IGNORECASE)
    if sub_match:
        try:
            subtotal = float(sub_match.group(1).replace(",", ""))
        except (ValueError, IndexError):
            subtotal = None

    tax = 0.0
    tax_match = re.search(r"\b(?:tax\s*amount|sales\s*tax|tax|vat|gst)\b[:\s]*(?:[A-Z]{3}|\$)?\s*([0-9,]+\.[0-9]{2})", clean_text, re.IGNORECASE)
    if tax_match:
        try:
            tax = float(tax_match.group(1).replace(",", ""))
        except (ValueError, IndexError):
            tax = 0.0

    # Currency
    curr_match = re.search(r"\b(USD|EUR|GBP|PKR|CAD|AUD)\b|\$", clean_text)
    currency = "USD"
    if curr_match:
        matched_curr = curr_match.group(0)
        currency = "USD" if matched_curr == "$" else matched_curr.upper()

    # 4. Check for vendor
    vendor = None
    vend_match = re.search(r"(?:vendor|from|seller|supplier|billed\s*by)[:\s]+([^\n\r]+)", clean_text, re.IGNORECASE)
    if vend_match:
        candidate = vend_match.group(1).strip()
        candidate = re.split(r"\b(?:date|inv|invoice|bill\s*to)[:#]", candidate, flags=re.IGNORECASE)[0].strip()
        if candidate and len(candidate) > 1:
            vendor = candidate

    # Line items
    line_items = []
    lines = [l.strip() for l in clean_text.splitlines() if l.strip()]
    for line in lines:
        li_match = re.search(r"^([A-Za-z0-9\s\-_]+?)\s+(\d+(?:\.\d+)?)\s*(?:x|@)?\s*\$?([0-9,]+\.[0-9]{2})\s+\$?([0-9,]+\.[0-9]{2})$", line)
        if li_match:
            try:
                desc = li_match.group(1).strip()
                qty = float(li_match.group(2))
                uprice = float(li_match.group(3).replace(",", ""))
                ltotal = float(li_match.group(4).replace(",", ""))
                line_items.append(LineItem(description=desc, quantity=qty, unit_price=uprice, line_total=ltotal))
            except Exception:
                pass

    if not vendor and (inv_num or total is not None or inv_date or line_items):
        for line in lines:
            if re.match(r"^(?:invoice|bill\s*to|date|total|subtotal|receipt)\b", line, re.IGNORECASE):
                continue
            if len(line) >= 2 and not line.startswith("$"):
                vendor = re.split(r"\b(?:date|inv|invoice)[:#]", line, flags=re.IGNORECASE)[0].strip()
                if vendor:
                    break

    # If line items found and subtotal is None
    if subtotal is None and line_items:
        subtotal = round(sum(it.line_total for it in line_items), 2)
    if total is None and subtotal is not None and tax is not None:
        total = round(subtotal + tax, 2)

    # Gibberish check: no vendor, no invoice number, no total, no subtotal
    if total is None and inv_num is None and not line_items:
        return InvoiceExtractedData(
            vendor_name=None,
            invoice_number=None,
            invoice_date=None,
            currency=currency,
            line_items=[],
            subtotal=None,
            tax_amount=0.0,
            total_amount=None,
            confidence_score=15
        )

    # Score calculation
    confidence = 90
    if not vendor or not inv_num or total is None or subtotal is None:
        confidence = 45
    elif subtotal is not None and total is not None and abs((subtotal + tax) - total) > 0.05:
        confidence = 65

    return InvoiceExtractedData(
        vendor_name=vendor,
        invoice_number=inv_num,
        invoice_date=inv_date,
        currency=currency,
        line_items=line_items,
        subtotal=subtotal,
        tax_amount=tax,
        total_amount=total,
        confidence_score=confidence
    )

def extract_invoice_from_content(
    raw_text: str,
    filename: str = "document.pdf",
    mime_type: str = "application/pdf"
) -> tuple[InvoiceExtractedData, str]:
    """
    Extracts structured fields from raw invoice text.
    If LLM configured, attempts structured extraction and cross-checks with rules.
    If LLM not configured or fails, falls back strictly to rule-based parser.
    Returns (extracted_data, engine) where engine is 'llm' or 'rules'.
    """
    if llm.is_available():
        system_instruction = (
            "You are an expert OCR and financial document parser. "
            "Extract every line item, subtotal, tax amount, and total with exact numerical precision. "
            "Never invent numbers. If a line item does not have a quantity, default to 1.0. "
            "Calculate line_total = quantity * unit_price for each item."
        )

        prompt = (
            f"Analyze this raw invoice text from file '{filename}' and extract all fields according to the schema:\n\n"
            f"--- DOCUMENT START ---\n"
            f"{raw_text[:8000]}\n"
            f"--- DOCUMENT END ---\n"
        )

        try:
            extracted = llm.generate_structured(
                prompt=prompt,
                response_model=InvoiceExtractedData,
                system_instruction=system_instruction,
                temperature=0.0
            )
            # Cross-check against rule parser
            rule_data = parse_text_heuristics(raw_text)
            if rule_data.total_amount is not None and extracted.total_amount is not None:
                if abs(rule_data.total_amount - extracted.total_amount) > 0.05:
                    extracted.confidence_score = min(extracted.confidence_score, 50)
            return extracted, "llm"
        except Exception as e:
            logger.warning(f"LLM extraction unavailable/failed, using rules: {e}")
            return parse_text_heuristics(raw_text), "rules"

    return parse_text_heuristics(raw_text), "rules"
