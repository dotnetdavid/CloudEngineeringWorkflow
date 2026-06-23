# Known Risks

## Overconfident Analysis

LLM analysis can sound more certain than the evidence supports. Reports must
separate observed ticket content from inferred risk.

## Ticket Spam

Automatically posting comments can create process noise. V1 requires human
approval before any Linear write-back.

## Sensitive Data Leakage

Real tickets may include account IDs, hostnames, IAM policy details, incident
details, or customer information. Redaction rules are required before using this
workflow on real production tickets.

## False Sense of Readiness

A high readiness score is not approval to deploy. It only means the ticket is
clear enough for planning or review.

## Rubric Drift

The rubric may need to evolve as real workflows reveal better signals. Changes
to scoring rules should be documented rather than silently adjusted.

