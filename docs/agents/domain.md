# Domain Docs

## Entry point and authority

Start at `spec/README.md` and read the authoritative documents relevant
to the task.

Glossaries record terminology; ADRs record decision rationale. They
supplement the existing documentation and must not duplicate or override
its designated authorities.

## Layout

This repository uses a single-context layout:

- `GLOSSARY.md` at the repository root.
- ADRs under `docs/adr/`.

Read the glossary and ADRs relevant to the task when they exist.
If they are absent, proceed silently. Create domain documentation lazily
when terminology or decisions are resolved, subject to `AGENTS.md`.

## Vocabulary

Use the glossary's established terms. When no glossary exists, use
the vocabulary in the relevant authoritative specification.

If a needed concept is missing, reconsider whether a new term is necessary;
record a genuine terminology gap for the domain-modeling workflow.

## Conflicts

Surface conflicts with specifications or ADRs explicitly. Resolve them
through the repository's authority and approval workflow before changing
the current baseline.
