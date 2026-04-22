# Compatibility Matrix

| Input type | Classification | Execution status in repo state |
|---|---|---|
| Native ELF same ISA | NativeDirect | Runnable |
| Native PE same ISA | NativeDirect | Routed, but not validated on this packaging host |
| Native Mach-O same ISA | NativeDirect | Routed, but not validated on this packaging host |
| Foreign ELF/PE/Mach-O | ForeignDbt | Planned only |
| Wasm | ManagedPortable | Planned only |
| JAR | ManagedPortable | Planned only |
| .NET | ManagedPortable | Planned only |
| Shebang script | SandboxedPartial | Classified only |
| Unknown blob | Unsupported or partial | Not runnable |
