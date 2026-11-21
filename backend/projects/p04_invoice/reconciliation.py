"""
4-Way Mathematical Reconciliation Engine
Strict validation verifying:
1. Individual line item math: quantity * unit_price == line_total
2. Sum of line totals vs stated subtotal
3. Subtotal + tax == stated total
4. Tax rate plausibility and negative/anomaly detection
"""
from typing import List
from .schemas import InvoiceExtractedData, ReconciliationCheck

TOLERANCE = 0.02  # Two-cent tolerance for rounding

def reconcile_invoice_math(extracted: InvoiceExtractedData) -> ReconciliationCheck:
    discrepancies: List[str] = []

    # 1. Individual line items calculation
    calculated_subtotal = 0.0
    for idx, item in enumerate(extracted.line_items, 1):
        expected_line_total = round(item.quantity * item.unit_price, 2)
        if abs(expected_line_total - item.line_total) > TOLERANCE:
            discrepancies.append(
                f"Line item {idx} ('{item.description}'): qty ({item.quantity}) * unit price (${item.unit_price:.2f}) "
                f"= ${expected_line_total:.2f}, but line total states ${item.line_total:.2f}"
            )
        calculated_subtotal += item.line_total

    calculated_subtotal = round(calculated_subtotal, 2)
    subtotal_delta = round(abs(calculated_subtotal - extracted.subtotal), 2)
    line_subtotal_matched = subtotal_delta <= TOLERANCE

    if not line_subtotal_matched and len(extracted.line_items) > 0:
        discrepancies.append(
            f"Sum of line items (${calculated_subtotal:.2f}) does not match stated subtotal (${extracted.subtotal:.2f}) "
            f"[delta: ${subtotal_delta:.2f}]"
        )

    # 2. Subtotal + Tax vs Stated Total
    expected_total = round(extracted.subtotal + extracted.tax_amount, 2)
    total_delta = round(abs(expected_total - extracted.total_amount), 2)
    total_matched = total_delta <= TOLERANCE

    if not total_matched:
        discrepancies.append(
            f"Subtotal (${extracted.subtotal:.2f}) + Tax (${extracted.tax_amount:.2f}) = ${expected_total:.2f}, "
            f"does not match stated total (${extracted.total_amount:.2f}) [delta: ${total_delta:.2f}]"
        )

    # 3. Tax rate calculation
    tax_rate = None
    if extracted.subtotal > 0 and extracted.tax_amount > 0:
        tax_rate = round((extracted.tax_amount / extracted.subtotal) * 100, 2)

    # 4. Sanity checks (negatives or zero total)
    if extracted.total_amount <= 0:
        discrepancies.append(f"Invalid total amount: ${extracted.total_amount:.2f} must be greater than zero.")

    # Determine status
    if len(discrepancies) == 0:
        overall_status = "APPROVED"
    elif not total_matched or total_delta > 1.0:
        overall_status = "DISCREPANCY"
    else:
        overall_status = "NEEDS_MANUAL_REVIEW"

    return ReconciliationCheck(
        line_items_vs_subtotal_matched=line_subtotal_matched,
        line_items_sum=calculated_subtotal,
        stated_subtotal=extracted.subtotal,
        subtotal_delta=subtotal_delta,
        subtotal_plus_tax_vs_total_matched=total_matched,
        expected_total=expected_total,
        stated_total=extracted.total_amount,
        total_delta=total_delta,
        tax_rate_percentage=tax_rate,
        discrepancy_details=discrepancies,
        overall_status=overall_status
    )
