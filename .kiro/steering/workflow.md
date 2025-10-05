# Development Workflow

## Order of operations

In general, you MUST follow this order:

1. Update requirements.md
2. Update design.md
3. Update tasks.md
4. Write tests
5. Write code
6. Run the tests
7. Run the code, if needed

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
