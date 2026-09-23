import createClient from "openapi-fetch";

import type { components, paths } from "./api-types";

type Schemas = components["schemas"];

const client = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
});

type Result<T> = { data?: T; error?: unknown; response: Response };

/** Backend errors arrive as `{ detail: string }` (AppError) or a 422 validation list. */
function unwrap<T>({ data, error, response }: Result<T>): T {
  if (data !== undefined) return data;
  const detail = (error as { detail?: unknown } | undefined)?.detail;
  throw new Error(typeof detail === "string" ? detail : response.statusText || "Request failed");
}

export async function fetchHealth(): Promise<Schemas["HealthOut"]> {
  return unwrap(await client.GET("/health"));
}

export async function askLlm(prompt: string): Promise<Schemas["AskOut"]> {
  return unwrap(await client.POST("/ask", { body: { prompt } }));
}
