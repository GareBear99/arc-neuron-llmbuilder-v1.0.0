# Security Policy

This project is intended to execute and analyze binaries. Treat it as security-sensitive.

## Reporting
Privately report issues involving:
- sandbox escape assumptions
- arbitrary code execution beyond intended runtime scope
- receipt tampering or cache poisoning
- personality mediation bypass
- privilege or path traversal bugs

## Current status
The repo is not yet production-hardened. Do not deploy it as a trusted multi-tenant execution service in its current state.
