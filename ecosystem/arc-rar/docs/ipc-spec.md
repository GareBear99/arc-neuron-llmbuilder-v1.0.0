# IPC spec

Arc-RAR now includes a **real file-based IPC fallback** that works across macOS, Windows, Linux, and custom systems.

## Root

By default the IPC root is under the Arc-RAR config root, usually one of:

- `%APPDATA%/Arc-RAR/ipc`
- `$XDG_CONFIG_HOME/arc-rar/ipc`
- `$HOME/.config/arc-rar/ipc`
- override with `ARC_RAR_HOME`

## Layout

- `gui-inbox/` — terminal or automation writes command envelopes here
- `gui-outbox/` — native GUI may write response/event envelopes here
- `gui-status.json` — native GUI may write current status here

## Envelope

```json
{
  "protocol_version": 1,
  "request_id": "uuid",
  "op": "open_archive",
  "payload": {"archive": "/path/file.rar"}
}
```

## Current implementation

- CLI writes envelopes into `gui-inbox`
- CLI can read `gui-status.json`
- CLI can enumerate files in `gui-outbox`
- Native shells should consume the same files until a socket/named-pipe transport replaces or augments them
