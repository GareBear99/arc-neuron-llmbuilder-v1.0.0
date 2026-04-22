# v1.4 audit notes

This pass focused on consistency and package hygiene rather than adding speculative new architecture.

## Reviewed and corrected

- updated package version and metadata to `1.4.0`
- added a real CLI entrypoint: `lucifer`
- synchronized README with the current runtime shape
- removed stale cache artifacts from the repo tree
- removed the leftover non-primary `llama.cpp` backend adapter from the packaged source tree
- tightened high-risk approval budget logic so it counts only approved high-risk proposals rather than every approval event
- added CLI and budget-regression tests

## Command surface added

- `lucifer read <path>`
- `lucifer write <path> <content>`
- `lucifer delete <path> [--confirm]`
- `lucifer shell <allowlisted command>`
- `lucifer prompt <text>`
- `lucifer approve <proposal_id>`
- `lucifer reject <proposal_id> [--reason]`
- `lucifer rollback <proposal_id>`
- `lucifer trace [--output trace.html]`
- `lucifer state`
- `lucifer commands`

## Validation

- full test suite passing after audit changes
- package compiles cleanly
- CLI trace generation verified
