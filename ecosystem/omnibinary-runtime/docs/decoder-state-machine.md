# Decoder State Machine

The first real decoder should move through these states:

1. intake bytes
2. validate ISA mode
3. decode instruction
4. classify side effects
5. append canonical IR nodes
6. finalize block exit kind
7. emit decode receipt

Every state transition should be surfaced in receipts so failures are explicit.
