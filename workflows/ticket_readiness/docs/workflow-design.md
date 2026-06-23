# Ticket Readiness Workflow Design

## Purpose

Build a simple durable workflow that helps an infrastructure or cloud engineer
process backlog tickets before sprint commitment.

The workflow should improve engineering hygiene without pretending to be a
manager, architect, SRE, security reviewer, and deployment bot in a trench coat.
Its job is to surface missing context, risk, and next questions.

## Primary User

A cloud infrastructure engineer grooming Linear issues for sprint planning,
code review prep, meeting planning, and implementation readiness.

## Input

Linear issues from the sandbox project:

- Title
- Description
- Priority
- Estimate
- Status
- Labels
- Project and team metadata
- Comments, when available in later versions

## Output

For each issue:

- Readiness status
- Readiness score
- Work type classification
- Missing information
- Grooming questions
- Risk and blast-radius notes
- Security and operational concerns
- Suggested acceptance criteria improvements
- Draft Linear comment requiring human approval

For each run:

- Run manifest
- Event log
- Summary report
- Local snapshots of evaluated issue inputs

## Durability Model

V1 uses the filesystem as the durable store.

This is intentional. A database would be reasonable in production, but it adds
operational overhead before the workflow contracts are proven. The filesystem
still gives us evidence, replayability, reviewable artifacts, and a migration
path to database tables later.

## Human Approval Gate

The workflow may generate draft comments, but it must not post comments to
Linear without explicit human approval for each issue or approved batch.

V1 approval is manual and file-backed. The operator approves, rejects, or skips
drafts by creating or editing approval JSON records in the run's `approvals/`
directory. Later versions may add a CLI approval helper, but automatic approval
is out of scope.

Approval records should include:

- Issue ID
- Draft path or draft hash
- Decision: approved, rejected, skipped
- Approver identity, when available
- Timestamp
- Optional rationale

## Failure Handling

The workflow should fail closed:

- If Linear read fails, no analysis is posted.
- If report generation fails, no comment is posted.
- If approval is missing, no comment is posted.
- If comment posting fails, the failure is recorded in `events.jsonl` and the
  approval record remains available for retry.

## Security Notes

- Never store API tokens or credentials in workflow artifacts.
- Redact sensitive data when real tickets are used.
- V1 is limited to synthetic sandbox tickets. Real work tickets require an
  approved redaction policy before use.
- Flag IAM, networking, production, database, and incident tickets for stronger
  review.
- Treat broad access changes, irreversible operations, and production-impacting
  changes as not ready unless rollback and approval paths are explicit.
