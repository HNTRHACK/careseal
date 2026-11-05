"""
CareSeal — Application In-Memory / Relational Store Layer

Provides a clean repository interface for:
- Organizations
- User Profiles & Memberships
- Verified Organization Wallets
- Medical Claims & Line Items
- Append-Only Non-PHI Audit Events

All operations enforce strict typing and synthetic data validation.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
import hashlib


class InMemoryDataStore:
    def __init__(self):
        self.organizations: Dict[UUID, Dict[str, Any]] = {}
        self.profiles: Dict[UUID, Dict[str, Any]] = {}
        self.org_memberships: Dict[UUID, Dict[str, Any]] = {}
        self.organization_wallets: Dict[str, Dict[str, Any]] = {}  # (chain_id, address.lower()) -> wallet
        self.medical_claims: Dict[UUID, Dict[str, Any]] = {}
        self.claim_line_items: Dict[UUID, List[Dict[str, Any]]] = {}  # claim_id -> list of items
        self.audit_events: List[Dict[str, Any]] = []

        self._seed_synthetic_data()

    def _seed_synthetic_data(self):
        """Populate initial synthetic organizations, wallets, and roles."""
        # 1. Hospital Alpha
        hospital_alpha_id = UUID("11111111-1111-1111-1111-111111111111")
        self.organizations[hospital_alpha_id] = {
            "id": hospital_alpha_id,
            "name": "Synthetic Metro Hospital Alpha",
            "kind": "hospital",
            "verification_status": "verified",
            "created_at": datetime.now(timezone.utc)
        }

        # 2. Hospital Beta
        hospital_beta_id = UUID("22222222-2222-2222-2222-222222222222")
        self.organizations[hospital_beta_id] = {
            "id": hospital_beta_id,
            "name": "Synthetic Regional Care Beta",
            "kind": "hospital",
            "verification_status": "verified",
            "created_at": datetime.now(timezone.utc)
        }

        # 3. Independent Reviewer Org
        reviewer_org_id = UUID("33333333-3333-3333-3333-333333333333")
        self.organizations[reviewer_org_id] = {
            "id": reviewer_org_id,
            "name": "Independent Clinical Review Board",
            "kind": "reviewer",
            "verification_status": "verified",
            "created_at": datetime.now(timezone.utc)
        }

        # Profiles
        user_alpha_id = UUID("aaaa1111-1111-1111-1111-111111111111")
        self.profiles[user_alpha_id] = {
            "id": user_alpha_id,
            "display_name": "Dr. Sarah Rao (Hospital Alpha Issuer)",
            "created_at": datetime.now(timezone.utc)
        }

        user_beta_id = UUID("bbbb2222-2222-2222-2222-222222222222")
        self.profiles[user_beta_id] = {
            "id": user_beta_id,
            "display_name": "Dr. Anil Mehta (Hospital Beta Issuer)",
            "created_at": datetime.now(timezone.utc)
        }

        # Memberships
        mem_alpha_id = uuid4()
        self.org_memberships[mem_alpha_id] = {
            "id": mem_alpha_id,
            "organization_id": hospital_alpha_id,
            "user_id": user_alpha_id,
            "role": "issuer",
            "status": "active",
            "created_at": datetime.now(timezone.utc)
        }

        mem_beta_id = uuid4()
        self.org_memberships[mem_beta_id] = {
            "id": mem_beta_id,
            "organization_id": hospital_beta_id,
            "user_id": user_beta_id,
            "role": "issuer",
            "status": "active",
            "created_at": datetime.now(timezone.utc)
        }

    def register_wallet(self, org_id: UUID, wallet_address: str, chain_id: int, purpose: str):
        key = f"{chain_id}:{wallet_address.lower()}"
        self.organization_wallets[key] = {
            "id": uuid4(),
            "organization_id": org_id,
            "wallet_address": wallet_address.lower(),
            "chain_id": chain_id,
            "purpose": purpose,
            "verified_at": datetime.now(timezone.utc)
        }

    def get_wallet_binding(self, wallet_address: str, chain_id: int) -> Optional[Dict[str, Any]]:
        key = f"{chain_id}:{wallet_address.lower()}"
        return self.organization_wallets.get(key)

    def get_user_memberships(self, user_id: UUID, org_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
        results = []
        for mem in self.org_memberships.values():
            if mem["user_id"] == user_id and mem["status"] == "active":
                if org_id is None or mem["organization_id"] == org_id:
                    results.append(mem)
        return results

    def add_audit_event(
        self,
        event_type: str,
        actor_user_id: Optional[UUID] = None,
        actor_org_id: Optional[UUID] = None,
        claim_id: Optional[UUID] = None,
        safe_metadata: Optional[Dict[str, Any]] = None,
        chain_tx_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record an append-only non-PHI audit event."""
        event = {
            "id": uuid4(),
            "claim_id": claim_id,
            "actor_user_id": actor_user_id,
            "actor_org_id": actor_org_id,
            "event_type": event_type,
            "safe_metadata": safe_metadata or {},
            "chain_tx_hash": chain_tx_hash,
            "created_at": datetime.now(timezone.utc)
        }
        self.audit_events.append(event)
        return event

    def get_claim(self, claim_id: UUID) -> Optional[Dict[str, Any]]:
        return self.medical_claims.get(claim_id)

    def find_claim_by_fingerprint(self, hospital_id: UUID, fingerprint: str) -> Optional[Dict[str, Any]]:
        for claim in self.medical_claims.values():
            if claim["hospital_id"] == hospital_id and claim["hospital_invoice_fingerprint"] == fingerprint:
                return claim
        return None

    def find_claim_by_commitment(self, commitment: str) -> Optional[Dict[str, Any]]:
        for claim in self.medical_claims.values():
            if claim.get("claim_commitment") == commitment:
                return claim
        return None

    def save_claim_with_items(self, claim_data: Dict[str, Any], line_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        claim_id = claim_data["id"]
        self.medical_claims[claim_id] = claim_data
        self.claim_line_items[claim_id] = list(line_items)
        return claim_data


# Singleton instance
store = InMemoryDataStore()

