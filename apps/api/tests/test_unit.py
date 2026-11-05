import uuid
from uuid import UUID
import pytest
from fastapi import HTTPException
from apps.api.routers.health import get_health
from apps.api.routers.auth import (
    request_wallet_challenge,
    WalletChallengeRequest
)
from apps.api.routers.world import (
    verify_world_proof,
    WorldVerifyRequest,
    WorldProofPayload
)
from apps.api.routers.cre import (
    get_claim_verification_envelope
)
from apps.api.db.store import store


def test_unit_get_health():
    res = get_health()
    assert res.status == "healthy"
    assert res.service == "careseal-api"
    assert res.version == "0.1.0"


def test_unit_request_wallet_challenge():
    org_id = UUID("11111111-1111-1111-1111-111111111111")
    user_id = UUID("aaaa1111-1111-1111-1111-111111111111")
    req = WalletChallengeRequest(
        organization_id=org_id,
        user_id=user_id,
        wallet_address="0x1234567890123456789012345678901234567890",
        chain_id=5042002
    )
    res = request_wallet_challenge(req)
    assert res.nonce is not None
    assert len(res.nonce) == 32
    assert "CareSeal Verification" in res.statement


def test_unit_verify_world_proof_deferred():
    req = WorldVerifyRequest(
        claim_id=uuid.uuid4(),
        action="review-approval",
        signal="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        proof=WorldProofPayload(
            merkle_root="0x1234",
            nullifier_hash="0x5678",
            proof="0xabcd",
            verification_level="device"
        ),
        nonce="nonce-123"
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_world_proof(req)
    assert exc_info.value.status_code == 501
    assert "Phase 04" in exc_info.value.detail


def test_unit_get_cre_envelope_not_found():
    with pytest.raises(HTTPException) as exc_info:
        get_claim_verification_envelope(uuid.uuid4())
    assert exc_info.value.status_code == 404
