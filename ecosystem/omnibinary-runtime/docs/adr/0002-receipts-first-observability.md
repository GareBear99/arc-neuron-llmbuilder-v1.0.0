# ADR 0002: Receipts-first observability

## Status
Accepted

## Decision
Every intake, planning, decode, lowering, dispatch preview, and execution event emits structured receipts.

## Rationale
A binary runtime without strong observability becomes impossible to debug once compatibility work begins.
