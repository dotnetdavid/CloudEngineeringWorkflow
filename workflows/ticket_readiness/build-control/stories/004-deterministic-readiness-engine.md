# TR-004: Deterministic Readiness Engine

## Priority
P0

## Tool Type
workflow

## Spec Trace
Detailed Specification: `18.4 Deterministic Readiness Engine`, `8. Readiness Evaluation`, `9. Deterministic Checks`

## Story
As a reviewer, I want deterministic readiness checks to identify explicit
ticket signals so that required fields, risk flags, and obvious gaps are caught
before LLM interpretation.

## Scope Boundaries
### In
- Evaluate required readiness dimensions.
- Detect obvious missing title, description, priority, estimate, and acceptance
  criteria signals.
- Detect environment, blast-radius, rollback, validation, dependency, ownership,
  and security signals.
- Detect risk flags from the readiness rubric.
- Produce structured deterministic findings.
- Cover seeded sandbox fixture cases in tests.

### Out
- Final LLM-generated analysis.
- Linear reads.
- Report rendering.
- Draft comments.
- Changing the rubric without updating docs.

## Acceptance Criteria
- [ ] Required dimensions are evaluated.
- [ ] Findings are structured.
- [ ] Fixture issues produce expected obvious findings.
- [ ] Rules are covered by unit tests.
- [ ] Planning-only and documentation-only tickets use lighter requirements.

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
- Blocks: TR-005, TR-006, TR-007, TR-010
- Blocked By: TR-001

## Dependency Rationale
The LLM adapter, report generator, draft generator, and summary all need
structured deterministic findings to avoid relying on model interpretation
alone.

## Validation Notes
- Unit-test each readiness dimension.
- Unit-test high-risk signals for IAM, production, database reboot, broad
  network access, and security group changes.
- Unit-test lower-risk handling for documentation-only and planning-only
  tickets.
- Confirm deterministic findings separate observed evidence from inferred gaps.

## Notes
- Risks: brittle keyword checks, false confidence from rules-only evaluation.
- Open Questions: none.

