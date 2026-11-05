# CARESEAL — PHASE EXECUTION & SPONSOR TRACKER

**Current Phase:** Phase 00.5 Completed | **Next Phase:** Phase 01 Queued (Blocked on Arc Studio setup)  
**Hackathon Event:** ETHGlobal Mumbai 2026 | **Build Timestamp:** 05 November 2026

---

## 1. Phase Status Overview

| Phase | Description | Owner | Status | Exit Verification Criteria |
|---|---|---|---|---|
| **Phase 00** | Monorepo scaffolding, baseline services, Foundry, Next.js, FastAPI | Antigravity | **COMPLETE** | Tools verified on Windows; baseline compilation passed. |
| **Phase 00.5** | Foundation hardening, dependency fixes, disposable PostgreSQL RLS testing, typed sponsor interfaces, security docs | Antigravity | **COMPLETE** | 14/14 Pytest passed; Next.js 14.2.35 clean build; live disposable DB RLS verified; SECURITY.md & ARCHITECTURE.md created. |
| **Phase 01** | Arc Studio escrow implementation, USDC deposit logic, frozen payee, cap, refunds | Claude + Human | **READY (HOLD)** | **BLOCKED:** Human / Claude must initiate project in **Arc Studio** (`https://studio.arc.io/`) to guarantee prize eligibility. |
| **Phase 02** | Claims backend, hospital signing, deduplication, synthetic tariffs, ML screening | Antigravity | **QUEUED** | Real EIP-712 / EIP-191 verification, IsolationForest flags, no real patient PHI. |
| **Phase 03** | Chainlink CRE workflow & CLI simulation | Claude | **QUEUED** | Captured `cre simulate` CLI log reading external verification API and Arc chain. |
| **Phase 04** | World ID Agent Pass human-presence review gate | Antigravity | **QUEUED** | Server-side verification; verified path succeeds, denied/cancelled path blocks action. |
| **Phase 05** | "Proof in Motion" frontend, investigation scrollytelling, review vault, security lab | Antigravity | **QUEUED** | Responsive accessible Next.js UI; confirmed chain state reflection; no fake animations. |
| **Phase 06** | Codex red-team review, negative tests, sponsor evidence dossiers, demo recording | Codex + Human | **QUEUED** | Full invariant tests, 3-minute video, real transaction explorer hashes. |

---

## 2. Three Sponsor Track Readiness & Evidence Tracker

### 1. Arc — Advanced Stablecoin Logic IN ARC STUDIO ($3,000)
- **Status:** `UNCONFIRMED` *(Awaiting Human / Claude setup in Arc Studio)*
- **Requirement:** Arc Studio MUST be the origin of the prize-relevant contract/app.
- **Evidence Checklist:**
  - [ ] Shareable Arc Studio project URL created and recorded.
  - [ ] Screen recording of Studio workflow and prompt execution.
  - [ ] Smart contract logic aligned between Studio export and `contracts/src/CareSealEscrow.sol`.
  - [ ] Arc Testnet (`5042002`) contract deployment hash and test USDC faucet transactions.
  - [ ] Foundry negative tests proving overfunding and unauthorized payout reverts.

### 2. World — World ID Agent Pass ($5,000)
- **Status:** `SCAFFOLDED & FAIL-CLOSED` (Ready for Phase 04)
- **Requirement:** Server-validated human presence for sensitive review approval (`POST /claims/{id}/reviews`). Must demonstrate both verified path and denied/expired path.
- **Evidence Checklist:**
  - [x] Typed Pydantic models for zero-knowledge proof payload and single-use challenge nonce.
  - [x] Fail-closed endpoint: `POST /auth/world/verify` returns 501 with zero fake auth stubs.
  - [ ] Phase 04: Server-side proof verification via World Developer Portal API.
  - [ ] Phase 04: Denied/expired proof test demonstrating rejection of review approval.
  - [ ] Phase 04: `docs/WORLD_FEEDBACK.md` integration debrief.

### 3. Chainlink — Best Workflow with CRE ($1,500)
- **Status:** `SCAFFOLDED & FAIL-CLOSED` (Ready for Phase 03)
- **Requirement:** CRE workflow connecting external API with on-chain state, verified via CLI simulation or deployment.
- **Evidence Checklist:**
  - [x] Typed redacted verification envelope: `GET /integrations/cre/claims/{id}/verification`.
  - [x] Zero PHI guarantee in envelope schema.
  - [x] Fail-closed endpoint returns 501 with zero synthetic unverified data.
  - [ ] Phase 03: `integrations/cre/` workflow definition.
  - [ ] Phase 03: Captured `cre simulate` CLI command and stdout transcript.
  - [ ] Phase 03: Reproducible instructions in `integrations/cre/README.md`.

---

## 3. Real Verification & Test Pass Log

```text
1. FOUNDRY CONTRACT TESTS (Solc 0.8.24, Cancun EVM):
   [PASS] test_InitialState() (gas: 30347)
   [PASS] test_RevertWhen_FinancialMethodsCalledInPhase00() (gas: 16207)
   [PASS] test_RevertWhen_ZeroAddressAdmin() (gas: 106891)
   [PASS] test_RevertWhen_ZeroAddressToken() (gas: 106909)
   Result: 4 passed; 0 failed; 0 skipped.

2. FASTAPI PYTEST SUITE (Python 3.12.10):
   14 passed in 0.59s (Auth stubs, CRE envelope, World ID models, health check, unit handlers).

3. NEXT.JS FRONTEND BUILD & TYPE CHECK (Node v24.13.1, Next 14.2.35):
   - TypeScript tsc --noEmit: 0 errors.
   - Next.js production build: 4/4 static pages generated cleanly.

4. DISPOSABLE POSTGRESQL 16 LIVE RLS VERIFICATION:
   - Cluster initialized with initdb on port 54399.
   - Migration 00001_initial_schema.sql executed with 0 errors.
   - All 13 tables verified with rowsecurity = true.
   - Untrusted query under anon role: strictly returned "permission denied".
   - Untrusted query under authenticated role: strictly returned "permission denied".
   - Superuser query under postgres: confirmed service-role bypasses RLS.
```

