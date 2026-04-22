# v0.9 upgrade notes

- removed the fixed 300 second generation timeout from the live llamafile stream path
- split startup readiness from generation streaming timeout behavior
- added slow-CPU-safe streaming mode that disables fixed total generation timeout after connection
- kept optional idle-stall timeout support for stricter deployments
- updated README and llamafile flow docs to describe managed offline binary flow and exact token accounting
