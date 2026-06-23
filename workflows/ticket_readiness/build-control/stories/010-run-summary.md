# TR-010: Run Summary

## Priority
P0

## Tool Type
observability

## Spec Trace
Detailed Specification: `18.10 Run Summary`, `14. Observability`

## Story
As an operator, I want a human-readable run summary so that readiness results,
risks, errors, and write-back decisions can be reviewed after each run.

## Scope Boundaries
### In
- Generate `summary.md` for each run.
- Group issues by readiness status.
- Group issues by risk level.
- List errors and skipped write-backs.
- Link reports and drafts.
- Include counts suitable for quick review.

### Out
- Web dashboard.
- Metrics backend.
- Alerting.
- Hosted observability stack.
- Replacing detailed per-issue reports.

## Acceptance Criteria
- [ ] Summary groups issues by readiness status.
- [ ] Summary groups issues by risk level.
- [ ] Summary lists errors and skipped write-backs.
- [ ] Summary links reports and drafts.
- [ ] Summary is written even for partial runs when enough state exists.

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
- Blocks: TR-012
- Blocked By: TR-002, TR-003, TR-004, TR-005, TR-006, TR-007, TR-008, TR-009

## Dependency Rationale
The summary needs issue input, artifact paths, findings, reports, drafts,
approval outcomes, and write-back results to produce useful run visibility.

## Validation Notes
- Unit-test summary grouping by readiness status and risk level.
- Unit-test summary links to generated reports and drafts.
- Unit-test partial-run summary behavior.
- Manual review summary from seeded sandbox fixture run.

## Notes
- Risks: summary too thin to be useful, summary too noisy to scan.
- Open Questions: none.

