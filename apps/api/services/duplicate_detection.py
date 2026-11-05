"""
CareSeal — Privacy-Conscious Duplicate Detection Engine

Detects:
1. Exact invoice fingerprint collisions within the same hospital.
2. Cryptographic claim commitment collisions across the platform.
3. Identical line-item charge composition across synthetic claims.

PRIVACY INVARIANT:
Operates strictly on synthetic identifiers and cryptographic digests.
Never processes raw patient identities or personal documents.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
import hashlib
import json
from pydantic import BaseModel
from apps.api.db.store import store


class DuplicateCheckResult(BaseModel):
    passed: bool
    reason: Optional[str] = None
    existing_claim_id: Optional[UUID] = None
    duplicate_flag: Optional[str] = None


def compute_line_items_digest(procedure_code: str, line_items: List[Dict[str, Any]]) -> str:
    """Computes a deterministic hash of itemized charge composition."""
    normalized_items = sorted(
        [
            {
                "category": item["category"].strip().lower(),
                "description": item["item_description"].strip().lower(),
                "quantity": float(item["quantity"]),
                "unit_price": int(item["unit_price_inr_paise"]),
            }
            for item in line_items
        ],
        key=lambda x: (x["category"], x["description"])
    )
    payload = f"{procedure_code.strip().upper()}:{json.dumps(normalized_items, sort_keys=True)}"
    return hashlib.sha256(payload.encode()).hexdigest()


def check_claim_duplicates(
    hospital_id: UUID,
    invoice_fingerprint: str,
    procedure_code: str,
    line_items: List[Dict[str, Any]],
    claim_commitment: Optional[str] = None
) -> DuplicateCheckResult:
    """
    Evaluates new claim against stored claims for duplicate invoice fingerprints or commitments.
    """
    # 1. Exact hospital + invoice fingerprint collision
    existing_by_fp = store.find_claim_by_fingerprint(hospital_id, invoice_fingerprint)
    if existing_by_fp:
        return DuplicateCheckResult(
            passed=False,
            reason=f"Claim with invoice fingerprint '{invoice_fingerprint}' already exists for this hospital.",
            existing_claim_id=existing_by_fp["id"],
            duplicate_flag="EXACT_INVOICE_DUPLICATE"
        )

    # 2. Cryptographic commitment collision
    if claim_commitment:
        existing_by_commit = store.find_claim_by_commitment(claim_commitment)
        if existing_by_commit:
            return DuplicateCheckResult(
                passed=False,
                reason="Cryptographic claim commitment is already registered.",
                existing_claim_id=existing_by_commit["id"],
                duplicate_flag="COMMITMENT_COLLISION"
            )

    # 3. Identical item composition similarity flag
    new_digest = compute_line_items_digest(procedure_code, line_items)
    for c_id, stored_claim in store.medical_claims.items():
        if stored_claim.get("line_items_digest") == new_digest:
            return DuplicateCheckResult(
                passed=True,  # Allow submission but annotate anomaly flag
                reason="Warning: Identical charge profile found in historical claims.",
                existing_claim_id=c_id,
                duplicate_flag="CHARGE_COMPOSITION_ANOMALY"
            )

    return DuplicateCheckResult(passed=True)

