# mobile_base Collaboration Policy

## Project source of truth

- Treat `docs/README.md` as the documentation entrypoint and index. Read only the authoritative documents relevant to the task.
- Follow the repository's Single Source of Truth and Current Baseline principles. Keep architecture, requirements, subsystem details, and verification evidence in their designated documents; do not duplicate them here.

## Change workflow

- For feature or behavior-changing work, use the Superpowers `brainstorming` skill when it is available.
- Otherwise, inspect the relevant repository context, clarify the intended outcome when needed, present the intended change or design, and obtain explicit user approval before implementation.
- For staged work governed by the repository-defined authority chain, identify the earliest stage without explicit approval and work only within that stage. Do not produce downstream decisions, specifications, designs, interfaces, implementation plans, or artifacts; complete the current stage, then stop and wait for explicit user approval.
- Keep Reuse Assessment, Architecture, Subsystem Design, Implementation, and Verification within their documented authority boundaries.

## GitNexus

- Use the installed GitNexus capabilities for code exploration, debugging, refactoring, and code changes.
- Before modifying an existing function, class, or method, run impact analysis. Report HIGH or CRITICAL impact before proceeding.
- Use GitNexus-aware rename or refactoring mechanisms when applicable. After code changes, inspect the affected scope and change impact with GitNexus.
- If GitNexus is unavailable, report that dependency impact could not be determined; do not silently guess.

## Engineering principles

- Apply the principles defined in `docs/README.md`: V-Model, Hardware First, MVP First, Progressive Verification, Document Driven Development, Current Baseline Only, Single Source of Truth, Organic Growth, and Avoid Premature Structure.
- Preserve traceability from approved requirements and design through implementation and verification.

## Scope discipline

- Make the smallest change that satisfies the approved requirement, following existing architecture and patterns.
- Do not implement backlog or future functionality without explicit request and approval.
- Do not introduce speculative abstractions, premature structure, or unrelated refactoring.

## Build and verification

- Use the repository's existing Docker/container workflow for builds, tests, and validation.
- Use relevant existing package-level build and test mechanisms; do not invent parallel validation infrastructure.
- Run the available software verification relevant to the change. Where hardware is involved, follow the documented hardware verification procedures.

## Completion reporting

- Distinguish clearly between implemented, software-validated, and hardware-validated work.
- Never equate implementation with full verification or claim Feature Freeze unless the documented hardware verification requirements are complete.
- If validation could not be run, state exactly what remains unverified.
