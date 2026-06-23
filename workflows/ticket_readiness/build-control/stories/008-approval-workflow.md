# TR-008: Approval Workflow

## Priority
P0

## Tool Type
security

## Spec Trace
Detailed Specification: `18.8 Approval Workflow`, `7.6 Approval Contract`, `11.3 Approval Enforcement`

## Story
As an approver, I want manual file-based approval records so that Linear
write-back is deliberate, auditable, and blocked when approval is missing or
stale.

## Scope Boundaries
### In
- Approval JSON record format.
- Manual approve, reject, and skip decisions.
- Draft path and draft SHA-256 validation.
- Approval record validation command or mode.
- Missing, malformed, rejected, skipped, stale, or mismatched approval handling.
- Documentation for manual approval editing.

### Out
- Interactive approval UI.
- Automatic approval.
- CLI command that silently creates approvals without operator review.
- Posting comments to Linear.
- Approval of status changes or issue rewrites.

## Acceptance Criteria
- [ ] Workflow documents how an operator manually approves, rejects, or skips a
  draft by writing an approval JSON record.
- [ ] Workflow can validate manually edited approval records.
- [ ] Approval records include draft hash.
- [ ] Changed drafts require reapproval.
- [ ] Missing approvals block write-back.

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
- Blocks: TR-009, TR-010, TR-012
- Blocked By: TR-003, TR-007

## Dependency Rationale
Approval records need artifact storage and draft hashes. Write-back must wait
for approval enforcement.

## Validation Notes
- Unit-test approved, rejected, skipped, malformed, missing, stale hash, and
  issue-ID mismatch approval records.
- Confirm write-back is blocked unless approval is valid and current.
- Review docs for manual approval instructions.

## Notes
- Risks: accidental ticket spam, stale approvals, mismatched issue IDs.
- Open Questions: none.

