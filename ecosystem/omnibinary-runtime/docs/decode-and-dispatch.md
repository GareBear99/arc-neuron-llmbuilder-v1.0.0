
# Decode and Dispatch Preview

v0.6 adds two new proof paths.

## Decode preview
The decode preview reads a small prefix of input bytes and lowers them into a toy canonical IR mapping. This is not a real ISA decoder. It exists to prove the repo plumbing and receipt model from bytes -> decoded operations -> IR summary.

## Dispatch preview
The dispatch preview derives translation-block identities, synthetic compiled block keys, dispatch steps, and invalidation watchpoints. It is still not an execution backend, but it makes the next engineering step much more concrete.
