# TR-003: Artifact Store

## Priority
P0

## Tool Type
artifact-store

## Spec Trace
Detailed Specification: `18.3 Artifact Store`, `7. Artifact Layout`

## Story
As an operator, I want every workflow run to write durable local artifacts so
that inputs, events, reports, drafts, approvals, and summaries can be audited
and reviewed later.

## Scope Boundaries
### In
- Timestamped run folder creation.
- Stable run ID generation.
- `manifest.json` writing.
- Append-only `events.jsonl` writing.
- Creation of `inputs/`, `reports/`, `drafts/`, and `approvals/` directories.
- Safe path handling under the configured artifact root.
- Basic artifact write failure behavior.

### Out
- Database persistence.
- Cloud storage.
- Obsidian-specific publishing behavior.
- Report content generation.
- Approval decision semantics.
- Linear comment posting.

## Acceptance Criteria
- [ ] Run IDs are stable and collision-resistant.
- [ ] Manifest is written.
- [ ] Events are appended to `events.jsonl`.
- [ ] Inputs, reports, drafts, and approvals directories are created.
- [ ] Artifact writes fail closed before any external write-back can occur.

## Definition of Ready
- [ ] Story is clearly written.
- [ ] Acceptance criteria are defined.
- [ ] Dependencies are identified.
- [ ] Test strategy is understood.
- [ ] UX/Architecture reviewed, if applicable.
- [ ] Security impact reviewed, if applicable.
- [ ] Documentation impact reviewed.
- [ ] Approved by project approver.

## Definition of Done
- [ ] Code complete.
- [ ] Tests written and passing.
- [ ] Documentation updated.
- [ ] Security validation complete, if applicable.
- [ ] Observability/logging updated, if applicable.
- [ ] Demonstrated in the appropriate local environment.
- [ ] Comprehensive code review complete.
- [ ] Validated by project approver.

## Dependencies
- Blocks: TR-006, TR-007, TR-008, TR-010, TR-012
- Blocked By: TR-001

## Dependency Rationale
Reports, drafts, approval records, summaries, and demo evidence all depend on a
durable run artifact structure.

## Validation Notes
- Unit-test run folder path generation.
- Unit-test manifest writing.
- Unit-test event append behavior.
- Simulate artifact write failure and confirm no downstream write-back action is
  allowed.
- Verify generated paths stay under the configured artifact root.

## Notes
- Risks: path traversal, partial artifacts, non-replayable run evidence.
- Open Questions: none.

