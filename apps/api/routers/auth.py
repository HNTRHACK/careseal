"""
CareSeal — Wallet Authentication Router

Provides:
- POST /auth/wallet/challenge: Generates single-use expiring challenge
- POST /auth/wallet/verify: Cryptographically recovers signer address, verifies single-use nonce, and issues session token
"""

from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from apps.api.services.auth_service import challenge_manager, create_session_token
from apps.api.db.store import store

router = APIRouter(prefix="/auth/wallet", tags=["auth"])


class WalletChallengeRequest(BaseModel):
    organization_id: UUID = Field(..., description="Organization the wallet claims membership in")
    user_id: UUID = Field(..., description="Authenticated user ID in Supabase Auth")
    wallet_address: str = Field(
        ...,
        pattern=r"^0x[0-9a-fA-F]{40}$",
        description="EVM wallet address claiming identity"
    )
    chain_id: int = Field(5042002, description="Target network chain ID (defaults to Arc Testnet 5042002)")


class WalletChallengeResponse(BaseModel):
    challenge_id: UUID
    nonce: str
    domain: str
    statement: str
    message_to_sign: str
    issued_at: datetime
    expires_at: datetime


class WalletVerifyRequest(BaseModel):
    challenge_id: UUID
    wallet_address: str = Field(..., pattern=r"^0x[0-9a-fA-F]{40}$")
    signature: str = Field(..., description="EIP-191 / EIP-4361 cryptographic signature")


class WalletVerifyResponse(BaseModel):
    authenticated: bool
    session_token: str
    user_id: UUID
    organization_id: UUID
    roles: list[str]
    wallet_address: str
    expires_at: datetime


@router.post(
    "/challenge",
    response_model=WalletChallengeResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue single-use expiring wallet signature challenge"
)
def request_wallet_challenge(payload: WalletChallengeRequest):
    """
    Security invariant: Cryptographic wallet challenges bind wallet identity
    to an authenticated user and organization with a single-use, 5-minute expiring nonce.
    """
    # Verify user profile exists
    if payload.user_id not in store.profiles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {payload.user_id} not found."
        )

    # Verify organization exists
    if payload.organization_id not in store.organizations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {payload.organization_id} not found."
        )

    # Verify user holds active membership in the organization
    memberships = store.get_user_memberships(payload.user_id, payload.organization_id)
    if not memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User {payload.user_id} is not an active member of organization {payload.organization_id}."
        )

    challenge = challenge_manager.create_challenge(
        organization_id=payload.organization_id,
        user_id=payload.user_id,
        wallet_address=payload.wallet_address,
        chain_id=payload.chain_id
    )

    return WalletChallengeResponse(
        challenge_id=challenge["challenge_id"],
        nonce=challenge["nonce"],
        domain=challenge["domain"],
        statement=challenge["statement"],
        message_to_sign=challenge["message_to_sign"],
        issued_at=challenge["issued_at"],
        expires_at=challenge["expires_at"]
    )


@router.post(
    "/verify",
    response_model=WalletVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify cryptographic wallet signature and issue session token"
)
def verify_wallet_signature(payload: WalletVerifyRequest):
    """
    Recovers signer address using EIP-191, verifies that challenge is unexpired and unconsumed,
    marks challenge consumed (single use), and issues a signed session token.
    """
    challenge = challenge_manager.consume_and_verify_challenge(
        challenge_id=payload.challenge_id,
        wallet_address=payload.wallet_address,
        signature=payload.signature
    )

    user_id = challenge["user_id"]
    org_id = challenge["organization_id"]

    memberships = store.get_user_memberships(user_id, org_id)
    roles = [m["role"] for m in memberships]

    token = create_session_token(
        user_id=user_id,
        org_id=org_id,
        roles=roles,
        wallet_address=payload.wallet_address
    )

    # Record append-only audit event
    store.add_audit_event(
        event_type="WALLET_AUTHENTICATED",
        actor_user_id=user_id,
        actor_org_id=org_id,
        safe_metadata={
            "wallet_address": payload.wallet_address.lower(),
            "chain_id": challenge["chain_id"],
            "challenge_id": str(payload.challenge_id)
        }
    )

    return WalletVerifyResponse(
        authenticated=True,
        session_token=token,
        user_id=user_id,
        organization_id=org_id,
        roles=roles,
        wallet_address=payload.wallet_address.lower(),
        expires_at=datetime.now(timezone.utc)
    )
