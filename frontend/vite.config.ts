import { reactRouter } from "@react-router/dev/vite";
import basicSsl from "@vitejs/plugin-basic-ssl";
import { defineConfig } from "vite";
import devtoolsJson from "vite-plugin-devtools-json";

export default defineConfig(() => {
  const plugins = [reactRouter(), devtoolsJson()];
  if (process.env.USE_DEV_SSL === "true") {
    plugins.push(
      basicSsl({
        name: "frontend-test-cert",
      })
    );
  }
  return {
    plugins: plugins,
    ssr: {
      noExternal: ["@emotion/*"],
    },
    resolve: {
      alias: [
        {
          find: /^@mui\/material\/([^/]+)\/index\.js$/,
          replacement: "@mui/material/$1",
        },
      ],
    },
    server: {
      port: 3023,
      allowedHosts: [
        "petittonnerrelinux",
        "petittonnerrelinux.opossum-climb.ts.net",
        "fd7a:115c:a1e0::d033:5776",
      ],
    },
  };
});
