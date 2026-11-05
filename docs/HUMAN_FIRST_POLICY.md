# CareSeal — Human-First Product & Vibe-Code Transparency Policy

These rules apply to every future phase.

## Humanize the product

- Lead with the patient's medical funding problem, not with technology.
- Explain each feature in terms of the human problem it solves.
- Use understandable language, realistic workflows, and empathetic design.
- Treat donors, patients, hospitals, NGOs, and medical reviewers as real stakeholders with different needs.
- Do not fabricate patient stories, testimonials, verification results, or real-world impact.
- Maintain an original, distinctive brand with restrained, purposeful interactions.

## Mandatory vibe-code detection

After each implementation milestone, explicitly classify the work as:

- **REVIEWED & TESTED:** Functionality is understood and supported by executed tests.
- **AI-GENERATED — REVIEW REQUIRED:** Generated code or integration has not been sufficiently validated.
- **BLOCKED / UNSAFE:** Security flaw, fabricated functionality, unreliable payment logic, or unverified critical dependency.

Immediately flag:

- Hardcoded success responses presented as real.
- Mock data displayed as live production evidence.
- Unsupported claims of security or fraud prevention.
- Complex code without an understandable purpose.
- Generic AI-generated UI patterns and boilerplate.
- Missing access control, incomplete signature verification, or untested financial transactions.
- Untested integrations that merely display sponsor branding.

## Mandatory milestone report

For every milestone, report:

1. What changed and why it matters to a real user.
2. Which parts were AI-generated or AI-assisted.
3. What was independently reviewed and tested.
4. Which parts still qualify as vibe-coded or unverified.
5. Security and usability issues.
6. Required fixes before commit.
7. Proposed commit message.

Never call unfinished code production-ready. Never hide AI assistance or manufacture evidence. The human owner makes final acceptance decisions.

**Build CareSeal as a real, trustworthy product—not just a visually impressive hackathon demonstration.**
