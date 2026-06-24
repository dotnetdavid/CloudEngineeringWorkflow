# ADR-001: HTTP Client And SDK Usage

Date: 2026-06-24

Status: Deferred for V1

## Context

The Ticket Readiness workflow currently uses `urllib.request` for live Linear
GraphQL reads, OpenAI Responses calls, and optional Linear comment write-back.
The code review raised that direct standard-library HTTP usage increases
maintenance burden compared with a mature HTTP client such as `httpx` or
`requests`, or provider SDKs.

The concern is valid. Mature clients can provide cleaner request APIs,
connection pooling, richer timeout models, retry hooks, transport-level
testing, and clearer error handling. Official SDKs can also reduce drift from
provider API contracts.

## Decision

Do not migrate HTTP calls to `httpx`, `requests`, the OpenAI SDK, or a Linear
SDK in V1. Keep the current `urllib.request` clients for the sandbox workflow,
but treat this as an explicit production-readiness limitation.

## Rationale

V1 is a local sandbox workflow with a narrow live HTTP surface:

- one Linear GraphQL read client;
- one OpenAI Responses client;
- one optional Linear comment write-back client.

Recent hardening has reduced the highest-risk gaps without adding runtime
dependencies:

- API timeout values are validated.
- API calls can be rate limited.
- HTTP 429 responses produce clear domain errors.
- HTTP error response details are redacted before surfacing.
- Write-back remains comment-only and approval-gated.
- Tests cover request construction, credential sourcing, rate-limit handling,
  timeout validation, error redaction, and write-back gating.

Migrating now would add dependency and review surface while the surrounding
workflow is still stabilizing. For V1, that cost is not justified by the
current call volume or operational model.

## Risks

Keeping `urllib.request` means V1 still lacks features that mature clients or
SDKs commonly provide:

- connection pooling;
- first-class retry/backoff policies;
- richer per-phase timeout controls;
- cleaner test transports;
- provider-maintained request and response models;
- less hand-written HTTP boilerplate.

These risks are acceptable only because V1 is sandbox-scoped and not approved
for employer, customer, proprietary, or production ticket processing.

## Revisit Triggers

Reevaluate this decision before any of the following:

- production or team-shared deployment;
- processing real employer, customer, or proprietary tickets;
- adding retries, pagination beyond the current Linear read path, or more API
  operations;
- adding concurrent live API calls;
- introducing observability that needs request latency, status, and retry
  metrics;
- expanding write-back beyond approved Linear comments.

## Future Migration Preference

If migration is adopted later:

1. Prefer `httpx` for explicit timeout, transport, and testability controls.
2. Evaluate the official OpenAI SDK for the OpenAI Responses path if it reduces
   provider-contract drift without weakening testability.
3. Keep Linear GraphQL behind the existing client interface unless a mature
   Linear SDK provides clear value for the supported operations.
4. Preserve all current security tests, including timeout validation,
   rate-limit handling, redacted HTTP error details, and approval-gated
   write-back.
