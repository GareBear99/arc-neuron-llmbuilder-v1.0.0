# v1.0 upgrade notes

- Corrected llamafile stream watchdog semantics.
- Live generation no longer uses "wait forever" as the default slow-CPU-safe behavior.
- The stream now uses an inactivity timeout (`stream_idle_timeout`) that resets on every incoming chunk.
- This means the runtime waits while generation is alive and only errors when the stream truly stalls.
- No fixed total generation timeout was reintroduced.
