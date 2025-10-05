// @ts-check
import js from "@eslint/js";
import prettierPlugin from "eslint-plugin-prettier";
import globals from "globals";
import tseslint from "typescript-eslint";

export default [
  // Base ESLint recommended configuration
  js.configs.recommended,

  // TypeScript configuration
  ...tseslint.configs.recommended,

  // Global settings for all files
  {
    files: ["**/*.{js,ts}"],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: "module",
      globals: {
        ...globals.node,
        ...globals.es2021,
      },
    },
    settings: {
      "import/resolver": {
        node: {
          extensions: [".js", ".ts", ".mjs", ".cjs"],
        },
      },
    },
    linterOptions: {
      reportUnusedDisableDirectives: true,
    },
  },

  // TypeScript-specific configs
  {
    files: ["**/*.ts"],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaVersion: 2021,
        sourceType: "module",
      },
    },
  },

  // Global rules for all files
  {
    files: ["**/*.{js,ts}"],
    plugins: {
      typescript: tseslint.plugin,
      prettier: prettierPlugin,
    },
    rules: {
      "prettier/prettier": "error",
      "typescript/no-unused-vars": "warn",
      "typescript/no-explicit-any": "warn",
      "no-restricted-imports": [
        "warn",
        {
          patterns: ["~*"],
        },
      ],
      "no-console": "error",
      quotes: ["error", "double", { avoidEscape: true }],
      semi: ["error", "always"],
    },
  },

  // File-specific overrides
  {
    files: ["test/**"],
    rules: {
      "no-console": "off",
    },
  },
];
