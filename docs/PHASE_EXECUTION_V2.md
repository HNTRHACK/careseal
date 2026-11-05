# CareSeal — Phase Plan V2: Arc + CRE + World + Claude

**Use the actual ETHGlobal submission cutoff, not a presumed full 48h.** Preserve kickoff provenance. Keep one coherent product rather than three sponsor mini-apps.

## First: Phase 00.5 hardening (blocking)
- Confirm kickoff/Classic eligibility and whether any existing Phase 00 project-specific files were created prematurely. Record provenance; do not hide work.
- Upgrade Next.js 14.2.35 to a supported patched version compatible with RainbowKit, Wagmi, Viem and React; run vulnerability check and production build.
- Check `next.config.mjs` for workaround externals/aliases masking unresolved dependency problems; document exactly why any fallback exists.
- Confirm AGENTS.md/ARCHITECTURE.md/SECURITY.md/CONTRACT_SPEC.md/PHASE_STATUS.md actually exist; initial report lacked several.
- Validate PostgreSQL migration and cross-org RLS under real test roles in disposable database; no reliance on backend service-role alone.
- Current `/auth` endpoints return 501: fail closed, and don't call them 'implemented auth'.
- Confirm chain RPC, token contract, decimals, native gas vs ERC20 accounting with official Arc references.
- Re-run Foundry, pytest, frontend build, secret scan. Avoid automatic commits and deployments.

## Phase 01: Arc Studio and secure escrow (Claude / human)
Start relevant contract/app work IN Arc Studio with shareable URL. Implement minimum claim cap + fixed payee + test USDC deposit + approvals + settlement + refund, with Foundry tests on reviewed contract implementation. Human owns deployer key. Get one actual successful testnet escrow and one contract-level rejected attack before adding features.

## Phase 02: Claims backend (Antigravity)
Implement signing authenticity, canonical invoice identity and duplicate block, private claim docs, two independent reviewers, cost plausibility flags trained on synthetic pricing data, bounded screening latencies. No fake real hospital pricing. Test org isolation and denied roles.

## Phase 03: CRE workflow (Claude)
In `integrations/cre` build a real/simulated CRE CLI workflow consuming redacted `ClaimVerificationEnvelope` API plus Arc blockchain state. Show successful simulated result and record command and output. No claim of deployment unless live.

## Phase 04: World approval gate (Antigravity)
Protect sensitive action `POST /claims/{id}/reviews`. Bind successful server-validated World result with existing reviewer authentication, org membership, nonce, claim/action and freshness. Show denied/expired path blocks the POST. Maintain immutable append-only audit events. Mock identities are not production verification.

## Phase 05: Frontend + integration (Antigravity)
Keep original Proof in Motion: editorial typographic landing, one-shot Flow invoice video only if eligible, annotated claims, review panel, funding vault, security lab. Show confirmed chain state, not fake animation. No bento/template visuals. Test mobile and reduced motion.

## Phase 06: independent review + submission (Codex + human)
Codex reviews Solidity and sensitive authorization paths on separate branch. Run full negative tests and trace escrow balances. Produce precise three sponsor evidence bundles, README, architecture diagram, actual hashes, time-stamped clips and an under-4-minute integrated demo.

## Fallback decision ladder
1. Core escrow + one actual settlement and attack test must work.
2. Arc Studio evidence is required for Arc target; if cannot qualify, disclose and avoid mislabeling.
3. CRE successful CLI simulation is a low-overhead target.
4. World successful + denied protection is independent and meaningful.
5. Reduce ML and visual complexity rather than cutting core security.
6. No guarantees of winning or of production-grade financial/clinical security.
