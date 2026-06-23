# TR-007: Draft Comment Generator

## Priority
P0

## Tool Type
backend

## Spec Trace
Detailed Specification: `18.7 Draft Comment Generator`, `7.5 Draft Comment Contract`

## Story
As an operator, I want draft Linear comments generated from validated analysis
so that I can review proposed ticket feedback before anything is posted.

## Scope Boundaries
### In
- Generate draft comment Markdown files under `drafts/`.
- Include readiness status, short explanation, missing information, grooming
  questions, risk notes, and recommendation.
- Include a generated-by-workflow marker.
- Compute draft hashes for approval validation.
- Ensure drafts are tied to trusted workflow issue IDs.

### Out
- Posting comments to Linear.
- Automatically approving drafts.
- Changing issue status, description, priority, labels, or assignee.
- Generating comments for failed analysis.

## Acceptance Criteria
- [ ] Drafts are written to `drafts/`.
- [ ] Drafts include readiness status, missing information, questions, risks,
  and recommendation.
- [ ] Draft hashes can be computed for approval.
- [ ] Drafts are not generated for invalid analysis output.
- [ ] Draft target issue IDs come from workflow state.

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
- Blocks: TR-008, TR-009, TR-010, TR-012
- Blocked By: TR-003, TR-004, TR-005, TR-006

## Dependency Rationale
Drafts need artifact storage, deterministic findings, validated LLM analysis,
and reports. Approval, write-back, summaries, and demo work depend on drafts.

## Validation Notes
- Unit-test draft rendering.
- Unit-test draft hash stability.
- Unit-test that changed draft content changes the hash.
- Confirm invalid analysis produces no draft comment.

## Notes
- Risks: ticket spam if drafts bypass approval, misleading recommendation text.
- Open Questions: none.

