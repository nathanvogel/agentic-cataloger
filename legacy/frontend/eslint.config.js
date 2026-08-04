// eslint.config.js
import js from "@eslint/js";
import i18nextPlugin from "eslint-plugin-i18next";
import importPlugin from "eslint-plugin-import";
import prettierPlugin from "eslint-plugin-prettier";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import globals from "globals";
import typescript from "typescript-eslint";

// Create flat config format
export default [
  // Base ESLint recommended configuration
  js.configs.recommended,

  // TypeScript configuration
  ...typescript.configs.recommended,

  // Global settings for all files
  {
    files: ["**/*.{js,jsx,ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.es2021,
        ...globals.node,
      },
    },
    settings: {
      react: {
        version: "detect",
      },
      "import/resolver": {
        node: {
          extensions: [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"],
        },
      },
    },
    linterOptions: {
      reportUnusedDisableDirectives: true,
    },
  },

  // TypeScript-specific configs
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: typescript.parser,
      parserOptions: {
        ecmaVersion: 12,
        sourceType: "module",
      },
    },
  },

  // React configs
  {
    files: ["**/*.{jsx,tsx}"],
    plugins: {
      react: reactPlugin,
    },
    rules: {
      ...reactPlugin.configs.recommended.rules,
      "react/prop-types": "off",
      "react/display-name": "off",
      ...reactPlugin.configs["jsx-runtime"].rules,
    },
  },

  // React hooks configs
  {
    files: ["**/*.{jsx,tsx}"],
    plugins: {
      "react-hooks": reactHooksPlugin,
    },
    rules: {
      ...reactHooksPlugin.configs.recommended.rules,
      "react-hooks/exhaustive-deps": "error",
      "react-hooks/rules-of-hooks": "error",
    },
  },

  // Global rules for all files
  {
    files: ["**/*.{js,jsx,ts,tsx}"],
    plugins: {
      typescript: typescript.plugin,
      import: importPlugin,
      prettier: prettierPlugin,
      i18next: i18nextPlugin,
    },
    rules: {
      "prettier/prettier": "error",
      "import/imports-first": "warn",
      "import/newline-after-import": "warn",
      "import/no-duplicates": "warn",
      "import/first": "warn",
      "typescript/no-unused-vars": "warn",
      "typescript/no-explicit-any": "warn",
      "no-restricted-imports": [
        "warn",
        {
          patterns: ["~*"],
        },
      ],
      "no-console": "error",
      "i18next/no-literal-string": "off",
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
