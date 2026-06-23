# TR-005: LLM Analysis Adapter

## Priority
P0

## Tool Type
adapter

## Spec Trace
Detailed Specification: `18.5 LLM Analysis Adapter`, `10. LLM-Assisted Analysis`

## Story
As a reviewer, I want OpenAI-assisted analysis to interpret ticket intent and
draft grooming feedback so that nuanced readiness issues can be identified
without giving the model authority to mutate Linear.

## Scope Boundaries
### In
- OpenAI API usage for V1.
- Prompting based only on issue snapshot, readiness rubric, and deterministic
  findings.
- Structured model output validation.
- Failure behavior for invalid or missing model output.
- Model metadata capture when available.
- Secret-safe API key handling through environment or approved local secret
  store.

### Out
- Multi-provider abstraction.
- Codex-only model execution.
- Model-selected Linear target IDs.
- Automatic comment posting.
- Processing real work tickets.
- Storing API keys or credentials in artifacts.

## Acceptance Criteria
- [ ] Prompt uses issue snapshot and rubric only.
- [ ] Output schema is validated.
- [ ] Invalid output fails closed.
- [ ] Model metadata is recorded when available.
- [ ] OpenAI API key is never hard-coded or persisted in workflow artifacts.

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
- Blocks: TR-006, TR-007, TR-010
- Blocked By: TR-001, TR-004, TR-011

## Dependency Rationale
The adapter needs project structure, deterministic findings, and secret/redaction
guardrails before model output can safely influence reports or drafts.

## Validation Notes
- Unit-test prompt construction with fixture issue snapshots.
- Unit-test model output schema validation.
- Unit-test invalid output behavior.
- Review code to confirm target Linear issue IDs come from workflow state, not
  model output.
- Review code to confirm API key is not logged or written to artifacts.

## Notes
- Risks: overconfident model output, prompt drift, secret leakage, target-ID
  injection.
- Open Questions: none.

