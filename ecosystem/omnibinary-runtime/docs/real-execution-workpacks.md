# Real Execution Workpacks

## Workpack 1
Implement one real guest decoder (recommended: aarch64 basic blocks on x86_64 Linux host).

## Workpack 2
Lower decoded guest blocks into canonical IR and compare against fixtures.

## Workpack 3
Emit one runnable host block through Cranelift and prove re-entry through a dispatch stub.

## Workpack 4
Persist compiled block metadata and invalidation reasons in cache.

## Workpack 5
Mediate one real syscall surface through the Linux personality layer.

## Workpack 6
Execute translated code inside a brokered process boundary and emit crash/fault receipts.
