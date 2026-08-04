import createFetchClient from "openapi-fetch";
import createClient from "openapi-react-query";
import { paths } from "./backend-schema";

const fetchClient = createFetchClient<paths>({
  baseUrl: import.meta.env.VITE_BACKEND_URL || "http://localhost:3010",
  credentials: "include",
});

export const $api = createClient(fetchClient);
