# Arc-RAR Autowrap + Intent Validation Doctrine

## Goal

Every actionable path in Arc-RAR should be **accounted for**. Nothing should execute as an unclassified, silent side effect.

That means every archive command, GUI control command, API submission, automation recipe, and later native UI action should pass through the same spine:

1. **autowrap begin**
2. **declare intent contract**
3. **evaluate checks**
4. **block or continue depending on strict mode**
5. **emit receipt**
6. **emit violation record if any required intent is unmet**

## Terms

### Autowrap
A wrapper record that captures:
- plane
- operation
- args
- wrap id
- timestamp
- declared intents

### Intent contract
A list of what must be true or should be true for the action to be considered legitimate.

### Required intent
If unmet, the action should fail in strict mode and produce a violation.

### Optional intent
If unmet, the action may still proceed, but the receipt should make the gap visible.

### Violation
A structured record proving that an action was attempted without satisfying required intent conditions.

## Current starter implementation

The starter now wires this into:
- archive CLI verbs
- GUI terminal-control verbs
- API submission/status verbs
- automation recipe rendering

The starter is still backend-stubbed, so many operations intentionally show optional intent failures such as:
- `real_backend_connected = false`
- `native_gui_listener_connected = false`

That is by design. The action is accounted for even before the real backend exists.

## Example intent contracts

### `arc-rar list archive.zip`
Required:
- archive path present
- format supported

Optional:
- live backend connected

### `arc-rar extract archive.zip --out ./out`
Required:
- archive path present
- output path present
- format supported

Optional:
- live backend connected

### `arc-rar gui open ./archive.zip`
Required:
- archive path present

Optional:
- native GUI listener connected

### `arc-rar api submit payload.json`
Required:
- path present

## How native apps should hook in later

Every native action should call the same contract machinery before the core operation begins.

Examples:
- user clicks **Open Archive** in macOS app
- user clicks **Extract** in WinUI app
- Linux GTK app receives drag-and-drop files

Each of those should become:
- wrap begin
- intent checks
- validation report
- receipt
- result / violation

## Strict vs non-strict

### Strict mode
If any required intent is unmet:
- block the action
- emit a receipt
- emit violation
- return non-zero / show surfaced failure

### Non-strict mode
If required intents are unmet:
- still emit the receipt and violation
- allow only when policy explicitly permits degraded behavior

## Why this matters

This makes Arc-RAR auditable in the same way your validator doctrine expects:
- no silent path
- no unclassified action
- every result tied to declared intent
- every failure explainable
- every stubbed area visible instead of hidden
