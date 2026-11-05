# CARESEAL — SECURITY POLICY & AUDIT SPECIFICATION

**Version:** 1.0.0 | **Updated:** 05 November 2026 (Phase 00.5)  
**Classification:** Hackathon MVP (Synthetic Data & Testnet Value Only)

---

## 1. Core Security Invariants

### 1.1 Synthetic Data & Privacy Firewall
- **Zero Real Protected Health Information (PHI):** The system strictly forbids real patient names, government IDs (e.g., Aadhaar, SSN), authentic hospital invoice numbers, or real clinical records.
- **Off-Chain Isolation:** No medical documentation or clinical diagnoses are ever written to the blockchain.
- **Confidential Commitments:** Claims are anchored on-chain using a cryptographically salted `claimCommitment = keccak256(canonicalId, hospitalPayee, cap, salt)` where salt retains high entropy.

### 1.2 Database & Supabase Row Level Security (RLS)
- **Deny-by-Default:** All 13 tables in the `public` schema have Row Level Security enabled (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`).
- **Restricted Public Grants:** All default permissions for untrusted roles (`anon`, `authenticated`) are explicitly revoked (`REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated`).
- **Service Role Reality:** Supabase / PostgreSQL `service_role` credentials bypass RLS completely. The backend application (FastAPI) must NEVER assume RLS protects queries made via service credentials; organizational isolation and tenant boundaries MUST be enforced in Python code.

### 1.3 Authentication & Authorization Fail-Closed Invariant
- **No Insecure Stubs:** Unimplemented authentication or proof verification endpoints MUST fail closed and return `501 Not Implemented`. Under no circumstances may an endpoint return a synthetic `200 OK` or spoofed JWT token.
- **Multi-Factor Independence:**
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

Following `npm audit`, 29 transitive vulnerabilities were identified in the frontend workspace. Their root causes and mitigations are documented below:

| Package | Source Dependency | Risk Summary | Mitigation & Residual Risk Decision |
|---|---|---|---|
| `decode-uri-component` | `@walletconnect/utils` | Denial of service via malformed percent-encoding | **FIXED:** Pinned `0.5.1` via `package.json` overrides. |
| `ws` | `@walletconnect/utils`, `@reown/appkit` | Uninitialized memory disclosure & small fragment DoS | **FIXED:** Pinned `8.22.1` via `package.json` overrides. |
| `postcss` / `next` | `next@14.2.35` | Source map path traversal during development | **DOCUMENTED RESIDUAL:** Running `npm audit fix --force` would force Next.js 16 and Wagmi 3, breaking React 18 and RainbowKit v2 compatibility. CareSeal does not expose Next.js dev server to public untrusted networks. |
| `deepmerge` | `@vanilla-extract/css` | Prototype pollution in nested merge | **DOCUMENTED RESIDUAL:** Subdependency of RainbowKit UI styling. RainbowKit does not parse attacker-controlled objects into vanilla-extract CSS. |
| `uuid` | `@metamask/sdk` | Missing buffer bounds check in v3/v5/v6 | **DOCUMENTED RESIDUAL:** Only affects custom buffer allocation in legacy UUID methods; MetaMask SDK internally uses standard v4 generation. |
| `zod` | `@coinbase/cdp-sdk` | Oversized constrained collection memory exhaustion | **DOCUMENTED RESIDUAL:** Subdependency of wagmi Coinbase connector. Coinbase micropayments are excluded via Webpack fallback in `next.config.mjs`. |

---

## 3. Threat Matrix & Mitigations

| Threat | Attack Vector | Mitigation |
|---|---|---|
| **Collusive Hospital Claim** | Compromised hospital issues inflated bill | Duplicate invoice fingerprint check + IsolationForest anomaly flags + mandatory independent medical and financial reviewer approvals. |
| **Escrow Drain / Payee Redirection** | Attacker attempts to change recipient address | Payee address is immutable in Solidity contract storage upon `registerClaim`. |
| **Overfunding Exploitation** | Donor sends funds exceeding the registered cap | Contract strictly requires `raised + amount <= maxAmountTokenUnits`; reverts otherwise. |
| **Reentrancy on Settle/Refund** | Malicious token contract attempts reentrancy | Follows Checks-Effects-Interactions pattern; status updated before external call; OpenZeppelin `ReentrancyGuard`. |
| **Service-Role Data Leakage** | Backend query leaks claims across hospitals | Python API explicitly enforces `WHERE hospital_id = current_user.org_id` in application logic. |
| **World ID Proof Replay** | Attacker replays intercepted ZKP proof | Backend verifies nullifier hash uniqueness in `audit_events` and enforces 5-minute single-use challenge nonces. |

