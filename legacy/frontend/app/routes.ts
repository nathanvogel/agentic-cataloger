import {
  type RouteConfig,
  index,
  layout,
  route,
} from "@react-router/dev/routes";

export default [
  layout("routes/_layout.tsx", [
    index("routes/landingpage.tsx"),
    route("terms", "routes/terms.tsx"),
  ]),
] satisfies RouteConfig;
