# CareSeal — AI Agent Collaboration Protocol

## Ownership, not free-for-all editing

| Owner | Owns | May review | Must NOT modify without agreement |
|---|---|---|---|
| **Claude** | `contracts/`, `integrations/cre/`, corresponding tests; **Arc Studio integration coordination** | shared ABI proposal, external API schema | `apps/web/`, `apps/api/`, SQL migrations |
| **Antigravity/Gemini** | `apps/web/`, `apps/api/`, `supabase/`, presentation/assets during eligible window | proposed ABI and contract events | `contracts/`, `integrations/cre/` |
| **Codex** | Independent read-only audit, reproduction tests; separate security-review branch for reviewed patches | all code | no direct auto-merge, deployment, wallet operations, or broad refactors |
| **Human owner** | Git merges, secrets, test wallets, release approval, final submission | all architecture and demos | never approve undocumented financial permission changes |
| **ChatGPT** | Architecture reviewer; prompts, phase checklists and debugging guidance | pasted nonsecret output and repository files made accessible | cannot execute operations in local Antigravity/Claude sessions automatically |

**Preferred branching:** `feat/arc-escrow`, `feat/cre-workflow`, `feat/backend-claims`, `feat/world-review-gate`, `feat/web-frontend`, `review/security-gate`. Use distinct Git worktrees if two agents work concurrently. Never let two agents edit the same file at the same time.

## Freeze integration contracts early
1. Define `ClaimCommitment` fields: random non-PII `bytes32 claimId`, fixed token, token integer cap, fixed hospital address, settled flag and role-authorizations. Confirm exact ABI with tests, publish under `packages/abi/` once approved.
2. Define backend `ClaimVerificationEnvelope` as versioned JSON (`claimId`, `issuerSignatureValid`, `duplicateCheck`, `screeningStatus`, `medicalReview`, `financialReview`, `referenceHash`, `issuedAt`, `expiresAt`, `schemaVersion`). No patient identity or diagnosis in the response.
3. Define `WorldReviewGateResult` bound to claim ID, action, reviewer session, organization role, nonce, expiration, verification status and evidence reference; verified World proof does not replace org membership.
4. Financial data: 6-decimal test ERC20 USDC units only after confirmed token address/decimals; do not confuse INR sample estimates, Arc gas accounting or chain-native token transfer with USDC ERC20 amounts.
5. Every API change requires an updated contract and consumer tests; never silently drift schema.

## Merge gate
- Check `git diff`, `git status`, staged files and no secrets; no force pushes.
- `forge build`, `forge test`, fuzz/invariants, API pytest, Next build/lint and basic browser path must pass after integration.
- Run negative tests for forged claim, unauthorized NGO, double approval, World denied proof, replay, overfund, unauthorized payout, refund double-claim and pause/recovery.
- Report exact failures; don't patch by weakening security. Security high-severity finding blocks merge/deploy.
- Record actual testnet explorer links, Studio URL, CRE CLI output and World proof-validation evidence for judges.
- Commit incremental work with accurate messages, no fabricated history. Document AI tool use transparently.

## Security boundaries
No real patient information, no real token value, no wallet seed phrase in any agent context, no unreviewed admin sweep, no direct payable fallback, no confirmation on mere UI state, no inference of medical necessity from ML. A valid hospital signature authenticates the issuer, not claim truth.

## Agent task prompt contract
Every task must state: owner; exact paths allowed; input spec; desired changes; out-of-scope files; security invariants; tests and concrete exit criteria; stop and report on ambiguous requirements. Implementation must never continue to the next phase automatically.
