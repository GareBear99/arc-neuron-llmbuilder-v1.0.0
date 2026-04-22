# Incident Response

## Failure classes
- Backend unavailable
- Invalid benchmark outputs
- Promotion regression
- Schema drift
- Attachment/evidence incompatibility

## Immediate response
1. Stop promotion.
2. Preserve reports and experiment logs.
3. Re-run validation and backend health checks.
4. Compare against last known-good experiment.
5. Open an incident entry with:
   - timestamp
   - backend target
   - candidate model
   - observed failure
   - blocked release decision

## Recovery rule
Never promote a candidate when benchmark execution, scoring, or validation artifacts are incomplete.
