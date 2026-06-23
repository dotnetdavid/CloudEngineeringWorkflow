# TR-002: Linear Read Adapter

## Priority
P0

## Tool Type
adapter

## Spec Trace
Detailed Specification: `18.2 Linear Read Adapter`, `11.1 Read Behavior`

## Story
As an operator, I want the workflow to read issues from the configured Linear
project so that readiness analysis is based on real sandbox issue data.

## Scope Boundaries
### In
- Read issues by configured Linear project ID.
- Normalize Linear issue fields into internal issue objects.
- Preserve issue identifier, title, description, URL, priority, estimate,
  status, labels, project, team, and timestamps when available.
- Provide mocked adapter behavior for tests.
- Fail closed on Linear read errors.

### Out
- Linear comment creation.
- Linear status, priority, assignment, label, project, or description mutation.
- Workspace-wide reads unless explicitly requested by config later.
- Jira support.
- Multi-workspace Linear routing.

## Acceptance Criteria
- [ ] Adapter reads issues by project ID.
- [ ] Adapter returns normalized issue objects.
- [ ] Adapter can run against mocked data in tests.
- [ ] Adapter does not perform write operations.
- [ ] Linear read failures are surfaced without generating write-back actions.

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
- Blocks: TR-006, TR-010
- Blocked By: TR-001

## Dependency Rationale
The adapter needs the project scaffold and config loader. Reports and summaries
need normalized issue data from this adapter.

## Validation Notes
- Unit-test normalized issue object creation from mocked Linear payloads.
- Unit-test read failure behavior.
- Review implementation to confirm it uses read-only Linear operations.
- Confirm no write-back code is introduced in this story.

## Notes
- Risks: accidentally coupling analysis to raw Linear payloads, accidentally
  adding mutation behavior too early.
- Open Questions: none.

