# pricecomp backend

Python monolith root (structural seed). Domain logic arrives in later stories.

## Toolchain

- **CPython** 3.14.6 (non-free-threaded — not `3.14t`)
- **uv** 0.12.1 (required for lock generation / sync)
- **pytest** 9.1.1 (dev dependency group)

```bash
cd backend
uv sync          # installs runtime + dev groups (includes pytest)
uv run pytest    # structural seed smoke tests
```

Active host ports (GATE-01): API **3020**, Postgres **3021**, Phoenix **3022**, frontend **3023**. Compose and role commands land in Story 1.2.
