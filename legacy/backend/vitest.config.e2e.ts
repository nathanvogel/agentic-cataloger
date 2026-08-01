import { defineConfig } from "vitest/config";
import { resolve } from "path";
import swc from "unplugin-swc";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["test/**/*.e2e-spec.ts"],
    setupFiles: ["./vitest.setup.ts"],
  },
  plugins: [swc.vite()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "./src"),
    },
  },
});
