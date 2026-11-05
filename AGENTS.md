# CARESEAL AI — AGENT DIRECTIVES & GUARDRAILS

**Role:** Senior Full-Stack Developer & Web3 Security Engineer  
**Canonical Specification:** `docs/CARESEAL_MASTER_BLUEPRINT.md`  
**Database Reference:** `docs/CARESEAL_SCHEMA_DRAFT.sql`  

---

## 1. Core Operating Protocol

For every feature or phase:
```
PLAN -> IMPLEMENT -> TEST -> SHOW RESULTS -> SECURITY REVIEW -> COMMIT
```
- Never alter permissions or security invariants to bypass failing tests.
- Stop and report immediately upon any failed security invariant.
- Never advance to a subsequent phase without explicit user approval.
- Do not auto-commit or push changes without human sign-off.

---

## 2. Invariants & Security Boundaries

### Database Security
1. **Deny-by-Default RLS:** All tables must have Row Level Security enabled. Initial access must be strictly denied until explicitly tested tenant/membership policies are defined.
2. **Service Role Reality:** Service-role credentials bypass RLS completely in PostgreSQL/Supabase. Never assume RLS protects backend queries executed via service keys. The backend API must explicitly enforce organizational isolation, role authorization, and tenant boundaries in code.
3. **Restricted Grants:** Revoke public/unauthenticated permissions (`REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated`).
4. **Synthetic Data Only:** Strict zero-tolerance for real patient records, actual government IDs, or authentic health documents. All data, prices, and references must be synthetic.

### Authentication & Authorization
1. **Nonce-Based Challenges:** Wallet verification requires single-use, cryptographically generated, time-expiring nonces bound to a specific domain and organization.
2. **Identity Binding:** A verified wallet must be cryptographically bound to an authenticated user profile and an active organization membership.
3. **No Insecure Stubs:** No endpoint may return a fake `200 OK` or spoofed authorization token. Unimplemented or incomplete authentication flows must return `501 Not Implemented` or be explicitly deferred.

### Smart Contracts (`CareSealEscrow`)
1. **Phase Scope:** Phase 00 is restricted to compilation and test harness scaffolding. Financial logic (deposits, settlements, refunds) belongs strictly to Phase 01.
2. **Privilege Boundaries:**
   - No administrative account may hold unrestricted escrow withdrawal authority or arbitrary fund-sweep capabilities.
   - Hospital payee address is permanently frozen upon claim registration.
   - Medical and financial approvals must originate from distinct authorized organizations, both separate from the issuing hospital.
3. **Funding Invariants:**
   - Cumulative contributions cannot exceed the registered `maxAmount` cap.
   - Escrow accounting must satisfy exact conservation: `contract balance == sum(unsettled deposits) - refunds - settlements`.
   - Settlement is one-time only and releases exclusively to the frozen hospital payee.

### Arc Testnet Configuration
1. **Network Identity:**
   - Chain ID: `5042002` (Hex: `0x4cef52`)
   - RPC: `https://rpc.testnet.arc.network` / `https://rpc.testnet.arc.io`
   - Currency Symbol: `USDC`
2. **Gas vs. Token Decimals:**
   - Arc native gas is paid in USDC and accounted internally by the EVM with **18 decimals**.
   - Standard ERC-20 USDC application token accounting uses **6 decimals** (1 USDC = 1,000,000 micro-units).
   - Never conflate native value transfers (`msg.value`) with ERC-20 token transfers (`SafeERC20`).
3. **No Mainnet Fallback:** Never configure fallback to Ethereum mainnet or unauthorized public networks.

---

## 3. Frontend & UX Guardrails

- **Aesthetic Thesis:** “Proof in Motion” — tactile paper, editorial typography, hairline rules, authentic forensic annotations.
- **Forbidden Patterns:** Bento grids, dark generic SaaS gradient cards, glassmorphism, glowing neon, uncalibrated AI confidence rings.
- **Palette:** Paper `#EDEBE3`, Ink `#181C1A`, Signal `#FF654A`, Clinical `#A9CFE0`, Verified `#235D4C`.
- **Honesty in UI:** Chain states (`pending`, `confirmed`, `reverted`) must reflect actual RPC receipts. No motion-simulated transaction confirmations.
- **Labels:** Explicitly display `TESTNET`, `SYNTHETIC PATIENT`, `SYNTHETIC BENCHMARK`, `DEMO ONLY`.

