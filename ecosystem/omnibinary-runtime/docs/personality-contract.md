# Personality Contract

A personality adapter is usable only when it can:
- map at least one real guest userspace syscall surface
- return deterministic error translations
- capture receipts for mediated calls
- refuse unsupported operations explicitly
- isolate host-only resources behind policy
