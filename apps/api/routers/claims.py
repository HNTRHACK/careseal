"""
CareSeal — Medical Claims Router

Provides:
- POST /claims: Authenticated hospital claim submission with itemized charges & duplicate detection
- GET /claims: List claims scoped strictly to caller's organization
- GET /claims/{id}: Retrieve single claim with tenant isolation enforcement
- GET /claims/{id}/audit: Append-only audit trail for the claim
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from eth_utils import keccak
from apps.api.security.org_isolation import CallerContext, enforce_tenant_isolation, TenantAccessDenied
from apps.api.services.auth_service import get_current_caller
from apps.api.services.duplicate_detection import check_claim_duplicates, compute_line_items_digest
from apps.api.db.store import store

router = APIRouter(prefix="/claims", tags=["claims"])


class ClaimLineItemCreate(BaseModel):
    category: str = Field(..., json_schema_extra={"example": "Surgical"})
    item_description: str = Field(..., json_schema_extra={"example": "Coronary Artery Bypass Graft Consumables"})
    quantity: float = Field(..., gt=0, json_schema_extra={"example": 1.0})
    unit_price_inr_paise: int = Field(..., ge=0, json_schema_extra={"example": 50000000})  # in paise (₹5,00,000)


class ClaimLineItemResponse(BaseModel):
    id: UUID
    claim_id: UUID
    category: str
    item_description: str
    quantity: float
    unit_price_inr_paise: int
    created_at: datetime


class ClaimSubmissionRequest(BaseModel):
    hospital_id: UUID = Field(..., description="Issuing hospital organization ID")
    hospital_invoice_fingerprint: str = Field(
        ...,
        min_length=3,
        description="Opaque synthetic invoice fingerprint (never real patient invoice numbers)"
    )
    procedure_code: str = Field(..., json_schema_extra={"example": "PROC-CABG-01"})
    procedure_description: str = Field(..., json_schema_extra={"example": "Coronary Artery Bypass Grafting"})
    clinical_complexity: Literal["standard", "moderate", "high"] = Field("standard")
    hospital_payee_address: str = Field(..., pattern=r"^0x[0-9a-fA-F]{40}$")
    line_items: List[ClaimLineItemCreate] = Field(..., min_length=1)


class ClaimDetailResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    hospital_invoice_fingerprint: str
    claim_commitment: str
    procedure_code: str
    procedure_description: str
    clinical_complexity: str
    estimate_inr_paise: int
    approved_cap_token_units: Optional[int] = None
    hospital_payee_address: str
    status: str
    risk_flags: List[str]
    line_items: List[ClaimLineItemResponse]
    created_by: UUID
    created_at: datetime
    updated_at: datetime


@router.post(
    "",
    response_model=ClaimDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit authenticated hospital claim with itemized charges"
)
def submit_medical_claim(
    payload: ClaimSubmissionRequest,
    caller: CallerContext = Depends(get_current_caller)
):
    """
    Hospital Issuer submits a claim:
    1. Enforces that caller belongs to payload.hospital_id and has 'issuer' or 'admin' role.
    2. Runs duplicate detection against historical invoice fingerprints and commitments.
    3. Calculates itemized charge total from line items.
    4. Computes confidential cryptographic claim commitment.
    5. Saves claim and emits an append-only audit event.
    """
    # 1. Organization-level authorization
    try:
        enforce_tenant_isolation(
            resource_hospital_id=payload.hospital_id,
            caller=caller,
            allowed_roles=["admin", "issuer"]
        )
    except TenantAccessDenied as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )

    # 2. Duplicate Detection
    dup_result = check_claim_duplicates(
        hospital_id=payload.hospital_id,
        invoice_fingerprint=payload.hospital_invoice_fingerprint,
        procedure_code=payload.procedure_code,
        line_items=[item.model_dump() for item in payload.line_items]
    )
    if not dup_result.passed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=dup_result.reason
        )

    # 3. Itemized Charge Calculation
    total_estimate_paise = sum(
        int(round(item.quantity * item.unit_price_inr_paise))
        for item in payload.line_items
    )
    if total_estimate_paise <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total claim estimate must be greater than zero."
        )

    claim_id = uuid4()
    now = datetime.now(timezone.utc)

    # 4. Generate Cryptographic Claim Commitment
    # keccak256(abi.encodePacked(claim_id, hospital_payee, total_estimate_paise, salt))
    salt = uuid4().bytes
    commitment_preimage = claim_id.bytes + bytes.fromhex(payload.hospital_payee_address[2:]) + total_estimate_paise.to_bytes(32, "big") + salt
    claim_commitment = "0x" + keccak(commitment_preimage).hex()

    risk_flags = []
    if dup_result.duplicate_flag:
        risk_flags.append(dup_result.duplicate_flag)

    line_items_digest = compute_line_items_digest(
        payload.procedure_code,
        [item.model_dump() for item in payload.line_items]
    )

    claim_record = {
        "id": claim_id,
        "hospital_id": payload.hospital_id,
        "patient_ref_token": uuid4(),
        "hospital_invoice_fingerprint": payload.hospital_invoice_fingerprint,
        "claim_commitment": claim_commitment,
        "procedure_code": payload.procedure_code,
        "procedure_description": payload.procedure_description,
        "clinical_complexity": payload.clinical_complexity,
        "estimate_inr_paise": total_estimate_paise,
        "approved_cap_token_units": int(total_estimate_paise / 100),  # 1:1 test conversion (1 INR = 1 USDC cent = 10,000 micro-units)
        "token_chain_id": 5042002,
        "hospital_payee_address": payload.hospital_payee_address.lower(),
        "status": "submitted",
        "risk_flags": risk_flags,
        "line_items_digest": line_items_digest,
        "created_by": caller.user_id,
        "created_at": now,
        "updated_at": now
    }

    stored_items = []
    for item in payload.line_items:
        stored_items.append({
            "id": uuid4(),
            "claim_id": claim_id,
            "category": item.category,
            "item_description": item.item_description,
            "quantity": item.quantity,
            "unit_price_inr_paise": item.unit_price_inr_paise,
            "created_at": now
        })

    store.save_claim_with_items(claim_record, stored_items)

    # 5. Record Append-Only Non-PHI Audit Event
    store.add_audit_event(
        event_type="CLAIM_SUBMITTED",
        actor_user_id=caller.user_id,
        actor_org_id=caller.org_id,
        claim_id=claim_id,
        safe_metadata={
            "hospital_id": str(payload.hospital_id),
            "claim_commitment": claim_commitment,
            "estimate_inr_paise": total_estimate_paise,
            "line_item_count": len(stored_items)
        }
    )

    return ClaimDetailResponse(
        id=claim_id,
        hospital_id=payload.hospital_id,
        hospital_invoice_fingerprint=payload.hospital_invoice_fingerprint,
        claim_commitment=claim_commitment,
        procedure_code=payload.procedure_code,
        procedure_description=payload.procedure_description,
        clinical_complexity=payload.clinical_complexity,
        estimate_inr_paise=total_estimate_paise,
        approved_cap_token_units=claim_record["approved_cap_token_units"],
        hospital_payee_address=payload.hospital_payee_address.lower(),
        status=claim_record["status"],
        risk_flags=risk_flags,
        line_items=[ClaimLineItemResponse(**item) for item in stored_items],
        created_by=caller.user_id,
        created_at=now,
        updated_at=now
    )


@router.get(
    "/{claim_id}",
    response_model=ClaimDetailResponse,
    summary="Retrieve single claim with organization-level authorization"
)
def get_claim_by_id(
    claim_id: UUID,
    caller: CallerContext = Depends(get_current_caller)
):
    """
    Enforces tenant isolation: Caller must belong to the issuing hospital OR be an authorized reviewer.
    """
    claim = store.get_claim(claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found."
        )

    try:
        enforce_tenant_isolation(
            resource_hospital_id=claim["hospital_id"],
            caller=caller,
            allow_cross_tenant_reviewers=True
        )
    except TenantAccessDenied as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )

    stored_items = store.claim_line_items.get(claim_id, [])

    return ClaimDetailResponse(
        id=claim["id"],
        hospital_id=claim["hospital_id"],
        hospital_invoice_fingerprint=claim["hospital_invoice_fingerprint"],
        claim_commitment=claim["claim_commitment"],
        procedure_code=claim["procedure_code"],
        procedure_description=claim["procedure_description"],
        clinical_complexity=claim["clinical_complexity"],
        estimate_inr_paise=claim["estimate_inr_paise"],
        approved_cap_token_units=claim.get("approved_cap_token_units"),
        hospital_payee_address=claim["hospital_payee_address"],
        status=claim["status"],
        risk_flags=claim.get("risk_flags", []),
        line_items=[ClaimLineItemResponse(**item) for item in stored_items],
        created_by=claim["created_by"],
        created_at=claim["created_at"],
        updated_at=claim["updated_at"]
    )


@router.get(
    "",
    response_model=List[ClaimDetailResponse],
    summary="List claims scoped strictly to caller's organization"
)
def list_claims(
    caller: CallerContext = Depends(get_current_caller)
):
    """
    Returns only claims belonging to caller's organization.
    """
    results = []
    for claim in store.medical_claims.values():
        if claim["hospital_id"] == caller.org_id:
            items = store.claim_line_items.get(claim["id"], [])
            results.append(
                ClaimDetailResponse(
                    id=claim["id"],
                    hospital_id=claim["hospital_id"],
                    hospital_invoice_fingerprint=claim["hospital_invoice_fingerprint"],
                    claim_commitment=claim["claim_commitment"],
                    procedure_code=claim["procedure_code"],
                    procedure_description=claim["procedure_description"],
                    clinical_complexity=claim["clinical_complexity"],
                    estimate_inr_paise=claim["estimate_inr_paise"],
                    approved_cap_token_units=claim.get("approved_cap_token_units"),
                    hospital_payee_address=claim["hospital_payee_address"],
                    status=claim["status"],
                    risk_flags=claim.get("risk_flags", []),
                    line_items=[ClaimLineItemResponse(**item) for item in items],
                    created_by=claim["created_by"],
                    created_at=claim["created_at"],
                    updated_at=claim["updated_at"]
                )
            )
    return results


@router.get(
    "/{claim_id}/audit",
    summary="Retrieve non-PHI audit events for a claim"
)
def get_claim_audit_events(
    claim_id: UUID,
    caller: CallerContext = Depends(get_current_caller)
):
    """
    Returns append-only audit trail for the claim, enforcing tenant isolation.
    """
    claim = store.get_claim(claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found."
        )

    try:
        enforce_tenant_isolation(
            resource_hospital_id=claim["hospital_id"],
            caller=caller,
            allow_cross_tenant_reviewers=True
        )
    except TenantAccessDenied as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )

    events = [e for e in store.audit_events if e.get("claim_id") == claim_id]
    return events
