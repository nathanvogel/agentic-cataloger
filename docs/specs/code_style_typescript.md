# TypeScript Code Style Specification

## 1. Introduction

This document defines the standard TypeScript coding style for all TypeScript projects developed within the organization. Its purpose is to ensure code consistency, readability, maintainability, and quality across all projects. All developers contributing to the TypeScript codebase are expected to follow these guidelines.

## 2. Tools & Automation

- **Mandatory Tools:** Use the following tools to automatically enforce best practices where possible. Configuration is managed centrally.
- **Prettier:** Used for automatic code formatting.
  ```json
  {
    "singleQuote": false,
    "trailingComma": "all"
  }
  ```
- **ESLint:** Used for static code analysis and enforcing coding standards.
- **TypeScript Compiler:** Enable strict type checking in tsconfig.json.
- **Pre-commit Hooks:** It is mandatory to configure pre-commit hooks to run Prettier and ESLint automatically before committing code.

## 3. Naming Conventions

- Type Names: Types, interfaces, and classes must use `PascalCase`.
- Variable Names: Variables, functions, and methods must use `camelCase`.
- Constant Names: Constant names must use `UPPER_CASE_WITH_UNDERSCORES`.
- Boolean Prefixes: Boolean variable names should preferably start with `is`, `has`, or `should` (e.g., `isActive`).
- Named Conditions: Use boolean variables with descriptive names for complex conditions.
- Component Files: React component files should use `PascalCase`.
- Component Props: Props interface should be named `[ComponentName]Props`.
- Higher-Order Components: Should start with 'with' (e.g., `withAuth`).
- Controllers: API controllers should end with 'Controller'.
- Services: API services should end with 'Service'.
- DTOs: Data Transfer Objects should end with 'Dto'.
- Entities: Database entities should be singular nouns.
- Descriptive Names: Use descriptive names; avoid overly cryptic single letters, except potentially for simple loop counters.

## 4. Code Documentation

- Comments: Use comments sparingly, code should ideally be self-explanatory about what it does. Comments clarify non-obvious logic, assumptions, or reasoning.
- JSDoc: All public modules, functions, classes, and methods must have JSDoc comments.
- TSDoc Style: Use standard TSDoc style documentation.
- Documentation vs. Comments: Documentation must describe the object's purpose and usage (the _what_), while comments should explain implementation details (the _why_ or complex _how_).
- One-Line Comments: Must be concise and clear.
- Multi-Line Documentation: Must start with a concise summary, followed by detailed parameter descriptions and return types.
- Constructor Documentation: Class constructors should be documented within their own JSDoc.
- TODO Comments: Use TODO comments to flag areas needing future attention.

## 5. Type Hints

- Function Signatures: Always define return types for functions and methods.
- Type Declarations: Prefer interfaces over type aliases for object definitions. Use type aliases for unions and complex types.
- Generics: Use generics when appropriate to create reusable components.
- Void Functions: Functions/methods that do not explicitly return a value must be annotated with `: void`.
- No Any: Avoid using the `any` type. Use proper typing or `unknown` if type information is unavailable.

## 6. Error Handling

- Use Typed Errors: Use strongly typed error handling patterns.
- Specific Error Catching: Catch specific exception types rather than using generic error handling.
- Custom Errors: Define custom error classes for application-specific errors, extending from `Error`.
- Informative Messages: Provide clear and informative messages within errors.
- Avoid Silent Failures: Ensure errors are handled or propagated; avoid silently catching errors without proper handling.
- Error Checks: Always check for possible null/undefined values before accessing properties.
- Input Validation: Validate external input using conditional checks and throw appropriate errors upon failure.

## 7. Logging

- **Appropriate Log Levels:** Use log levels semantically to convey the severity and nature of the logged event:
  - `debug`: For detailed diagnostic information useful during development and troubleshooting.
  - `info`: For messages confirming that operations are proceeding as expected.
  - `warn`: To indicate potential issues or unexpected events that do not (yet) prevent the software from working as intended.
  - `error`: For errors that prevented a specific operation from completing but allow the application to continue.
  - `fatal`: For severe errors that might lead to the application's termination.
- **Structured Logging:** Use exclusively structured logging formats (e.g., JSON) for easier parsing and analysis.
- **Wide-Event Logging:** Prefer wide-event logging where possible (e.g. use it for atomic REST API endpoints, but not necessarily for real-time streaming operations).
- **Avoid Sensitive Information:** Ensure that no sensitive data (e.g., passwords, API keys, PII (Personal Identifiable Information)) is logged.
- **Message Clarity:** Log messages should be clear, concise, and provide sufficient context to understand the event without needing to read the source code.

## 8. General Best Practices

- Null and Undefined: Use `undefined` for uninitialized values and optional properties. Use `null` when explicitly setting a value to nothing.
- Type Guards: Use type guards to narrow types when working with null/undefined.
- Optional Chaining: Use optional chaining (`?.`) and nullish coalescing (`??`) operators for safer property access.
- Imports Organization: Group imports in the following order: external libraries, internal modules, type imports, asset imports.
- Destructuring: Use destructuring for props and function parameters.
- Immutability: Prefer immutable data structures and avoid direct mutation of state.
- Async/Await: Prefer async/await over raw promises for asynchronous code.

## 9. Framework-Specific Guidelines

### 9.1 React

- Component Structure: Use functional components with hooks over class components.
- Hooks Rules: Follow React hooks rules strictly (only call hooks at the top level, only call hooks from React functions).
- Dependencies: Include all required dependencies in useEffect dependency arrays.
- Custom Hooks: Custom hooks should be prefixed with 'use' and follow the same rules as React's built-in hooks.
- State Management: Use appropriate state management based on complexity (useState, useReducer, or external libraries for complex state).

### 9.2 React Component Architecture

#### Presentational vs Logic Separation

Separate **what the user sees** from **what the app does** using file suffixes:

- **`.ui.tsx`** — Rendering, styling, layout. Receives all data and callbacks via props. May import other `.ui.tsx` components, CSS/style utilities, and UI libraries. **No** data fetching, routing side-effects, or business logic.
- **`.logic.tsx`** — Orchestration: data fetching, mutations, state machines, routing, error handling. Renders one or more `.ui.tsx` components and passes props down. May import hooks, services, stores, and `.ui.tsx` components.

A `.logic.tsx` file is only needed when a component has non-trivial orchestration (data fetching, complex state, side-effects). Simple pages or wrappers that only compose UI components don't require a separate logic file.

```
AnalysisResults.ui.tsx      # pure presentation — props in, JSX out
AnalysisResults.logic.tsx   # fetches data, manages state, renders the .ui component
```

**Rules of thumb:**

- A `.ui.tsx` component can be rendered in Storybook or a test without mocking services.
- A `.logic.tsx` component never contains `className`, inline styles, or layout markup — it delegates all of that to `.ui.tsx`.
- When a component is small and has no logic beyond local UI state (e.g. toggle, hover), a single `.tsx` file without a suffix is fine.

#### Atomic Component Structure

UI components (`*.ui.tsx`) are organized into layers of increasing specificity. Start lightweight — introduce layers only as the component library grows.

1. **atoms** — Small, generic, highly reusable building blocks with minimal internal state. Unaware of business domain or app-level context.
   _Examples: `Button`, `Badge`, `TextInput`, `Icon`, `Label`._

2. **molecules** — Compositions of atoms that form a distinct UI feature. May hold local UI state (open/closed, selected index). Still domain-agnostic where possible.
   _Examples: `SearchBox`, `FileDropzone`, `ScoreBar`, `ConfirmDialog`._

3. **organisms** — Domain-specific UI assemblies. Combine molecules/atoms into a recognizable section of the interface. Receive data via props; still no data fetching.
   _Examples: `RfpQuestionCard.ui.tsx`, `AnalysisResultsTable.ui.tsx`, `DocumentList.ui.tsx`._

**Folder structure** (grow into this as needed):

```
frontend/src/
  components/
    atoms/          # generic building blocks
    molecules/      # composed UI features
  features/
    analysis/
      AnalysisResults.ui.tsx
      AnalysisResults.logic.tsx
      AnalysisResults.test.tsx
  pages/            # route-level logic components
```

**Naming:**

- Organism-level UI components that live inside a `features/` folder are suffixed `.ui.tsx` to make the presentation boundary explicit.
- Atoms and molecules inside `components/` don't need the `.ui.tsx` suffix — their location already communicates that they are pure UI.

### 9.3 NestJS

- Controller Structure: Use decorators for route definitions. Always validate input using DTOs.
- Service Layer: Keep business logic in services. Use interfaces for dependency injection.
- Exception Filters: Use exception filters to handle errors consistently across the application.
- Guards and Interceptors: Use guards for authorization and interceptors for cross-cutting concerns.
- Dependency Injection: Use constructor-based dependency injection.

## 10. Testing

- Requirement: All new features and bug fixes should ideally be accompanied by automated tests (unit, integration, etc.).
- Framework: Use Vitest as the standard testing framework.
- UI Testing: For React components, use React Testing Library to test behavior rather than implementation details.
- API Testing: For API endpoints, test both successful operations and error cases.
- Test Structure: Tests should be organized in a way that matches the structure of the code they are testing.
- Test Descriptions: Test descriptions should clearly state what is being tested and expected outcomes.
- Mocking: Use mock implementations for external dependencies to isolate the code under test.
- Coverage: Use Vitest's coverage tools to measure and maintain test coverage.
