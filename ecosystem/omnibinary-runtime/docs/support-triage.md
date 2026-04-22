# Support Triage

Use `obi env-report` to capture a deterministic local environment snapshot for debugging.

Recommended flow:
1. `obi doctor`
2. `obi status`
3. `obi env-report`
4. `obi receipt-summary`

Never share secrets from your shell environment. Review the report before posting it.
