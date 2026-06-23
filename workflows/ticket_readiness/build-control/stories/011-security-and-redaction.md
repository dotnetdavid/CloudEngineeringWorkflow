# TR-011: Security And Redaction

## Priority
P0

## Tool Type
security

## Spec Trace
Detailed Specification: `18.11 Security And Redaction`, `15. Security Requirements`

## Story
As a maintainer, I want secret-like strings redacted and security boundaries
documented so that workflow artifacts do not leak credentials or imply approval
to process real work tickets.

## Scope Boundaries
### In
- Secret-like string detection.
- Redaction before writing issue snapshots and model outputs.
- Tests for common API key and token patterns.
- Documentation of security limitations.
- Explicit sandbox-only V1 warnings.
- OpenAI API key handling guidance.

### Out
- Full data loss prevention system.
- Real work ticket processing.
- Redaction policy for production/employer/customer data.
- Secret scanning service integration.
- Credential storage implementation.

## Acceptance Criteria
- [ ] Obvious API keys and tokens are redacted from artifacts.
- [ ] Redaction tests cover common secret patterns.
- [ ] Security limitations are documented.
- [ ] OpenAI API key is read from environment or approved local secret store.
- [ ] V1 documentation states real work tickets are not authorized.

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
- Blocks: TR-005, TR-009, TR-012
- Blocked By: TR-001

## Dependency Rationale
LLM analysis and Linear write-back must not be built without security and
redaction guardrails. Documentation and demo need the security boundaries.

## Validation Notes
- Unit-test redaction for obvious token, API key, and bearer token patterns.
- Review artifacts from fixture runs to confirm redaction is applied.
- Verify no API keys are logged, committed, or written to artifacts.
- Verify docs state sandbox-only V1 limitations.

## Notes
- Risks: false sense of safety, insufficient redaction, accidental real-ticket
  use.
- Open Questions: none.

