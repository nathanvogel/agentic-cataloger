# Python Code Style Specification

## 1. Introduction
This document defines the standard Python coding style for all Python projects developed within the organization. Its purpose is to ensure code consistency, readability, maintainability, and quality across all projects. All developers contributing to the Python codebase are expected to follow these guidelines.

## 2. Tools & Automation
- **Mandatory Tools:** Use the following tools to automatically enforce best practices where possible. Configuration is managed centrally (e.g., in `pyproject.toml`).
- **Ruff:** Used for automatic formatting and linting.
  ```toml
  [tool.ruff]
  # Enable linters:
  # E: pycodestyle (style errors)
  # F: Pyflakes (logical errors)
  # DOC: pydocstyle (docstring style)
  # D: pydocstyle (docstring content)
  # I: isort (import sorting)
  # N: naming (variable/function naming)
  # B: flake8-bugbear (bug detection)
  # C4: flake8-comprehensions (list/dict comprehension improvements)
  # ARG: flake8-unused-arguments (unused function arguments)
  # SIM: flake8-simplify (code simplification)
  # TID: flake8-tidy-imports (import organization)
  # TD: flake8-todos (TODO comments)
  # PL: Pylint (general Python linting)
  # RUF: Ruff-specific rules
  # PERF: Perflint (performance optimizations)
  # ERA: eradicate (commented-out code detection)
  # FAST: FastAPI-specific rules
  # G: flake8-logging-format (logging best practices)
  # S: flake8-bandit (security)
  # C901: mccabe cyclomatic complexity
  # BLE: blind-except (no bare `except Exception`)
  # TRY: tryceratops (exception anti-patterns)
  # T20: flake8-print (no print/pprint, use logging; CLI stdout excepted)
  lint.select = ["E", "F", "DOC", "D", "I", "N", "B", "C4", "ARG", "SIM", "TID", "TD", "PL", "RUF", "PERF", "ERA", "FAST", "G", "S", "C901", "BLE", "TRY", "T20"]
  # raise-vanilla-args (TRY003) fights informative raise-site messages (§6).
  lint.ignore = ["raise-vanilla-args"]
  target-version = "py314"

  [tool.ruff.lint.mccabe]
  max-complexity = 10

  [tool.ruff.format]
  docstring-code-format=true
  docstring-code-line-length = "dynamic"

  [tool.ruff.lint.per-file-ignores]
  "__init__.py" = ["F401"]
  "**/{tests,docs,tools}/*" = ["E402"]
  ```
- **Pyright**: Used for static type checking.
  ```toml
  [tool.pyright]
  reportMissingSuperCall = "error"
  reportMissingParameterType = "error"
  ```
- **jscpd**: Copy/paste detection on `backend/src` (config: repo-root `.jscpd.json`). Runs via `./scripts/ci/backend-lint.sh` and pre-commit.
- **For substantial projects**:
  - **import-linter**: enforce package boundaries (e.g. `domain ↛ platform` and vendor adapters).
  - **Unused-export analyzer** (e.g. vulture): Knip-style dead public API detection.
- **Pre-commit Hooks**: Configured at repo root (`.pre-commit-config.yaml`). Install once with `uv run --directory backend pre-commit install`. Manual full-tree run: `./scripts/ci/backend-lint.sh` or `uv run --directory backend pre-commit run --all-files`. CLI details live in [`backend/README.md`](../../backend/README.md).
  
## 3. Naming Conventions
- Constant Names: Constant names must use `UPPER_CASE_WITH_UNDERSCORES`.
- Function Naming: Function names should generally start with a verb describing their action (e.g., `get_user_data`).
- Boolean Prefixes: Boolean variable names should preferably start with `is_` or `has_` (e.g., `is_active`).
- Named Conditions: Use boolean variables with descriptive names for complex conditions.
- Non-Public Identifiers: Non-public methods and instance variables must have a single leading underscore (e.g., `_internal_method`). 
- Descriptive Names: Use descriptive names for variables and functions; avoid overly cryptic single letters, except potentially for simple loop counters.
- Avoid Ambiguous Single Letters: Avoid single-letter variable names `l` (lowercase el), `O` (uppercase oh), or `I` (uppercase eye).

## 4. Code Documentation
- Comments: Use comments sparingly, code should ideally be self-explanatory about what it does. Comments clarify non-obvious logic, assumptions, or reasoning.
- Docstrings: All public modules, functions, classes, and methods must have docstrings. Non-public methods should have docstrings if their purpose or logic is not immediately obvious.
- Docstrings Style: Use Google Style Docstrings.
- Docstring vs. Comments: Docstrings must describe the object's purpose and usage (the _what_), while comments should explain implementation details (the _why_ or complex _how_).
- One-Line Docstrings: Must be concise, use the imperative mood (e.g., `"""Return the sum."""`).
- Multi-Line Docstrings: Must start with a concise summary line, followed by a blank line, then a more detailed description.
- Constructor Documentation: Class constructors (`__init__`) must be documented within their own docstring.
- Mood Consistency: Maintain a consistent mood (imperative or descriptive) for docstring summaries within a single file.
- TODO Comments: Use TODO comments to flag areas needing future attention.

## 5. Type Hints
- Function Signatures: Use type hints for all function and method parameters and return types except for `self` and `cls`.
- Void Functions: Functions/methods that do not explicitly return a value must be annotated with `-> None`.
- Protocol: Protocols must be typed as `typing.Protocol`; required methods use `...` as the body. Use Protocols to define application boundaries (ports).
- Protocol adapters: Implementations inherit the protocol and are marked `@final`.

## 6. Error Handling
- Use Exceptions: Use exceptions to signal errors, not return codes or `None`.
- Specific Exceptions: Catch specific exception types rather than using a bare `except:` clause.
- Custom Exceptions: Define custom exceptions for application-specific errors, inheriting from `Exception` or a more specific built-in exception.
- Custom Exception Naming: Custom exception class names must end with `Error`.
- Informative Messages: Provide clear and informative messages within exceptions.
- Avoid Silent Failures: Ensure errors are handled or propagated; avoid silently passing exceptions (e.g., using `except Exception: pass`).
- `assert` Usage: Use `assert` only for internal checks and invariants during development/testing, not for handling runtime errors or validating external input.
- Input Validation: Validate external input using conditional checks and raise appropriate exceptions (e.g., `ValueError`) upon failure.

## 7. Logging
- **Logger Instantiation**: Always retrieve logger instances using `logging.getLogger(__name__)`. This leverages the logger hierarchy and provides clear context for log messages.
- **Configuration**: Configure logging at the application's entry point (e.g., using `logging.basicConfig()` or `logging.config.dictConfig()`). Libraries should not configure logging themselves but expect the application to do so.
- **Appropriate Log Levels**: Use log levels semantically to convey the severity and nature of the logged event:
    - `DEBUG`: For detailed diagnostic information useful during development and troubleshooting.
    - `INFO`: For messages confirming that operations are proceeding as expected.
    - `WARNING`: To indicate potential issues or unexpected events that do not (yet) prevent the software from working as intended.
    - `ERROR`: For errors that prevented a specific operation from completing but allow the application to continue.
    - `CRITICAL`: For severe errors that might lead to the application's termination.
- **Logging Exceptions**: When logging an error that occurred due to an exception, prefer using `logger.exception("Descriptive message")` within an `except` block. This automatically includes traceback information. Alternatively, for `logger.error` or `logger.critical`, ensure `exc_info=True` is passed if inside an `except` block and traceback is desired.
- **Avoid Sensitive Information**: Ensure that no sensitive data (e.g., passwords, API keys, personal identifiable information) is logged. Review log messages carefully.
- **Message Clarity**: Log messages should be clear, concise, and provide sufficient context to understand the event without needing to read the source code. Include relevant identifiers or state where helpful.
- **Structured Logging (Consideration)**: For applications integrated with log management systems, consider adopting structured logging (e.g., outputting logs in JSON format) to facilitate easier parsing, searching, and analysis.

## 8. General Best Practices
- Immutability: Prefer immutable objects where possible. Be cautious with mutable default arguments in function definitions (use None and initialize within the function instead).
- Generators: Use generators (via yield) for memory-efficient iteration over large sequences.
- Context Managers: Use the with statement when working with resources that need cleanup (files, network connections, locks) to ensure they are managed correctly. Implement __enter__ and __exit__ or use contextlib for custom context managers.
- Data Structures: For complex data structures, strongly prefer using Pydantic models over plain dictionaries.

## 9. Testing
- Requirement: All new features and bug fixes must be accompanied by automated tests (unit, integration, etc.).
- Framework: Use Pytest as the standard testing framework.
- Fixtures: Utilize pytest fixtures for setting up and tearing down test preconditions (e.g., database connections, temporary files, object instances).
- Asynchronous Code: For testing async code, use the `pytest-asyncio` plugin and mark test functions with `@pytest.mark.asyncio`.
- Test Docstrings: Test functions must have docstrings clearly stating what scenario or behavior is being tested.
- Isolation: Ensure tests are independent and isolated from each other. Tests should not rely on the state or side effects of previously run tests.
- Mocking: `pytest-mock` is the preferred tool to isolate the code under test from external dependencies (e.g., databases, external APIs, filesystem).
- Coverage: Use `pytest-cov` to measure coverage.
