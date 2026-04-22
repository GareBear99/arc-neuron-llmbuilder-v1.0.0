# CLI

## Core commands
- `obi doctor`
- `obi support`
- `obi init-config`
- `obi inspect <path>`
- `obi explain <path>`
- `obi plan <path>`
- `obi lower <path>`
- `obi decode <path>`
- `obi dispatch <path>`
- `obi run <path> -- <args...>`
- `obi receipts [limit]`
- `obi cache-dir`
- `obi cache-stats`

## Command intent
- `doctor`: show current repo-state health
- `support`: show the declared support inventory and lane status
- `init-config`: write a starter config file to the local config path
- `inspect`: classify a target and persist a decision receipt
- `explain`: print a human-readable explanation of the lane choice
- `plan`: generate the canonical IR planning receipt
- `lower`: generate translation-block and compilation-preview receipts
- `decode`: run the toy decode preview over a file prefix
- `dispatch`: show preview dispatch steps and invalidation watchpoints
- `run`: execute only the native direct lane in this repo state


## v1.1 additions
- `obi env-report` writes a deterministic environment/debug receipt.
- `obi receipt-summary` aggregates receipt categories and latest entries.
- `obi clear-cache` clears generated local receipts and index state.


## Additional commands

- `obi core-gap`
- `obi fixture-manifest`


- `obi milestone-check` — emit the current completion ledger and shortest remaining implementation path.

- `obi cache-validate` — verify that receipt index entries and cached receipt files still agree.
- `obi slice-report` — emit the current execution-slice progression and next cut line.


Additional commands added later:
- `obi repo-audit`
- `obi report-pack`
