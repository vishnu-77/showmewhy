# Architecture comparison

## `/showmewhy compare Redis and PostgreSQL for durable agent memory`

```text
RECOMMENDATION

Use PostgreSQL for durable memory. Keep Redis for ephemeral working state.

| Need | PostgreSQL | Redis |
|---|---|---|
| Durable history | Strong | Limited by persistence model |
| Transactions | Strong | Narrower |
| Provenance queries | Strong | Awkward |
| Low-latency ephemeral state | Good | Strong |

WHY

durable memory
   ├── history
   ├── provenance
   └── transactions
          ↓
      PostgreSQL

Caveat: Redis remains useful as the fast working-memory tier.
```
