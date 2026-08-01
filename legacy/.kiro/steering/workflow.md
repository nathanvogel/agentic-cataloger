---
inclusion: always
---

# Development Workflow

## Development Order

1. Update `requirements.md`, if needed.
2. Update `design.md`, if needed.
3. Write tests
4. Write code
5. Build and run tests
6. Execute, if needed

## Package Manager

Always use `yarn` for all operations.

## Execution Pattern

## `backend`

The user is responsible for ensuring the backend is running through `yarn dev`, usually on port 3010.

## `frontend`

The user is responsible for ensuring the backend is running through `yarn dev`, usually on port 3011.

### `data-importer`

```bash
# Build first
yarn run build

# Then run compiled output
yarn run import
```

## Verification

Always run tests after changes:

```bash
yarn test
```

## Code Styling

Directly write Prettier-formatted code. This makes subsequent edits easier, as the IDE autoformats your code. `.prettierrc`:

```
{
  "singleQuote": false,
  "trailingComma": "all"
}
```
