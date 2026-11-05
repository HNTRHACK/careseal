"""
CareSeal — Authentication & Cryptographic Wallet Signature Service

Provides:
- Single-use, expiring wallet challenges bound to an organization and user.
- Real EIP-191 signature recovery using eth_account.
- Immediate challenge invalidation (single-use guarantee).
- Cryptographically signed HMAC-SHA256 session tokens.
- FastAPI dependency for extracting and verifying caller context.
"""

import os
import secrets
import hmac
import hashlib
import json
import base64
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any, List
from uuid import UUID, uuid4
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from eth_account.messages import encode_defunct
from eth_account import Account
from apps.api.security.org_isolation import CallerContext
from apps.api.db.store import store

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "careseal_hackathon_super_secret_key_2026").encode()
CHALLENGE_EXPIRY_MINUTES = 5
SESSION_EXPIRY_HOURS = 8

security_bearer = HTTPBearer(auto_error=False)


class WalletChallengeManager:
    """In-memory tracking of active single-use challenges."""
    def __init__(self):
        self._challenges: Dict[UUID, Dict[str, Any]] = {}

    def create_challenge(
        self,
        organization_id: UUID,
        user_id: UUID,
        wallet_address: str,
        chain_id: int = 5042002,
        domain: str = "careseal.health"
    ) -> Dict[str, Any]:
        challenge_id = uuid4()
        nonce = secrets.token_hex(16)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=CHALLENGE_EXPIRY_MINUTES)
        
        statement = (
            f"CareSeal Verification: Sign this challenge to authenticate wallet identity. "
            f"Nonce: {nonce} | Org: {organization_id} | User: {user_id}"
        )

        message_to_sign = (
            f"{domain} wants you to sign in with your Ethereum account:\n"
            f"{wallet_address}\n\n"
            f"{statement}\n\n"
            f"Chain ID: {chain_id}\n"
            f"Nonce: {nonce}\n"
            f"Issued At: {now.isoformat()}\n"
            f"Expiration Time: {expires_at.isoformat()}"
        )

        challenge = {
            "challenge_id": challenge_id,
            "organization_id": organization_id,
            "user_id": user_id,
            "wallet_address": wallet_address.lower(),
            "chain_id": chain_id,
            "nonce": nonce,
            "domain": domain,
            "statement": statement,
            "message_to_sign": message_to_sign,
            "issued_at": now,
            "expires_at": expires_at,
            "consumed_at": None,
        }
        self._challenges[challenge_id] = challenge
        return challenge

    def consume_and_verify_challenge(
        self,
        challenge_id: UUID,
        wallet_address: str,
        signature: str
    ) -> Dict[str, Any]:
        """
        Validates challenge freshness, verifies signature, and invalidates challenge immediately.
        """
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Challenge not found or invalid challenge ID."
            )

        now = datetime.now(timezone.utc)

        # 1. Check expiration
        if now > challenge["expires_at"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Challenge has expired. Please request a fresh challenge."
            )

        # 2. Check single-use guarantee (replay attack block)
        if challenge["consumed_at"] is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Challenge has already been used. Replay attacks are prohibited."
            )

        # 3. Invalidate challenge immediately (fail-closed before signature recovery)
        challenge["consumed_at"] = now

        # 4. Check requested wallet matches challenge wallet
        if wallet_address.lower() != challenge["wallet_address"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wallet address does not match the challenge address."
            )

        # 5. Recover signer address from signature
        try:
            signable_msg = encode_defunct(text=challenge["message_to_sign"])
            recovered_address = Account.recover_message(signable_msg, signature=signature)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Cryptographic signature verification failed: {str(e)}"
            )

        if recovered_address.lower() != wallet_address.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Signature signer ({recovered_address}) does not match claimed wallet ({wallet_address})."
            )

        return challenge


challenge_manager = WalletChallengeManager()


def create_session_token(
    user_id: UUID,
    org_id: UUID,
    roles: List[str],
    wallet_address: str
) -> str:
    """Generate a tamper-proof signed session token."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=SESSION_EXPIRY_HOURS)
    payload = {
        "user_id": str(user_id),
        "org_id": str(org_id),
        "roles": roles,
        "wallet_address": wallet_address.lower(),
        "exp": exp.timestamp()
    }
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    signature = hmac.new(SECRET_KEY, encoded_payload.encode(), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"


def decode_session_token(token: str) -> Dict[str, Any]:
    """Validate token signature and expiration, returning parsed payload."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            raise ValueError("Malformed token format")
        encoded_payload, signature = parts
        expected_sig = hmac.new(SECRET_KEY, encoded_payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid token signature")

        payload_bytes = base64.urlsafe_b64decode(encoded_payload.encode())
        payload = json.loads(payload_bytes.decode())

        # Expiry check
        if datetime.now(timezone.utc).timestamp() > payload["exp"]:
            raise ValueError("Token has expired")

        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authorization token: {str(e)}"
        )


def get_current_caller(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> CallerContext:
    """FastAPI Dependency: Authenticates Bearer token and returns active CallerContext."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header."
        )
    token = credentials.credentials
    payload = decode_session_token(token)
    
    return CallerContext(
        user_id=UUID(payload["user_id"]),
        org_id=UUID(payload["org_id"]),
        roles=payload.get("roles", []),
        is_active=True
    )

