# Model vs Runtime Boundary Spec

## Model responsibilities
The model should learn to:
- summarize a binary intake surface
- identify likely host/runtime constraints
- choose a candidate execution lane with reasons
- request preflight before execution
- state blockers honestly
- format an evidence-minded receipt summary
- distinguish planning/preview from real execution

## Runtime responsibilities
The runtime should:
- perform binary parsing and intake
- compute fingerprints
- run decoder/lowering pipelines
- enforce policy and sandbox contracts
- execute or preview a selected lane
- store machine receipts and artifacts

## Failure policy
The model must never imply that execution already happened when the runtime only produced a preview or preflight report.
