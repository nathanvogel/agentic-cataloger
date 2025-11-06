---
inclusion: always
---

# Development Workflow

## Development Order

1. Write tests
2. Write code
3. Build and run tests
4. Execute if needed

## Package Manager

Always use `yarn` for all operations.

## Execution Pattern

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
