# Frontend

A React-based frontend app built with TypeScript and Vite.

## Project Structure

The project follows Domain-Driven Design (DDD) principles, organizing code by business domains rather than technical concerns.

```
app/
├── components/       # Shared UI components
├── domains/          # Business domains
│   ├── common/       # Shared domain logic
│   ├── landingpage/  # Landing page domain
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── store/
│   │   ├── types/
│   │   └── utils/
│   └── .../          # ...
├── hooks/            # Shared React hooks
├── layouts/          # Page layouts
├── routes/           # Route definitions
├── store/            # Global state management
├── theme/            # Theme configuration
└── types/            # Shared TypeScript types
```

### Domain Structure

Each domain follows a consistent structure:

```
domains/
└── [domain-name]/
    ├── components/   # Domain-specific components
    ├── hooks/        # Domain-specific hooks
    ├── store/        # Domain state management
    ├── types/        # Domain-specific types
    └── utils/        # Domain-specific utilities
```

## Development

### Prerequisites

- Node.js v20 or later
- Yarn v4.x

### Setup

1. Install dependencies:

   ```bash
   yarn install
   ```

2. Create a .env file in the app root directory with the following variables:
   ```bash
   VITE_BACKEND_URL=http://localhost:3010
   ```
3. Start the development server:

   ```bash
   yarn dev
   ```

4. Start the backend development server:
   ```bash
   cd ../backend && yarn start
   ```

The application will be available at `http://localhost:3023`

### Available Scripts

- `yarn dev` - Start development server
- `yarn dev-ssl` - Start development server with SSL
- `yarn build` - Build for production
- `yarn preview-build` - Preview production build with Firebase emulators
- `yarn lint` - Run ESLint and TypeScript checks
- `yarn format` - Format code with Prettier
- `yarn prettier:check` - Check for formatting issues with Prettier
- `yarn typecheck` - Run type checking
- `yarn schema:generate` - Generate TypeScript schema from the OpenAPI specification

## Code Style

We use ESLint and Prettier for code formatting and linting. The configuration is in:

- `.prettierrc` - Prettier configuration
- `eslint.config.js` - ESLint configuration

## Domain-Driven Design Guidelines

### Domain Organization

1. **Domain Boundaries**

   - Each domain should be self-contained
   - Domains should have clear boundaries
   - Cross-domain dependencies should be explicit

2. **Domain Components**

   - Components should be scoped to their domain
   - Shared components go in `app/components`
   - Domain-specific components go in their domain's `components` folder

3. **State Management**

   - Domain state should be managed within the domain
   - Global state should be minimal
   - Use Zustand for complex state management

4. **Type Definitions**
   - Domain types should be defined within the domain
   - Shared types go in `app/types`
   - Use TypeScript interfaces for domain models

### Best Practices

1. **Domain Isolation**

   - Keep domain logic within its domain
   - Use interfaces for cross-domain communication
   - Avoid direct dependencies between domains

2. **Component Organization**

   - Group related components together
   - Use index files for clean exports
   - Keep components focused and small

3. **State Management**

   - Use local state for UI-only state
   - Use domain state for business logic
   - Use global state sparingly

4. **Type Safety**
   - Use strict TypeScript configurations
   - Define clear interfaces for domain models
   - Use type guards for runtime checks
