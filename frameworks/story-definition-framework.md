# Story Definition Framework

## Purpose

This framework defines how to turn an approved workflow or product
specification into precise, buildable development stories.

It exists so stories are not created directly from vibes, meeting fragments, or
an overconfident summary. The goal is to produce stories that are small enough
to build, specific enough to test, safe enough to operate, and clear enough to
be useful in Linear without making Linear the architecture source of truth.

## Source Material

This framework consolidates the useful parts of:

- `D:\ai-projects\Telos\Personal\Leadership Portfolio\Delivery Frameworks\Scrum Story Framework.md`
- `/home/dfrey/devel/ai-projects/agent-foundations/docs/application-planning-process.md`
- `/home/dfrey/devel/ai-projects/agent-foundations/build-control/BUILD_RUNBOOK.md`
- `/home/dfrey/devel/ai-projects/agent-foundations/build-control/stories/*.md`

The base Scrum framework provides the story skeleton. The Agent Foundations
planning process adds build-control discipline, scope boundaries, dependency
metadata, validation gates, and Linear creation policy.

## Operating Principle

The local planning package is the source of truth. Linear is the execution
tracker.

That means:

- architecture decisions live in durable local docs;
- stories are drafted and reviewed locally before Linear creation;
- Linear issues are concise execution records, not the full design archive;
- dependencies and scope boundaries are resolved before development starts.

## Story Creation Flow

```text
approved specification
  -> story candidates identified
  -> stories grouped by build sequence
  -> dependencies mapped
  -> scope boundaries written
  -> acceptance criteria written
  -> validation notes written
  -> story package reviewed
  -> Linear creation approved
  -> Linear issues created
```

## Entry Criteria For Creating Stories

Story creation is a strict gate. Do not create implementation stories until all
of these are true:

- The cover sheet or equivalent overview has been reviewed.
- The detailed specification is reviewed and current enough to drive
  implementation without hidden discovery work.
- V1 success criteria are documented.
- Major scope decisions are resolved.
- V1 in-scope and out-of-scope boundaries are documented.
- Implementation constraints are documented, including repository location,
  runtime or language expectations, provider choices, and major integration
  boundaries.
- Security and data-handling boundaries are documented.
- External systems and write-back behavior are documented.
- Durable artifact or persistence expectations are documented.
- Human approval gates are documented, if the system can mutate external state.
- Testing expectations are documented.
- Known risks are documented.
- Open questions that affect implementation story shape are resolved.

If an unresolved question changes what must be built, story creation is blocked.
Resolve the question first. If investigation is required, create an explicit
discovery or design story before implementation stories are generated.

## Exit Criteria For The Story Package

The story package exits planning and becomes eligible for Linear creation only
when all of these are true:

- Story list reviewed.
- Story sequence reviewed.
- Story dependencies reviewed.
- Each dependency has a reason, not just a link.
- Scope boundaries accepted.
- Priorities assigned.
- Tool types assigned.
- Every story maps back to a section of the approved specification.
- Acceptance criteria are testable.
- Definition of Ready is satisfied for each story.
- Validation notes are specific enough for review.
- Security-sensitive work is explicitly flagged.
- Cross-cutting documentation, testing, and observability work is represented.
- No story contains unresolved implementation-shaping questions.
- Story package has been reviewed against V1 success criteria.
- Linear milestone, project, or grouping strategy is confirmed.

## Build-Control Package Requirements

A build-control package should include:

- decision log or detailed specification;
- runbook or build plan;
- story list;
- dependency graph or dependency table;
- explicit V1 non-goals;
- validation gates;
- story files;
- Linear creation policy.

For small projects, this may be lightweight. It still must exist. Small
projects are where sloppy assumptions wear a fake mustache and sneak into prod.

## Story File Requirements

Each story must include:

- title;
- priority;
- tool type;
- story statement;
- scope boundaries;
- acceptance criteria;
- Definition of Ready;
- Definition of Done;
- dependencies;
- validation notes;
- notes for risks and open questions.

## Priority Model

Use this default model unless the project defines a better one:

- `P0`: required to prove the core workflow safely.
- `P1`: required for usable V1 product or operator surface.
- `P2`: required for showcase completeness, polish, or follow-on integration.

Priority is not urgency theater. A story is P0 only if the system cannot prove
its core behavior safely without it.

## Tool Type

Use tool type to clarify the kind of work and the likely reviewer.

Common tool types:

- `foundation`
- `workflow`
- `backend`
- `api`
- `cli`
- `adapter`
- `artifact-store`
- `security`
- `qa-docs`
- `observability`
- `integration`
- `showcase`
- `design`

Tool type is not a team label. It is a planning signal.

## Story Template

```markdown
# <PROJECT-ID>: <Story Title>

## Priority
P0 | P1 | P2

## Tool Type
<foundation | workflow | backend | api | cli | adapter | artifact-store | security | qa-docs | observability | integration | showcase | design>

## Story
As a <user/persona>, I want <capability> so that <outcome>.

## Scope Boundaries
### In
- <Included behavior or responsibility>

### Out
- <Explicitly excluded behavior or responsibility>

## Acceptance Criteria
- [ ] <Observable, testable criterion>
- [ ] <Observable, testable criterion>
- [ ] <Observable, testable criterion>

## Definition of Ready
- [ ] Story is clearly written.
- [ ] Acceptance criteria are defined.
- [ ] Dependencies are identified.
- [ ] Test strategy is understood.
- [ ] UX/Architecture reviewed, if applicable.
- [ ] Security impact reviewed, if applicable.
- [ ] Documentation impact reviewed.
- [ ] Approved by Team and Product Owner, or explicit project approver.

## Definition of Done
- [ ] Code complete.
- [ ] Tests written and passing.
- [ ] Documentation updated.
- [ ] Security validation complete, if applicable.
- [ ] Observability/logging updated, if applicable.
- [ ] Deployed or demonstrated in the appropriate environment.
- [ ] Comprehensive code review complete.
- [ ] Validated by Product Owner or explicit project approver.

## Dependencies
- Blocks:
- Blocked By:

## Validation Notes
- <Specific commands, review checks, fixture cases, or manual verification>

## Notes
- Risks:
- Open Questions:
```

## Acceptance Criteria Rules

Acceptance criteria must be:

- observable;
- testable;
- specific to this story;
- written from the system behavior perspective;
- narrow enough that completion is not a debate.

Bad:

```markdown
- [ ] Workflow works.
```

Better:

```markdown
- [ ] Running `ticket-readiness run-analysis` creates a timestamped run folder
      containing `manifest.json`, `events.jsonl`, `summary.md`, `inputs/`,
      `reports/`, `drafts/`, and `approvals/`.
```

## Scope Boundary Rules

Every story must say what is in and what is out.

Use `Out` to prevent accidental scope creep, especially for:

- production access;
- automatic external write-back;
- database persistence;
- authentication expansion;
- additional providers;
- UI polish;
- scheduled automation;
- cross-system integrations;
- deployment automation.

If the story could reasonably be misunderstood, the boundary is not clear
enough.

## Dependency Rules

Dependencies must identify both directions:

- `Blocks`: stories that cannot safely start until this story is done.
- `Blocked By`: stories that must be done before this one starts.

Dependencies should be based on contracts and risk, not personal preference.

Examples:

- A write-back story is blocked by approval-record validation.
- A UI story is blocked by a stable API or artifact contract.
- A provider integration is blocked by config and secret-handling policy.
- A demo story is blocked by test data, documentation, and minimum workflow
  completion.

## Validation Notes Rules

Validation notes should explain how reviewers prove the story is done.

Good validation notes include:

- test command names;
- fixture names;
- manual verification steps;
- security checks;
- expected artifact paths;
- expected failure behavior;
- acceptance demo steps.

Do not write empty validation notes. That is how defects get a guest bedroom.

## Definition Of Ready

Definition of Ready means the story can be pulled into implementation without
requiring discovery disguised as coding.

Minimum ready criteria:

- Story is clearly written.
- Acceptance criteria are defined.
- Scope boundaries are explicit.
- Dependencies are identified.
- Test strategy is understood.
- Security impact is identified.
- Documentation impact is identified.
- UX or architecture review is complete when relevant.
- Project approver accepts the story for implementation.

If the story still contains implementation-shaping open questions, it is not
ready.

## Definition Of Done

Definition of Done means the story is complete enough to survive contact with
another engineer.

Minimum done criteria:

- Code or document changes are complete.
- Tests are written and passing, where applicable.
- Documentation is updated.
- Security validation is complete, where applicable.
- Observability or logging is updated, where applicable.
- Manual verification is recorded, where applicable.
- Code review is complete.
- Product or project validation is complete.

Do not mark a story done just because the happy path works once.

## Linear Creation Policy

Do not create Linear issues until the local story package has been reviewed and
accepted.

When creating Linear issues:

- use the local story file as the source;
- keep the Linear issue readable and execution-oriented;
- include links or references to durable local docs when useful;
- do not paste excessive architecture detail into Linear;
- preserve priority, dependencies, acceptance criteria, and validation notes;
- do not create issues for unresolved questions unless they are explicit
  discovery/design stories.

## Story Quality Review Checklist

Before creating Linear issues, review each story:

- Does the title describe a deliverable?
- Does the story statement identify persona, capability, and outcome?
- Are `In` and `Out` boundaries clear?
- Are acceptance criteria testable?
- Is the story small enough to complete independently?
- Are dependencies accurate?
- Is security impact addressed?
- Is observability or logging addressed where relevant?
- Is documentation impact addressed?
- Are validation notes specific?
- Are open questions acceptable, or should they block story creation?

## Common Anti-Patterns

Avoid:

- giant stories that hide multiple deliverables;
- acceptance criteria that restate the title;
- scope boundaries that omit obvious non-goals;
- stories that require unapproved architecture decisions;
- stories that mutate external systems without approval gates;
- security-sensitive work without validation notes;
- documentation treated as cleanup instead of completion;
- Linear issues created before the local planning package is reviewed.

## Recommended Use For Cloud Engineer Workflows

For each workflow project:

1. Write the cover sheet.
2. Write the detailed specification.
3. Resolve implementation-shaping questions.
4. Create a build-control package.
5. Draft story files with this framework.
6. Review story sequence and dependencies.
7. Confirm Linear grouping strategy.
8. Create Linear issues only after approval.
