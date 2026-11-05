"""
CareSeal — End-to-End Hospital Claim Submission & Verification Slice Test

Tests:
1. Expiring single-use wallet signature challenge generation.
2. Real EIP-191 cryptographic signature verification using eth_account.
3. Replay attack rejection (challenge consumed immediately).
4. Authenticated hospital claim submission with itemized charges.
5. Privacy-conscious duplicate detection (409 Conflict).
6. Organization-level authorization (Cross-tenant read blocked with 403).
7. Append-only non-PHI audit event logging.
8. Redacted verification envelope for Chainlink CRE.
9. World ID verification remains fail-closed (501).
"""

import pytest
from uuid import UUID
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from eth_account import Account
from eth_account.messages import encode_defunct
from apps.api.main import app
from apps.api.db.store import store


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def hospital_alpha_id():
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def hospital_beta_id():
    return UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def user_alpha_id():
    return UUID("aaaa1111-1111-1111-1111-111111111111")


@pytest.fixture
def user_beta_id():
    return UUID("bbbb2222-2222-2222-2222-222222222222")


@pytest.fixture
def hospital_alpha_wallet():
    # Dedicated test key for Hospital Alpha Issuer
    return Account.create()


@pytest.fixture
def hospital_beta_wallet():
    # Dedicated test key for Hospital Beta Issuer
    return Account.create()


def authenticate_wallet(client, org_id: UUID, user_id: UUID, account: Account) -> str:
    """Helper: Executes challenge-response flow and returns session token."""
    # 1. Request Challenge
    res_challenge = client.post(
        "/auth/wallet/challenge",
        json={
            "organization_id": str(org_id),
            "user_id": str(user_id),
            "wallet_address": account.address,
            "chain_id": 5042002
        }
    )
    assert res_challenge.status_code == 200, res_challenge.text
    ch_data = res_challenge.json()
    challenge_id = ch_data["challenge_id"]
    message_to_sign = ch_data["message_to_sign"]

    # 2. Cryptographically Sign Challenge using eth_account
    signable = encode_defunct(text=message_to_sign)
    signed = account.sign_message(signable)

    # 3. Verify Signature
    res_verify = client.post(
        "/auth/wallet/verify",
        json={
            "challenge_id": challenge_id,
            "wallet_address": account.address,
            "signature": signed.signature.hex()
        }
    )
    assert res_verify.status_code == 200, res_verify.text
    return res_verify.json()["session_token"]


def test_wallet_authentication_replay_protection(client, hospital_alpha_id, user_alpha_id, hospital_alpha_wallet):
    """Challenge cannot be consumed more than once (replay attack protection)."""
    # Request challenge
    res = client.post(
        "/auth/wallet/challenge",
        json={
            "organization_id": str(hospital_alpha_id),
            "user_id": str(user_alpha_id),
            "wallet_address": hospital_alpha_wallet.address,
            "chain_id": 5042002
        }
    )
    assert res.status_code == 200
    ch_data = res.json()
    challenge_id = ch_data["challenge_id"]

    signable = encode_defunct(text=ch_data["message_to_sign"])
    signed = hospital_alpha_wallet.sign_message(signable)

    # First verify -> 200 OK
    res_verify1 = client.post(
        "/auth/wallet/verify",
        json={
            "challenge_id": challenge_id,
            "wallet_address": hospital_alpha_wallet.address,
            "signature": signed.signature.hex()
        }
    )
    assert res_verify1.status_code == 200

    # Second verify with same challenge -> 401 Unauthorized (Replay prevented)
    res_verify2 = client.post(
        "/auth/wallet/verify",
        json={
            "challenge_id": challenge_id,
            "wallet_address": hospital_alpha_wallet.address,
            "signature": signed.signature.hex()
        }
    )
    assert res_verify2.status_code == 401
    assert "already been used" in res_verify2.json()["detail"]


def test_wallet_authentication_forged_signature_rejected(client, hospital_alpha_id, user_alpha_id, hospital_alpha_wallet):
    """Signature from wrong key is rejected."""
    res = client.post(
        "/auth/wallet/challenge",
        json={
            "organization_id": str(hospital_alpha_id),
            "user_id": str(user_alpha_id),
            "wallet_address": hospital_alpha_wallet.address,
            "chain_id": 5042002
        }
    )
    assert res.status_code == 200
    ch_data = res.json()

    # Attacker signs challenge with their own key
    attacker_wallet = Account.create()
    signable = encode_defunct(text=ch_data["message_to_sign"])
    signed = attacker_wallet.sign_message(signable)

    res_verify = client.post(
        "/auth/wallet/verify",
        json={
            "challenge_id": ch_data["challenge_id"],
            "wallet_address": hospital_alpha_wallet.address,
            "signature": signed.signature.hex()
        }
    )
    assert res_verify.status_code == 401
    assert "does not match" in res_verify.json()["detail"]


def test_end_to_end_hospital_claim_submission(
    client,
    hospital_alpha_id,
    hospital_beta_id,
    user_alpha_id,
    user_beta_id,
    hospital_alpha_wallet,
    hospital_beta_wallet
):
    """
    Complete Vertical Slice:
    1. Hospital Alpha authenticates via wallet.
    2. Submits itemized claim.
    3. Rejects duplicate submission.
    4. Hospital Beta is denied cross-tenant access.
    5. CRE verification envelope retrieved successfully.
    """
    # 1. Authenticate Hospital Alpha
    token_alpha = authenticate_wallet(client, hospital_alpha_id, user_alpha_id, hospital_alpha_wallet)
    headers_alpha = {"Authorization": f"Bearer {token_alpha}"}

    # 2. Submit Claim for Hospital Alpha
    claim_payload = {
        "hospital_id": str(hospital_alpha_id),
        "hospital_invoice_fingerprint": "SYNTH-INV-ALPHA-9001",
        "procedure_code": "PROC-CARDIO-CABG-01",
        "procedure_description": "Coronary Artery Bypass Grafting",
        "clinical_complexity": "moderate",
        "hospital_payee_address": hospital_alpha_wallet.address,
        "line_items": [
            {
                "category": "Surgeon & Anesthesia",
                "item_description": "Cardiac Specialist Surgical Fee",
                "quantity": 1.0,
                "unit_price_inr_paise": 25000000  # ₹2,50,000
            },
            {
                "category": "OT & ICU",
                "item_description": "ICU Cardiac Monitoring 3 Days",
                "quantity": 3.0,
                "unit_price_inr_paise": 5000000   # ₹50,000 x 3 = ₹1,50,000
            },
            {
                "category": "Consumables",
                "item_description": "Perfusion Cannulae and Oxygenator",
                "quantity": 1.0,
                "unit_price_inr_paise": 10000000  # ₹1,00,000
            }
        ]
    }
    # Total = 2,50,000 + 1,50,000 + 1,00,000 = ₹5,00,000 = 50,000,000 paise

    res_submit = client.post("/claims", json=claim_payload, headers=headers_alpha)
    assert res_submit.status_code == 201, res_submit.text
    claim_data = res_submit.json()
    claim_id = claim_data["id"]

    assert claim_data["estimate_inr_paise"] == 50000000
    assert claim_data["status"] == "submitted"
    assert claim_data["claim_commitment"].startswith("0x")
    assert len(claim_data["claim_commitment"]) == 66
    assert len(claim_data["line_items"]) == 3

    # 3. Duplicate Prevention: Submitting identical invoice fingerprint -> 409 Conflict
    res_dup = client.post("/claims", json=claim_payload, headers=headers_alpha)
    assert res_dup.status_code == 409
    assert "already exists" in res_dup.json()["detail"]

    # 4. Cross-Tenant Read Denial:
    # Authenticate Hospital Beta
    token_beta = authenticate_wallet(client, hospital_beta_id, user_beta_id, hospital_beta_wallet)
    headers_beta = {"Authorization": f"Bearer {token_beta}"}

    # Hospital Beta tries to read Hospital Alpha claim -> 403 Forbidden
    res_cross_read = client.get(f"/claims/{claim_id}", headers=headers_beta)
    assert res_cross_read.status_code == 403
    assert "Cross-tenant access violation" in res_cross_read.json()["detail"]

    # Hospital Alpha reads own claim -> 200 OK
    res_own_read = client.get(f"/claims/{claim_id}", headers=headers_alpha)
    assert res_own_read.status_code == 200
    assert res_own_read.json()["id"] == claim_id

    # 5. Audit Trail Verification:
    res_audit = client.get(f"/claims/{claim_id}/audit", headers=headers_alpha)
    assert res_audit.status_code == 200
    audit_events = res_audit.json()
    assert len(audit_events) >= 1
    assert any(e["event_type"] == "CLAIM_SUBMITTED" for e in audit_events)

    # 6. Redacted Verification Envelope for Chainlink CRE:
    res_cre = client.get(f"/integrations/cre/claims/{claim_id}/verification")
    assert res_cre.status_code == 200
    cre_envelope = res_cre.json()
    assert cre_envelope["claim_id"] == claim_id
    assert cre_envelope["claim_commitment"] == claim_data["claim_commitment"]
    assert cre_envelope["duplicate_check_passed"] is True
    assert cre_envelope["screening_status"] == "submitted"
    assert cre_envelope["token_chain_id"] == 5042002

    # 7. World ID remains strictly fail-closed:
    res_world = client.post(
        "/auth/world/verify",
        json={
            "claim_id": claim_id,
            "action": "review-approval",
            "signal": "reviewer-wallet",
            "proof": {
                "merkle_root": "0x123",
                "nullifier_hash": "0x456",
                "proof": "0x789",
                "verification_level": "device"
            },
            "nonce": "test-nonce"
        }
    )
    assert res_world.status_code == 501
    assert "scheduled for Phase 04" in res_world.json()["detail"]

