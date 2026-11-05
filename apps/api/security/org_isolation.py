"""
CareSeal — Application-Level Multi-Tenant Organization Isolation

SECURITY REALITY:
PostgreSQL service-role credentials and backend connection pools bypass Row Level Security (RLS).
Backend services (FastAPI) MUST enforce organization isolation, tenant boundaries,
and role authorization in application code before executing or returning queries.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID


class TenantAccessDenied(Exception):
    """Raised when an operation violates organization isolation or tenant boundaries."""
    def __init__(self, message: str, code: str = "FORBIDDEN_CROSS_TENANT_ACCESS"):
        super().__init__(message)
        self.message = message
        self.code = code


class CallerContext:
    """Security context of the authenticated caller making the backend request."""
    def __init__(
        self,
        user_id: UUID,
        org_id: UUID,
        roles: List[str],
        is_active: bool = True,
        is_platform_admin: bool = False,
    ):
        self.user_id = user_id
        self.org_id = org_id
        self.roles = roles
        self.is_active = is_active
        self.is_platform_admin = is_platform_admin

    def has_role(self, role: str) -> bool:
        return role in self.roles


def enforce_tenant_isolation(
    resource_hospital_id: UUID,
    caller: CallerContext,
    allowed_roles: Optional[List[str]] = None,
    allow_cross_tenant_reviewers: bool = False,
) -> None:
    """
    Validates that the caller is authorized to access or mutate the resource.
    
    Invariants:
    1. Inactive/disabled users are strictly denied.
    2. Hospital members can only access their own hospital's resources.
    3. Cross-tenant reads are only permitted if explicitly authorized for independent reviewers.
    4. Cross-tenant writes/updates are NEVER permitted for hospital members.
    """
    if not caller.is_active:
        raise TenantAccessDenied(
            f"User {caller.user_id} membership is inactive or disabled.",
            code="INACTIVE_MEMBERSHIP"
        )

    # Cross-tenant check
    if caller.org_id != resource_hospital_id:
        if allow_cross_tenant_reviewers:
            reviewer_roles = {"medical_reviewer", "financial_reviewer", "auditor"}
            if not any(r in reviewer_roles for r in caller.roles):
                raise TenantAccessDenied(
                    f"Cross-tenant access violation: Caller org {caller.org_id} is not authorized "
                    f"to review hospital {resource_hospital_id} data.",
                    code="UNAUTHORIZED_REVIEWER"
                )
        else:
            raise TenantAccessDenied(
                f"Cross-tenant access violation: Caller org {caller.org_id} cannot access or modify "
                f"data belonging to hospital {resource_hospital_id}.",
                code="CROSS_TENANT_ACCESS_DENIED"
            )

    # Role check
    if allowed_roles is not None:
        if not any(r in allowed_roles for r in caller.roles):
            raise TenantAccessDenied(
                f"User {caller.user_id} does not possess required role(s): {allowed_roles}. Caller roles: {caller.roles}",
                code="INSUFFICIENT_ROLE_PERMISSIONS"
            )


class PrivilegedClaimStore:
    """
    In-memory mock / abstraction demonstrating application-level enforcement
    for privileged backend queries (simulating Supabase service-role client).
    """
    def __init__(self):
        self._claims: Dict[UUID, Dict[str, Any]] = {}

    def insert_claim_privileged(self, claim_data: Dict[str, Any], caller: CallerContext) -> Dict[str, Any]:
        """Insert claim using privileged connection while enforcing application-level tenant check."""
        hospital_id = claim_data["hospital_id"]
        enforce_tenant_isolation(
            resource_hospital_id=hospital_id,
            caller=caller,
            allowed_roles=["admin", "issuer"]
        )
        claim_id = claim_data["id"]
        self._claims[claim_id] = dict(claim_data)
        return self._claims[claim_id]

    def read_claim_privileged(self, claim_id: UUID, caller: CallerContext) -> Dict[str, Any]:
        """Read claim using privileged connection while enforcing application-level tenant check."""
        if claim_id not in self._claims:
            raise KeyError(f"Claim {claim_id} not found.")
        claim = self._claims[claim_id]
        
        # Enforce that caller can only view claims belonging to their hospital
        enforce_tenant_isolation(
            resource_hospital_id=claim["hospital_id"],
            caller=caller,
            allow_cross_tenant_reviewers=True
        )
        return dict(claim)

    def update_claim_privileged(
        self,
        claim_id: UUID,
        updates: Dict[str, Any],
        caller: CallerContext
    ) -> Dict[str, Any]:
        """Update claim using privileged connection while enforcing application-level tenant check."""
        if claim_id not in self._claims:
            raise KeyError(f"Claim {claim_id} not found.")
        claim = self._claims[claim_id]

        # Hospital A member can NEVER update Hospital B claim
        enforce_tenant_isolation(
            resource_hospital_id=claim["hospital_id"],
            caller=caller,
            allowed_roles=["admin", "issuer"],
            allow_cross_tenant_reviewers=False  # Reviewers cannot modify hospital claim fields
        )

        claim.update(updates)
        return dict(claim)

