# TR-009: Linear Comment Write-Back

## Priority
P0

## Tool Type
integration

## Spec Trace
Detailed Specification: `18.9 Linear Comment Write-Back`, `11.2 Write Behavior`, `11.3 Approval Enforcement`

## Story
As an operator, I want approved draft comments posted to Linear so that reviewed
readiness feedback can be shared where sprint planning work happens.

## Scope Boundaries
### In
- Post approved draft comments to Linear.
- Verify approval record before posting.
- Verify draft hash before posting.
- Record posted comment ID when available.
- Record write-back failures without infinite retry.
- Ensure write-back targets the trusted workflow issue ID.

### Out
- Automatic status changes.
- Priority changes.
- Assignment changes.
- Description rewrites.
- Label mutations.
- Project moves.
- Posting unapproved drafts.
- Retrying indefinitely.

## Acceptance Criteria
- [ ] Only approved drafts are posted.
- [ ] Draft hash must match approval record.
- [ ] Posted comment ID is recorded.
- [ ] Failures are logged without infinite retry.
- [ ] Disallowed Linear mutations are not implemented.

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
- Blocks: TR-010, TR-012
- Blocked By: TR-007, TR-008, TR-011

## Dependency Rationale
Write-back depends on drafts, approval enforcement, and security/redaction
guardrails. Summary and demo work depend on write-back results.

## Validation Notes
- Unit-test that unapproved, rejected, skipped, stale, or malformed approvals do
  not post.
- Unit-test successful mocked comment posting records comment ID.
- Integration-test one approved comment against the sandbox only after review.
- Review implementation to confirm no disallowed Linear mutations exist.

## Notes
- Risks: ticket spam, wrong issue target, accidental mutation beyond comments.
- Open Questions: none.

