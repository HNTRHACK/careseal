# CareSeal — Three-Sponsor Eligibility and Evidence Plan
**Reviewed against ETHGlobal Mumbai prize descriptions on 05 Nov 2026.** Official source: https://ethglobal.com/events/mumbai/prizes

> Sponsor selection and awards are not guaranteed. Register the eligible program categories in ETHGlobal; avoid Continuity-only variants unless registered accordingly. Exact final deadlines and team eligibility are controlled by organizers. Keep evidence of work created after the official kickoff.

## Arc — Best Smart Contracts with Advanced Stablecoin Logic, In Arc Studio ($3,000 prize pool)
- **Mandatory:** Arc Studio is the starting point of the relevant submission. Create and retain the shareable Studio project link; judges must see Studio in the demo. Functional frontend + backend, architectural diagram, video/presentation, docs and repository link.
- **Meaningful CareSeal use:** claim-scoped conditional test-USDC escrow; approved claim commitment and immutable hospital recipient; cap; verified NGO deposits; multiple independent review approvals; authorized one-time settlement; donor refunds on well-defined eligible states; pause/guardian safety controls.
- **Implementation:** prompt/build prize-relevant contract/app in Arc Studio first, review its generated Solidity, test/reconcile in Foundry, integrate into existing Next/FastAPI app. If using an existing external contract, confirm sponsor eligibility rather than presuming a late Studio import counts.
- **Evidence:** URL, screen recording of Studio workflow, deployed chain/address, actual test token transactions and Foundry negative tests. Verify native Arc gas accounting versus ERC-20 USDC token decimals instead of assuming they are the same token unit.

## World — World ID Agent Pass ($5,000 prize pool, separate Classic-eligible track)
- **Mandatory:** use official Agent Pass; show request, completion, **server-validated** result and meaningful protected action. Also demonstrate denied/expired/cancelled path where protected action does not happen. Provide concise integration debrief/feedback.
- **Meaningful CareSeal use:** fresh human-presence check before a medical/financial reviewer records a high-stakes approval; bind result to authenticated user, verified org membership, review action, claim ID, nonce and expiration. Check independence of reviewers separately.
- **Limits:** World states proofs currently use mocked identities; don't claim real-world identity/KYB or medical professional validation. A valid human-presence proof does not authorize settlement alone. Keep secrets server-side and use one-time tokens where supported.
- **Evidence:** backend verification response, denial path, audit event proving protected action only happened when all checks passed, WORLD_FEEDBACK.md.
- **API/keys:** configure through official portal; keep backend secrets only server-side, never browser or LLM prompt. Confirm live SDK environment variable names in official docs before populating.

## Chainlink — Best Workflow with CRE ($1,500 prize pool)
- **Mandatory:** a CRE workflow must meaningfully integrate an external API/data source/AI agent with at least one blockchain, and show **successful CRE CLI simulation OR deployed workflow**. Simulation is sufficient for this track; CCIP is a different, harder prize.
- **Meaningful CareSeal use:** CRE calls CareSeal FastAPI `GET /integrations/cre/claims/{id}/verification` (redacted signed assessment) and checks the claim commitment/approval status on Arc. It outputs a deterministic evidence envelope and optionally submits an on-chain update only if the approved contract design allows it. No fabricated oracle truth.
- **Evidence:** workflow source, CRE config, CLI command/output, external API response schema, blockchain read/receipt, reproducible setup steps. Distinguish simulation output from live network attestation.
- **No authorization bypass:** CRE reports evidence; it must not independently satisfy two-reviewer requirement or release escrow unless contract authority is intentionally and safely designed/tested.

## Across all tracks
- Prioritize a single 3-minute CareSeal demo over three disjoint SDK demos.
- Preserve separate source code paths and actual proof of integration.
- No real funds, real medical data, fake transaction hashes, invented partner verifications or unjustified security guarantees.
- Submission should mention sponsor program names explicitly. Multiple sponsorship entries may be possible according to event rules but each sponsor decides its prize.
