# Ticket Readiness Rubric

The workflow scores each issue across practical readiness dimensions. The score
is a decision aid, not an oracle.

## Statuses

- `ready` - sufficient for sprint planning or implementation.
- `needs_grooming` - useful ticket, but missing information should be resolved
  before sprint commitment.
- `blocked` - cannot proceed without an external dependency, approval, or input.
- `not_ready` - too vague, risky, or underspecified for useful planning.

## Dimensions

### Outcome Clarity

Does the ticket explain the desired outcome rather than only naming an activity?

### Scope and Boundaries

Does it say what is in scope and out of scope?

### Environment and Blast Radius

Does it identify environment, account, region, service, system, or affected
users?

### Acceptance Criteria

Can a reviewer tell when the work is complete?

### Rollback and Recovery

For change tickets, is rollback or recovery described?

### Security Impact

Does the ticket touch IAM, network access, secrets, data, production, or
privileged operations?

### Observability and Validation

Does the ticket describe how the change or investigation will be validated?

### Dependencies and Ownership

Are blockers, approvers, owners, and related systems identified?

### Estimate Confidence

Is the estimate plausible given the information available?

## Default Readiness Heuristics

- Missing acceptance criteria usually means `needs_grooming` or worse.
- Production-impacting work without affected service, metric, or rollback is
  `not_ready`.
- IAM or access changes without approver and rollback path are `blocked` or
  `needs_grooming`.
- Investigation tickets may be ready without a fix plan if the investigation
  output is clear.
- Documentation-only work can be ready with lighter evidence requirements.

