# CARESEAL — PHASE EXECUTION & SPONSOR TRACKER

**Current Phase:** Phase 02 (Vertical Slice 1 Complete & Tested) | **Next Step:** Claude Arc Studio Escrow (Phase 01) / Antigravity ML Screening (Phase 02 Slice 2)  
**Hackathon Event:** ETHGlobal Mumbai 2026 | **Build Timestamp:** 05 November 2026

---

## 1. Phase Status Overview

| Phase | Description | Owner | Status | Exit Verification Criteria |
|---|---|---|---|---|
| **Phase 00** | Monorepo scaffolding, baseline services, Foundry, Next.js, FastAPI | Antigravity | **COMPLETE** | Tools verified on Windows; baseline compilation passed. |
| **Phase 00.5** | Foundation hardening, Next 15.5.29, PostgreSQL tenant isolation RLS, security docs | Antigravity | **COMPLETE** | Live disposable DB tenant isolation verified (5/5 assertions); Next.js clean build. |
| **Phase 01** | Arc Studio escrow implementation, USDC deposit logic, frozen payee, cap, refunds | Claude + Human | **READY (HOLD)** | **BLOCKED:** Human / Claude must initiate project in **Arc Studio** (`https://studio.arc.io/`) to guarantee prize eligibility. |
| **Phase 02 (Slice 1)** | Hospital wallet challenge/verify, authenticated claim submission, itemized charges, duplicate engine, CRE envelope | Antigravity | **COMPLETE & TESTED** | 22/22 Pytest passing; real EIP-191 signature recovery, replay rejection, cross-tenant 403, 409 duplicate rejection. |
| **Phase 02 (Slice 2)** | Synthetic tariff pricing benchmarks & IsolationForest explainable anomaly flags | Antigravity | **QUEUED** | Scikit-learn outlier scoring on synthetic claim charges. |
| **Phase 03** | Chainlink CRE workflow & CLI simulation | Claude | **QUEUED** | Captured `cre simulate` CLI log reading external verification API and Arc chain. |
| **Phase 04** | World ID Agent Pass human-presence review gate | Antigravity | **QUEUED** | Server-side verification; verified path succeeds, denied/cancelled path blocks action. |
| **Phase 05** | "Proof in Motion" frontend, investigation scrollytelling, review vault, security lab | Antigravity | **QUEUED** | Responsive accessible Next.js UI; confirmed chain state reflection; no fake animations. |
| **Phase 06** | Codex red-team review, negative tests, sponsor evidence dossiers, demo recording | Codex + Human | **QUEUED** | Full invariant tests, 3-minute video, real transaction explorer hashes. |

---

## 2. API Endpoints & Real Security Posture

| Endpoint / Subsystem | Current State | Invariant & Implementation Status |
| :--- | :--- | :--- |
| `POST /auth/wallet/challenge` | **IMPLEMENTED & TESTED** | Single-use expiring EIP-191 challenge with 5-minute timeout. |
| `POST /auth/wallet/verify` | **IMPLEMENTED & TESTED** | Cryptographic signature recovery (`eth_account`), challenge invalidated immediately (replay protected). |
| `POST /claims` | **IMPLEMENTED & TESTED** | Authenticated hospital claim submission with itemized charges, synthetic calculation, duplicate detection, and audit logging. |
| `GET /claims/{id}` | **IMPLEMENTED & TESTED** | Strict tenant isolation. Hospital members cannot read other hospitals' claims (403 Forbidden). |
| `GET /integrations/cre/claims/{id}/verification` | **IMPLEMENTED & TESTED** | Privacy-preserving redacted verification envelope. ZERO patient PHI. 404 for unknown claims. |
| `POST /auth/world/verify` | **UNIMPLEMENTED (HTTP 501)** | Strictly fail-closed HTTP 501 stub. Deferred to Phase 04. No fake passes or mock tokens. |

---

## 3. Real Verification & Test Pass Log

```text
1. FASTAPI PYTEST SUITE (Python 3.12.10):
   22 passed in 0.62s:
   - test_auth.py: 4 tests (unknown org 404, non-member 403, malformed wallet 422, unknown challenge 400).
   - test_claims_e2e.py: 3 tests (replay attack protection, forged signature rejection, end-to-end claim submission & verification).
   - test_cre.py: 2 tests (non-existent claim returns 404, non-UUID returns 422).
   - test_health.py: 2 tests (health probe succeeds, zero environment leaks).
   - test_org_isolation.py: 5 tests (cross-tenant read/write denial, disabled user denial, reviewer boundary).
   - test_unit.py: 4 tests (pure unit tests for health, challenge, CRE, and World ID 501).
   - test_world.py: 2 tests (fails closed with 501, payload schema validation).

2. NEXT.JS FRONTEND BUILD (Node v24.13.1, Next 15.5.29):
   - TypeScript tsc --noEmit: 0 errors.
   - Next.js production build: 4/4 static pages generated cleanly.

3. DISPOSABLE POSTGRESQL 16 LIVE TENANT ISOLATION:
   - All 5 assertions passed (Hospital A reads Hospital A, Hospital B hidden, UPDATE 0 on cross-tenant, INSERT RLS check violation, anon denied).
```
