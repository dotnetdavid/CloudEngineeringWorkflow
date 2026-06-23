# TR-006: Report Generator

## Priority
P0

## Tool Type
backend

## Spec Trace
Detailed Specification: `18.6 Report Generator`, `7.3 Markdown Report Contract`, `7.4 JSON Report Contract`

## Story
As an operator, I want Markdown and JSON readiness reports so that each issue's
analysis is reviewable by humans and usable by later workflow steps.

## Scope Boundaries
### In
- Generate Markdown reports from validated analysis.
- Generate JSON reports from validated analysis.
- Include deterministic and LLM findings.
- Include readiness status, score, work type, risk level, evidence, missing
  information, grooming questions, operational risk, security notes, acceptance
  criteria improvements, and recommended next action.
- Write reports under the run folder.
- Link reports from run summary data.

### Out
- Word document generation.
- PDF export.
- Linear comment posting.
- Approval record creation.
- UI rendering.

## Acceptance Criteria
- [ ] Markdown reports follow the template.
- [ ] JSON reports follow the contract.
- [ ] Reports include deterministic and LLM findings.
- [ ] Reports are linked from run summary.
- [ ] Report generation failure prevents write-back for affected issues.

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
- Blocks: TR-007, TR-010, TR-012
- Blocked By: TR-002, TR-003, TR-004, TR-005

## Dependency Rationale
Reports need issue input, artifact writing, deterministic findings, and
validated LLM analysis. Drafts, summaries, and the demo depend on generated
reports.

## Validation Notes
- Unit-test Markdown rendering from fixture analysis.
- Unit-test JSON report schema.
- Confirm report paths are stable and stored under the run folder.
- Confirm reports separate evidence from inference.

## Notes
- Risks: noisy reports, schema drift, missing security notes.
- Open Questions: none.

