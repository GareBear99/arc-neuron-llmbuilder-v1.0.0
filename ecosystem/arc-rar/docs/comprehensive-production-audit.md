# Arc-RAR Comprehensive Production Audit

Date: 2026-03-31

## Executive verdict

Arc-RAR is a credible **CLI/core architecture and handoff** with an implemented file-based GUI bridge and a clear validator doctrine. It is **not yet a truthfully complete production desktop suite**.

## File-by-file status

### Root
- `Cargo.toml` — Good workspace split. Needs real release/profile tuning and target-validated dependency locking.
- `README.md` — Honest overall. Should continue to clearly separate implemented vs partial vs planned.

### Common crate
- `config.rs` — Good default path model and basic validation. Needs migration/versioning strategy and richer OS-specific directory handling if shipped broadly.
- `errors.rs` — Good starter taxonomy. Needs richer source error chaining and more structured backend/process failures.
- `intent.rs` — Strong doctrine fit. Good shared schema for autowrap and intent results.
- `receipt.rs` — Solid base. Needs stronger production metadata coverage and maybe log rotation/retention policy.
- `types.rs` — Serviceable, but metadata is thinner than a full archive manager usually needs.

### Core crate
- `lib.rs` — Most important implemented area. Host-tool strategy is practical, but still depends on external tools and has not been validated on all targets. Production hardening still needed for archive parsing fidelity, malicious path handling, and backend variability.

### IPC crate
- `lib.rs` — File bridge is useful and portable. It is still a fallback transport, not the final transport. Production target should add Unix sockets on macOS/Linux and named pipes on Windows.

### Automation crate
- `lib.rs` — Thin starter. Not yet production-grade automation.

### CLI crate
- `main.rs` — Strongest operational surface in repo. Real structure exists, but final polish still needs validated build/test runs, stronger human-mode output, and battle-tested exit semantics.

### Native apps
- `apps/macos/ArcRAR/Sources/ArcRARApp.swift` — Placeholder shell only.
- `apps/linux/arc-rar-gtk/src/main.rs` — Placeholder shell only.
- `apps/windows/ArcRAR.WinUI/*` — Docs only, no implemented app.

### Packaging
- Linux/Mac/Windows packaging assets are useful templates, not final production installers.

### Scripts
- Setup/bootstrap scripts are helpful starter utilities, but need real target validation and polish.

## Production blockers

1. Native frontends are not fully implemented.
2. CI is present as templates but not validated.
3. Packaging/signing/notarization is not complete.
4. Tool-backed archive behavior needs target-matrix testing.
5. End-to-end malicious archive tests are not evident as complete fixtures.
6. No honest proof of successful builds on target operating systems exists in this handoff.

## What is genuinely good already

- Clear architecture
- Strong command-plane separation
- Useful autowrap/intent-validation model
- Receipt doctrine
- Practical host-tool backend strategy
- Portable file-based GUI control bridge
- Strong documentation compared with most starters

## Recommended ship order

1. Lock CLI/core as the production-first deliverable.
2. Build and validate **one** native frontend completely.
3. Add target-native IPC transport for that OS.
4. Add packaging/signing for that OS.
5. Add fixtures/integration tests.
6. Repeat for the other two OSes.

## Honest production claim threshold

Arc-RAR can be called production-ready only when all of these are true:
- successful build and test runs on macOS, Windows, Linux
- one-click/open-with integration on each target OS
- at least one validated installer per target OS
- real native frontends, not placeholders
- regression/fixture tests for supported archive formats
- clear support matrix published in README and release notes
