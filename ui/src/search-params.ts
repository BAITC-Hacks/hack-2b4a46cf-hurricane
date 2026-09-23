/** Filters <-> URL search params, shared by the search form and the results page. */
import type { Schemas } from "@/api";

type SearchFilters = Schemas["RecommendIn"];

export function validateSearchParams(search: Record<string, unknown>) {
  return {
    city: typeof search.city === "string" ? search.city.trim() : "",
    event_date: typeof search.event_date === "string" ? search.event_date.trim() : "",
    event_format: typeof search.event_format === "string" ? search.event_format.trim() : "",
    category: typeof search.category === "string" ? search.category.trim() : "",
    budget_kzt: Number(search.budget_kzt),
    ...(search.duration_hours ? { duration_hours: Number(search.duration_hours) } : {}),
    ...(typeof search.languages === "string" && search.languages
      ? { languages: search.languages.trim() }
      : {}),
  };
}

export type SearchParams = ReturnType<typeof validateSearchParams>;

export function getSearchFilters(search: Partial<SearchParams>): SearchFilters | null {
  if (!search.city || !search.event_date || !search.event_format || !search.category) return null;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(search.event_date)) return null;
  if (!Number.isInteger(search.budget_kzt) || !search.budget_kzt || search.budget_kzt < 1)
    return null;
  if (
    search.duration_hours &&
    (!Number.isInteger(search.duration_hours) || search.duration_hours < 1)
  )
    return null;
  return {
    city: search.city as SearchFilters["city"],
    event_date: search.event_date,
    event_format: search.event_format as SearchFilters["event_format"],
    category: search.category as SearchFilters["category"],
    budget_kzt: search.budget_kzt,
    duration_hours: search.duration_hours ?? null,
    languages: search.languages ? (search.languages.split(",") as Schemas["Language"][]) : [],
  };
}

export function getSearchParams(filters: SearchFilters): SearchParams {
  return {
    city: filters.city,
    event_date: filters.event_date,
    event_format: filters.event_format,
    category: filters.category,
    budget_kzt: filters.budget_kzt,
    ...(filters.duration_hours ? { duration_hours: filters.duration_hours } : {}),
    ...(filters.languages?.length ? { languages: filters.languages.join(",") } : {}),
  };
}
