# Execution Slices

The shortest honest path from scaffold to real runtime is:

1. native-direct proof path
2. toy decode + canonical IR preview
3. one real aarch64 basic-block decoder
4. one runnable Cranelift-emitted host block
5. cache reuse/invalidation + brokered execution loop

The repo is complete only after slice 5 is validated on supported machines.
