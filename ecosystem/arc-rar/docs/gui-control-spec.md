# GUI Control Spec

Arc-RAR exposes a second command surface so the GUI can be controlled by:
- a person in a terminal
- a local script
- an automation daemon
- an AI agent

## Envelope schema

```json
{
  "op": "open_archive",
  "payload": {
    "archive": "/absolute/or/relative/path.rar"
  }
}
```

## Canonical ops

- `start_gui`
- `open_archive`
- `select_entries`
- `extract`
- `create`
- `focus`
- `ping`
- `status`

## Design rule

The GUI should never invent a private action that the command plane cannot express.
