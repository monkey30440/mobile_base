# Issue tracker: GitHub

Work requests and implementation tickets live in GitHub Issues for
`monkey30440/mobile_base`. Use the `gh` CLI from this repository.

Tickets reference the authoritative requirements and design documents
identified by `spec/README.md`; they do not replace those documents.

## Operations

- Create: `gh issue create --title "..." --body-file <file>`
- Read: `gh issue view <number> --comments`
- List: `gh issue list --state open`
- Comment: `gh issue comment <number> --body-file <file>`
- Apply labels: `gh issue edit <number> --add-label "..."`
- Remove labels: `gh issue edit <number> --remove-label "..."`
- Close: `gh issue close <number>`

Use UTF-8 files with actual newlines for multiline issue bodies and comments.
Use `docs/agents/triage-labels.md` for triage role mappings.

## Pull requests as a triage surface

PRs as a request surface: no.

## Skill terminology

- “Publish to the issue tracker” means create a GitHub issue.
- “Fetch the relevant ticket” means read the issue and its comments.

## Wayfinding

- The map is one issue labelled `wayfinder:map`.
- Child tickets use `wayfinder:research`, `wayfinder:prototype`,
  `wayfinder:grilling`, or `wayfinder:task`.
- Link children as GitHub sub-issues. If unavailable, use a task list
  in the map and a `Part of #<map>` reference in each child.
- Represent blockers using native issue dependencies. If unavailable,
  use an explicit `Blocked by: #<number>` list.
- Select open, unassigned children whose blockers are all closed.
- Claim a ticket by assigning it to the driving developer.
- Resolve it by recording the outcome, closing the ticket, and linking
  the outcome from the map.
