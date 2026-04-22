# GUI daemon bridge

Arc-RAR now includes a file-based GUI daemon bridge that allows terminal commands, scripts, or an AI controller to drive a live or simulated GUI state machine without depending on sockets or platform-native IPC first.

## Commands

- `arc-rar gui open <archive>` queues an open request.
- `arc-rar gui select <entries...>` queues a selection update.
- `arc-rar gui extract --selected --out <dir>` queues an extraction request.
- `arc-rar gui daemon-once` consumes one queued command, updates GUI status, writes a response, and emits an event.
- `arc-rar gui daemon-loop --max <n>` consumes up to `n` commands.
- `arc-rar gui watch --json` reads outbox payloads.

## Files

Under the configured IPC root Arc-RAR uses:
- `gui-inbox/` for incoming GUI command envelopes
- `gui-outbox/` for response and event envelopes
- `gui-status.json` for current GUI status snapshot

This is intentionally simple and portable. A future production phase should add named pipes on Windows and Unix sockets on macOS/Linux while preserving the same envelope schema.
