# Development Workflow

## Package Manager

Always use `yarn` for all package management and script execution.

## Running Code

Never use `npx tsx` or similar ad-hoc execution tools. Use reliable local workflows:

```bash
# Build first
yarn run build

# Then run the compiled output
yarn run import
```

## Verification

Always run tests after making changes:

```bash
yarn test
```
