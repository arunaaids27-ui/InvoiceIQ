"""
confidence/confidence_scorer.py

Configurable 3-Tier Confidence Scoring & Routing Engine for InvoiceIQ.
Features:
  - 3 Tiers: High (>= 85%), Moderate (50% - 84%), Low (< 50%)
  - Dynamic Field Existence Handling (Optional/Receipt fields like due_date/tax absent -> N/A with No Score Penalty)
  - Mathematical Cross-Validation (|Subtotal + Tax - Total| <= 0.05)
  - Critical vs. Optional Field Weighting
"""

from typing import Dict, Any, Tuple, Optional

# ============================================================
# CONFIGURABLE THRESHOLDS
# ============================================================
AUTO_APPROVE_THRESHOLD: int = 85  # >= 85: Auto-approved, bypasses manual queue
CAUTION_THRESHOLD: int = 50       # 50 - 84: Moderate confidence, requires human review
                                  # < 50: Low confidence / Failed extraction

# Tier Visual Symbols & Labels
TIER_SYMBOLS = {
    "HIGH": "✅",       # Green checkmark
    "MODERATE": "⚠️",   # Yellow caution symbol
    "LOW": "🚨",        # Red warning sign
    "NA": "⚪"          # Neutral/Not Applicable
}

TIER_STATUSES = {
    "HIGH": "AUTO_ACCEPTED",
    "MODERATE": "NEEDS_REVIEW",
    "LOW": "FAILED_REJECTED",
    "NA": "NOT_APPLICABLE"
}


def classify_tier(score: Optional[float]) -> Tuple[str, str, str]:
    """
    Classifies any numeric score into one of three distinct tiers.
    Safely handles None, null, and non-numeric inputs.
    
    Returns:
        Tuple[str, str, str]: (tier_name, status_code, visual_symbol)
    """
    if score is None:
        return "LOW", TIER_STATUSES["LOW"], TIER_SYMBOLS["LOW"]
    
    try:
        numeric_score = float(score)
    except (ValueError, TypeError):
        return "LOW", TIER_STATUSES["LOW"], TIER_SYMBOLS["LOW"]

    if numeric_score >= AUTO_APPROVE_THRESHOLD:
        return "HIGH", TIER_STATUSES["HIGH"], TIER_SYMBOLS["HIGH"]
    elif numeric_score >= CAUTION_THRESHOLD:
        return "MODERATE", TIER_STATUSES["MODERATE"], TIER_SYMBOLS["MODERATE"]
    else:
        return "LOW", TIER_STATUSES["LOW"], TIER_SYMBOLS["LOW"]


def _score_field(value: Any, is_critical: bool = True) -> int:
    """Evaluates presence and basic format validity of individual fields."""
    if value is None:
        return 0
    
    val_str = str(value).strip()
    if not val_str or val_str.lower() in ["none", "null", "n/a", "unknown", ""]:
        return 0
    
    if is_critical and len(val_str) < 2:
        return 40  # Ambiguous single-character entry
    
    return 100


def score_invoice_confidence(invoice_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes field-level scores, checks mathematical consistency,
    intelligently handles absent optional fields without penalization,
    and aggregates an overall confidence score across 3 distinct tiers.
    """
    if not invoice_data or not isinstance(invoice_data, dict):
        return {
            "overall_score": 0,
            "overall_tier": "LOW",
            "overall_status": TIER_STATUSES["LOW"],
            "symbol": TIER_SYMBOLS["LOW"],
            "field_scores": {},
            "arithmetic_valid": False,
            "requires_review": True
        }

    # Mandatory fields strictly required on every valid financial document
    critical_fields = ["invoice_number", "invoice_date", "vendor_name", "total_amount"]
    
    # Optional fields (Receipts/Certain layouts often do not possess these)
    optional_fields = ["due_date", "vendor_address", "customer_name", "customer_address", "currency", "subtotal", "tax"]
    
    field_scores: Dict[str, Dict[str, Any]] = {}
    total_weights = 0.0
    weighted_sum = 0.0

    # 1. Evaluate Critical Fields (Weight = 2.0)
    for field in critical_fields:
        val = invoice_data.get(field)
        score = _score_field(val, is_critical=True)
        tier, status, sym = classify_tier(score)
        
        field_scores[field] = {
            "score": score,
            "tier": tier,
            "status": status,
            "symbol": sym,
            "value": val,
            "is_applicable": True
        }
        weighted_sum += (score * 2.0)
        total_weights += 2.0

    # 2. Evaluate Optional Fields (Weight = 1.0)
    for field in optional_fields:
        val = invoice_data.get(field)
        val_str = "" if val is None else str(val).strip().lower()
        
        # Check if the field is genuinely absent or not applicable on this receipt
        is_absent = (val is None) or (val_str in ["", "none", "null", "n/a", "unknown"])
        
        if is_absent:
            # Mark as N/A: Do NOT penalize the invoice overall score
            field_scores[field] = {
                "score": 100,
                "tier": "NA",
                "status": TIER_STATUSES["NA"],
                "symbol": TIER_SYMBOLS["NA"],
                "value": "N/A (Not on Document)",
                "is_applicable": False
            }
        else:
            score = _score_field(val, is_critical=False)
            tier, status, sym = classify_tier(score)
            field_scores[field] = {
                "score": score,
                "tier": tier,
                "status": status,
                "symbol": sym,
                "value": val,
                "is_applicable": True
            }
            weighted_sum += (score * 1.0)
            total_weights += 1.0

    # 3. Mathematical Verification (Subtotal + Tax == Total)
    arithmetic_valid = False
    subtotal = invoice_data.get("subtotal")
    tax = invoice_data.get("tax")
    total = invoice_data.get("total_amount")

    try:
        if total is not None and str(total).strip().lower() not in ["", "none", "null"]:
            f_total = float(total)
            f_subtotal = float(subtotal) if (subtotal is not None and str(subtotal).strip().lower() not in ["", "none", "null"]) else None
            f_tax = float(tax) if (tax is not None and str(tax).strip().lower() not in ["", "none", "null"]) else 0.0
            
            # If subtotal & tax are present, verify equation
            if f_subtotal is not None and f_tax is not None:
                if abs((f_subtotal + f_tax) - f_total) <= 0.05:
                    arithmetic_valid = True
            # If only subtotal is present and matches total (e.g. 0% tax)
            elif f_subtotal is not None and tax is None:
                if abs(f_subtotal - f_total) <= 0.05:
                    arithmetic_valid = True
            # Standalone total receipt with no breakdown
            elif f_subtotal is None and tax is None:
                arithmetic_valid = True
    except (ValueError, TypeError):
        arithmetic_valid = False

    # 4. Line Items Validation (Weight = 1.5)
    line_items = invoice_data.get("line_items")
    if isinstance(line_items, list) and len(line_items) > 0:
        item_scores = [_score_field(item.get("description")) for item in line_items if isinstance(item, dict)]
        avg_item_score = int(sum(item_scores) / max(len(item_scores), 1))
    else:
        avg_item_score = 40  # Penalty for missing itemization
    
    tier, status, sym = classify_tier(avg_item_score)
    field_scores["line_items"] = {
        "score": avg_item_score,
        "tier": tier,
        "status": status,
        "symbol": sym,
        "value": f"{len(line_items) if isinstance(line_items, list) else 0} items extracted",
        "is_applicable": True
    }
    weighted_sum += (avg_item_score * 1.5)
    total_weights += 1.5

    # 5. Aggregate Overall Score
    raw_overall = int(weighted_sum / max(total_weights, 1.0))
    
    # Arithmetic consistency penalty if amounts conflict
    if not arithmetic_valid and (subtotal is not None and tax is not None):
        raw_overall = max(0, raw_overall - 15)

    final_score = min(100, max(0, raw_overall))
    overall_tier, overall_status, overall_symbol = classify_tier(final_score)

    return {
        "overall_score": final_score,
        "overall_tier": overall_tier,
        "overall_status": overall_status,
        "symbol": overall_symbol,
        "threshold_used": AUTO_APPROVE_THRESHOLD,
        "arithmetic_valid": arithmetic_valid,
        "requires_review": final_score < AUTO_APPROVE_THRESHOLD,
        "field_scores": field_scores
    }


def requires_manual_review(confidence_result: Dict[str, Any]) -> Dict[str, Any]:
    """Determines whether an invoice must be routed to human review."""
    score = confidence_result.get("overall_score", 0)
    needs_review = score < AUTO_APPROVE_THRESHOLD
    
    return {
        "needs_review": needs_review,
        "reason": "Score below 85% auto-approval threshold" if needs_review else "Meets automated quality standard",
        "tier": confidence_result.get("overall_tier", "LOW"),
        "symbol": confidence_result.get("symbol", "🚨")
    }