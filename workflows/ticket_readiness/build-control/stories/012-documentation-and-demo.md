# TR-012: Documentation And Demo

## Priority
P1

## Tool Type
qa-docs

## Spec Trace
Detailed Specification: `18.12 Documentation And Demo`, `17. Documentation Requirements`, `19. Acceptance Criteria For V1`

## Story
As a reviewer, I want clear documentation and a sandbox demonstration so that
the workflow can be operated, evaluated, and shown without relying on tribal
knowledge.

## Scope Boundaries
### In
- README setup instructions.
- Configuration instructions.
- Analysis run instructions.
- Manual approval instructions.
- Approved comment posting instructions.
- Run artifact explanation.
- Safety and redaction notes.
- Known limitations.
- Troubleshooting guide.
- Sandbox demo run that produces artifacts.
- One approved comment posted to a sandbox issue.

### Out
- Real ticket demo.
- Production deployment docs.
- Hosted service docs.
- Web UI guide.
- Jira docs.
- Full compliance package.

## Acceptance Criteria
- [ ] README explains setup and commands.
- [ ] Demo run produces artifacts.
- [ ] One approved comment can be posted to a sandbox issue.
- [ ] Known risks and limitations are documented.
- [ ] Documentation explains operation, approval, write-back, and safety
  boundaries.

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
- Blocks: none
- Blocked By: TR-001, TR-003, TR-006, TR-007, TR-008, TR-009, TR-010, TR-011

## Dependency Rationale
The demo and operator docs need the scaffold, artifacts, reports, drafts,
approval behavior, write-back, summary, and security boundaries to exist first.

## Validation Notes
- Follow README from a clean local environment.
- Run analysis against sandbox fixtures or the sandbox Linear project.
- Verify artifacts are created.
- Manually approve one draft and post one sandbox comment.
- Verify docs include known limitations and sandbox-only warnings.

## Notes
- Risks: docs lagging behavior, demo accidentally using non-sandbox data.
- Open Questions: none.

