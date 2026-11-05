# CLAUDE.md — CareSeal Project Instructions

You are contributing to **CareSeal**, a hackathon prototype for verifiable healthcare claims and conditional medical aid funding. Read `docs/CARESEAL_MASTER_BLUEPRINT.md`, `docs/SPONSOR_PRIZE_PLAN.md`, `docs/AGENT_COORDINATION.md`, and `docs/PHASE_EXECUTION_V2.md` before implementation.

## Your assigned work
- **Primary:** Contract design/security tests in `contracts/`, Arc Studio-driven prize entry, Chainlink CRE in `integrations/cre/`.
- **Secondary:** propose ABI and redacted API interface changes in a written contract only; coordinate API changes with the Antigravity agent. Don't modify `apps/web`, `apps/api`, `supabase` or their lockfiles on your own.
- **Never:** deploy or move money without explicit human authorization, read or output secrets, add production funds, bypass failed tests, fabricate a successful CRE simulation, or claim Arc Studio provenance falsely.

## Key non-negotiable invariants
1. Fixed payee, immutable authorization conditions, cap in integer token units, no double settlement, precise state machine.
2. Different authorized medical and financial reviewers must approve; hospital can't approve itself; World human-presence alone is not role authorization.
3. External CRE report is evidence, not arbitrary payment authority.
4. No unrestricted admin withdrawal or upgrade backdoor; access-control, checks-effects-interactions, SafeERC20, reentrancy protections, emergency stop and donor-controlled refunds.
5. Fuzz/replay/reentrancy/overfund/incorrect-recipient/paused/refund/invariant tests with reproducible output.
6. Only synthetic clinical data and testnet value; document remaining trust assumptions and why a smart contract cannot independently verify surgery.

## Execution protocol
PLAN (files and tests) -> IMPLEMENT in named branch/worktree -> RUN ACTUAL TESTS -> SUMMARY (changed files, commands, failures, unresolved risks) -> REVIEW from Codex -> human merge approval. Stop on high-risk ambiguities. Don't claim complete based on compilation alone.

## Sponsor specific
- **Arc Studio is the starting point** of the prize-relevant workflow. Provide a shareable Studio URL and workflow demo. Foundry separately audits/contracts. If prior code or ineligible assets exist, ask organizer rather than conceal provenance.
- **CRE:** meaningful external API + blockchain interaction, verified CLI simulation or actual deployment.
- **World:** frontend/backend agent owned by Antigravity; Claude may check Solidity role binding and token security design, but does not assume a successful mock proof equals KYC.

## Expected output format
Objective; files touched; actual commands/results; contract invariants; bugs found; open questions; integration instructions; READY/BLOCKED decision. No autopush or automerge.

## Human-first and vibe-code transparency (every phase)
Follow `docs/HUMAN_FIRST_POLICY.md`. After each implementation milestone, classify the work as REVIEWED & TESTED, AI-GENERATED — REVIEW REQUIRED, or BLOCKED / UNSAFE, and include the seven-point milestone report alongside the expected output format above. Code written by Claude counts as AI-generated: only executed tests and independent review can move it to REVIEWED & TESTED. The proposed commit message is a proposal; the human owner decides acceptance and commits.
