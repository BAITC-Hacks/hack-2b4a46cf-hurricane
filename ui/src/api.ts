import createClient from "openapi-fetch";

import type { components, paths } from "./api-types";

export type Schemas = components["schemas"];

export const client = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
});

type Result<T> = { data?: T; error?: unknown; response: Response };

/** Backend errors arrive as `{ detail: string }` (AppError) or a 422 validation list. */
export function unwrap<T>({ data, error, response }: Result<T>): T {
  if (data !== undefined) return data;
  const detail = (error as { detail?: unknown } | undefined)?.detail;
  throw new Error(typeof detail === "string" ? detail : response.statusText || "Request failed");
}
