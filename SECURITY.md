# CARESEAL — SECURITY POLICY & AUDIT SPECIFICATION

**Version:** 1.1.0 | **Updated:** 05 November 2026 (Phase 00.5 Final Corrections)  
**Classification:** Hackathon MVP (Synthetic Data & Testnet Value Only)

---

## 1. Core Security Invariants

### 1.1 Synthetic Data & Privacy Firewall
- **Zero Real Protected Health Information (PHI):** The system strictly forbids real patient names, government IDs (e.g., Aadhaar, SSN), authentic hospital invoice numbers, or real clinical records.
- **Off-Chain Isolation:** No medical documentation or clinical diagnoses are ever written to the blockchain.
- **Confidential Commitments:** Claims are anchored on-chain using a cryptographically salted `claimCommitment = keccak256(canonicalId, hospitalPayee, cap, salt)` where salt retains high entropy.

### 1.2 Database & Supabase Row Level Security (RLS)
- **Deny-by-Default:** All 13 tables in the `public` schema have Row Level Security enabled (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`).
- **Restricted Public Grants:** All default permissions for untrusted roles (`anon`, `authenticated`) are explicitly revoked by default.
- **Tenant Isolation Policies:** `supabase/migrations/00002_tenant_rls_policies.sql` establishes strict tenant isolation. An authorized member of Hospital A can only read and mutate Hospital A claims; Hospital B claims are completely invisible and immutable to Hospital A users.
- **Service Role Reality & Application-Level Enforcement:** Supabase / PostgreSQL `service_role` credentials bypass RLS completely. The backend application (`apps/api/security/org_isolation.py`) explicitly enforces multi-tenant isolation in Python code (`enforce_tenant_isolation`) before executing or returning privileged queries.

### 1.3 Real Security Posture: Unimplemented Endpoints (Fail-Closed)
- **World ID, CRE, and Wallet Auth are UNIMPLEMENTED:** World ID proof verification, Chainlink CRE workflow orchestration, and cryptographic wallet authentication currently return `HTTP 501 Not Implemented`.
- **Zero Insecure Stubs:** Unimplemented authentication or proof verification endpoints MUST fail closed. Under no circumstances may an endpoint return a synthetic `200 OK` or spoofed token.
- **Multi-Factor Independence (Phase 02/03/04):**
  1. Hospital identity requires cryptographic signing key binding.
  2. Medical Reviewer and Financial Reviewer must belong to distinct organizations, both separate from the issuing hospital.
  3. Sensitive review approval requires a fresh, server-validated World ID Agent Pass zero-knowledge proof.
  4. World ID human presence does not replace organizational KYB or medical credentials.

### 1.4 Smart Contract Privilege Boundaries
- **No Admin Rescue/Sweep:** No administrative account or multisig holds authority to sweep escrowed funds to an arbitrary address.
- **Frozen Payee:** The hospital payee address is permanently immutable once a claim is registered on-chain.
- **Conservation of Value:** At all times, `contract token balance == sum(unsettled deposits) - refunds - settlements`.
- **All-or-Nothing Settlement:** Escrow releases exactly once to the registered hospital payee upon verified milestone attestation.
- **Pull-Based Refunds:** Expired or cancelled claims allow donors to withdraw their contributed balance directly. Double refunds and cross-donor balance claims are mathematically rejected.

### 1.5 Arc Testnet Token & Gas Decimals
- **Gas Accounting:** Arc native gas fees are paid in USDC and accounted internally by the EVM with **18 decimals** (`msg.value`).
- **Application Accounting:** Standard ERC-20 USDC contracts utilize **6 decimals** (1 USDC = 1,000,000 micro-units).
- **Rule:** Never conflate native value transfers (`msg.value`) with ERC-20 token transfers (`SafeERC20.safeTransferFrom`).

---

## 2. Dependency Advisory Investigation & Risk Analysis

Following `npm audit`, frontend dependencies were reviewed and upgraded to a controlled, supported version:

| Package | Status | Risk Summary | Mitigation & Residual Risk Decision |
|---|---|---|---|
| `next` | **UPGRADED to 15.5.29** | Cache key confusion & DoS in older versions | **RESOLVED:** Upgraded from unsupported Next 14 to official security-patched Next `15.5.29`. All critical Next.js CVEs resolved. |
| `decode-uri-component` | **OVERRIDDEN to 0.5.1** | Denial of service via malformed percent-encoding | **FIXED:** Pinned `0.5.1` via `package.json` overrides. |
| `ws` | **OVERRIDDEN to 8.22.1** | Uninitialized memory disclosure & small fragment DoS | **FIXED:** Pinned `8.22.1` via `package.json` overrides. |
| `deepmerge` | **DOCUMENTED RESIDUAL** | Prototype pollution in nested merge | Subdependency of `@vanilla-extract/css` in RainbowKit. Not exposed to untrusted input. |
| `uuid` | **DOCUMENTED RESIDUAL** | Missing buffer bounds check in v3/v5/v6 | Subdependency of MetaMask SDK. Standard v4 generation is unaffected. |
| `zod` | **DOCUMENTED RESIDUAL** | Memory exhaustion in oversized collections | Subdependency of Wagmi connectors. Excluded from runtime build via Webpack fallback in `next.config.mjs`. |

---

## 3. Threat Matrix & Mitigations

| Threat | Attack Vector | Mitigation |
|---|---|---|
| **Collusive Hospital Claim** | Compromised hospital issues inflated bill | Duplicate invoice fingerprint check + IsolationForest anomaly flags + mandatory independent medical and financial reviewer approvals. |
| **Escrow Drain / Payee Redirection** | Attacker attempts to change recipient address | Payee address is immutable in Solidity contract storage upon `registerClaim`. |
| **Overfunding Exploitation** | Donor sends funds exceeding the registered cap | Contract strictly requires `raised + amount <= maxAmountTokenUnits`; reverts otherwise. |
| **Reentrancy on Settle/Refund** | Malicious token contract attempts reentrancy | Follows Checks-Effects-Interactions pattern; status updated before external call; OpenZeppelin `ReentrancyGuard`. |
| **Service-Role Data Leakage** | Backend query leaks claims across hospitals | Python API explicitly enforces tenant isolation in `apps/api/security/org_isolation.py`. |
| **World ID Proof Replay** | Attacker replays intercepted ZKP proof | Backend verifies nullifier hash uniqueness in `audit_events` and enforces 5-minute single-use challenge nonces. |
