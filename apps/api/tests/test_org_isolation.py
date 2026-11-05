"""
Tests for Application-Level Organization Isolation and Tenant Boundaries.

Demonstrates:
1. Authorized member of Hospital A can read and write Hospital A data.
2. Authorized member of Hospital A CANNOT read Hospital B data.
3. Authorized member of Hospital A CANNOT change Hospital B data.
4. Unauthorized / disabled users are strictly denied.
5. Privileged backend queries enforce tenant boundaries despite service-role privileges.
"""

import pytest
from uuid import uuid4
from apps.api.security.org_isolation import (
    CallerContext,
    TenantAccessDenied,
    enforce_tenant_isolation,
    PrivilegedClaimStore,
)


@pytest.fixture
def hospital_a_id():
    return uuid4()


@pytest.fixture
def hospital_b_id():
    return uuid4()


@pytest.fixture
def member_hospital_a(hospital_a_id):
    return CallerContext(
        user_id=uuid4(),
        org_id=hospital_a_id,
        roles=["issuer"],
        is_active=True
    )


@pytest.fixture
def member_hospital_b(hospital_b_id):
    return CallerContext(
        user_id=uuid4(),
        org_id=hospital_b_id,
        roles=["issuer"],
        is_active=True
    )


@pytest.fixture
def disabled_member_hospital_a(hospital_a_id):
    return CallerContext(
        user_id=uuid4(),
        org_id=hospital_a_id,
        roles=["issuer"],
        is_active=False
    )


@pytest.fixture
def independent_reviewer():
    return CallerContext(
        user_id=uuid4(),
        org_id=uuid4(),
        roles=["medical_reviewer"],
        is_active=True
    )


def test_hospital_a_member_can_access_hospital_a_data(hospital_a_id, member_hospital_a):
    """Authorized member of Hospital A can access Hospital A data."""
    store = PrivilegedClaimStore()
    claim_id = uuid4()
    
    # Insert claim for Hospital A
    claim = store.insert_claim_privileged(
        claim_data={
            "id": claim_id,
            "hospital_id": hospital_a_id,
            "procedure_code": "PROC-001",
            "estimate_inr_paise": 5000000,
        },
        caller=member_hospital_a
    )
    assert claim["id"] == claim_id
    assert claim["hospital_id"] == hospital_a_id

    # Read claim for Hospital A
    read_claim = store.read_claim_privileged(claim_id, caller=member_hospital_a)
    assert read_claim["id"] == claim_id
    assert read_claim["estimate_inr_paise"] == 5000000

    # Update claim for Hospital A
    updated_claim = store.update_claim_privileged(
        claim_id=claim_id,
        updates={"estimate_inr_paise": 6000000},
        caller=member_hospital_a
    )
    assert updated_claim["estimate_inr_paise"] == 6000000


def test_hospital_a_member_cannot_read_hospital_b_data(hospital_a_id, hospital_b_id, member_hospital_a, member_hospital_b):
    """Authorized member of Hospital A CANNOT read Hospital B data."""
    store = PrivilegedClaimStore()
    claim_b_id = uuid4()

    # Hospital B member inserts claim B
    store.insert_claim_privileged(
        claim_data={
            "id": claim_b_id,
            "hospital_id": hospital_b_id,
            "procedure_code": "PROC-002",
            "estimate_inr_paise": 7500000,
        },
        caller=member_hospital_b
    )

    # Hospital A member attempts to read Hospital B claim -> MUST FAIL
    with pytest.raises(TenantAccessDenied) as exc_info:
        store.read_claim_privileged(claim_b_id, caller=member_hospital_a)
    
    assert "Cross-tenant access violation" in str(exc_info.value)
    assert exc_info.value.code == "UNAUTHORIZED_REVIEWER"


def test_hospital_a_member_cannot_change_hospital_b_data(hospital_a_id, hospital_b_id, member_hospital_a, member_hospital_b):
    """Authorized member of Hospital A CANNOT modify Hospital B data."""
    store = PrivilegedClaimStore()
    claim_b_id = uuid4()

    # Hospital B member inserts claim B
    store.insert_claim_privileged(
        claim_data={
            "id": claim_b_id,
            "hospital_id": hospital_b_id,
            "procedure_code": "PROC-002",
            "estimate_inr_paise": 7500000,
        },
        caller=member_hospital_b
    )

    # Hospital A member attempts to modify Hospital B claim -> MUST FAIL
    with pytest.raises(TenantAccessDenied) as exc_info:
        store.update_claim_privileged(
            claim_id=claim_b_id,
            updates={"estimate_inr_paise": 100},
            caller=member_hospital_a
        )
    
    assert "Cross-tenant access violation" in str(exc_info.value)
    assert exc_info.value.code == "CROSS_TENANT_ACCESS_DENIED"

    # Confirm claim B was NOT modified
    unmodified_claim = store.read_claim_privileged(claim_b_id, caller=member_hospital_b)
    assert unmodified_claim["estimate_inr_paise"] == 7500000


def test_unauthorized_and_disabled_users_are_denied(hospital_a_id, disabled_member_hospital_a):
    """Unauthorized and disabled members are strictly denied."""
    store = PrivilegedClaimStore()
    claim_id = uuid4()

    # Disabled member attempting to insert claim -> MUST FAIL
    with pytest.raises(TenantAccessDenied) as exc_info:
        store.insert_claim_privileged(
            claim_data={
                "id": claim_id,
                "hospital_id": hospital_a_id,
                "procedure_code": "PROC-001",
                "estimate_inr_paise": 5000000,
            },
            caller=disabled_member_hospital_a
        )
    assert "inactive or disabled" in str(exc_info.value)
    assert exc_info.value.code == "INACTIVE_MEMBERSHIP"


def test_independent_reviewer_can_read_but_cannot_modify_hospital_claims(
    hospital_a_id,
    member_hospital_a,
    independent_reviewer
):
    """Independent reviewer can read Hospital A claim, but CANNOT mutate hospital claim fields."""
    store = PrivilegedClaimStore()
    claim_a_id = uuid4()

    # Hospital A inserts claim
    store.insert_claim_privileged(
        claim_data={
            "id": claim_a_id,
            "hospital_id": hospital_a_id,
            "procedure_code": "PROC-001",
            "estimate_inr_paise": 5000000,
        },
        caller=member_hospital_a
    )

    # Independent reviewer reads claim -> ALLOWED
    claim = store.read_claim_privileged(claim_a_id, caller=independent_reviewer)
    assert claim["id"] == claim_a_id

    # Independent reviewer attempts to modify claim fields -> MUST FAIL
    with pytest.raises(TenantAccessDenied) as exc_info:
        store.update_claim_privileged(
            claim_id=claim_a_id,
            updates={"estimate_inr_paise": 100},
            caller=independent_reviewer
        )
    assert "Cross-tenant access violation" in str(exc_info.value)

