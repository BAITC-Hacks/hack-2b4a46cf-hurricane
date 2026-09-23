import { Trans, useLingui } from "@lingui/react/macro";
import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, LoaderCircle, SearchX } from "lucide-react";

import { fetchCatalogOptions, fetchRecommendations, type Schemas } from "@/api";
import { buttonVariants } from "@/components/ui/button";
import { VendorCard } from "@/components/VendorCard";

type SearchFilters = Schemas["RecommendIn"];

function validateSearch(search: Record<string, unknown>) {
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

export const Route = createFileRoute("/results")({
  validateSearch,
  component: ResultsPage,
});

function getFilters(search: ReturnType<typeof validateSearch>): SearchFilters | null {
  if (!search.city || !search.event_date || !search.event_format || !search.category) return null;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(search.event_date)) return null;
  if (!Number.isInteger(search.budget_kzt) || search.budget_kzt < 1) return null;
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

function ResultsPage() {
  const { t } = useLingui();
  const rejectionLabels: Record<Schemas["RejectionOut"]["reason"], string> = {
    busy: t`заняты на дату`,
    format: t`не работают в этом формате`,
    budget: t`дороже бюджета`,
    duration: t`не подходят по длительности`,
    language: t`не работают на выбранном языке`,
  };
  const search = Route.useSearch();
  const filters = getFilters(search);
  const options = useQuery({ queryKey: ["catalog", "options"], queryFn: fetchCatalogOptions });
  const recommendation = useQuery({
    queryKey: ["recommend", filters],
    queryFn: () => fetchRecommendations(filters!),
    enabled: filters !== null,
    retry: false,
  });

  function getLabel(values: Schemas["OptionOut"][] | undefined, value: string) {
    return values?.find((option) => option.value === value)?.label ?? value;
  }

  const summary = filters
    ? [
        getLabel(options.data?.cities, filters.city),
        getLabel(options.data?.event_formats, filters.event_format),
        getLabel(options.data?.categories, filters.category),
        filters.event_date.split("-").reverse().join("."),
        `${new Intl.NumberFormat("ru-RU").format(filters.budget_kzt)} ₸`,
      ]
    : [];

  return (
    <div className="grid gap-6 pb-12">
      <Link
        to="/"
        className="flex min-h-10 w-fit items-center gap-2 text-sm text-link hover:underline max-md:min-h-11"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        <Trans>Изменить фильтры</Trans>
      </Link>
      <header className="grid gap-2">
        <h1 className="text-2xl font-semibold max-md:text-xl">
          <Trans>Подбор подрядчиков</Trans>
        </h1>
        {filters && <p className="text-sm text-muted-foreground">{summary.join(" · ")}</p>}
      </header>
      {!filters ? (
        <div className="grid justify-items-center gap-3 rounded-lg border border-border bg-card p-8 text-center">
          <SearchX className="size-10 text-muted-foreground" aria-hidden="true" />
          <p className="font-semibold">
            <Trans>В ссылке не хватает параметров поиска</Trans>
          </p>
          <p className="text-sm text-muted-foreground">
            <Trans>Выберите фильтры на главной странице и создайте новую ссылку.</Trans>
          </p>
        </div>
      ) : recommendation.isPending ? (
        <div className="flex min-h-48 items-center gap-3 rounded-lg border border-border bg-card p-6">
          <LoaderCircle className="size-5 animate-spin" aria-hidden="true" />
          <p className="text-sm">
            <Trans>Подбираю подрядчиков…</Trans>
          </p>
        </div>
      ) : recommendation.isError ? (
        <div className="grid gap-3 rounded-lg border border-border bg-card p-6">
          <p className="text-sm text-destructive">
            <Trans>Не удалось подобрать подрядчиков. Проверьте фильтры и попробуйте ещё раз.</Trans>
          </p>
          <button
            type="button"
            onClick={() => recommendation.refetch()}
            className={buttonVariants({
              variant: "outline",
              className: "min-h-10 w-fit max-md:min-h-11 max-md:w-full",
            })}
          >
            <Trans>Повторить</Trans>
          </button>
        </div>
      ) : (
        <section className="grid gap-5" aria-live="polite">
          {recommendation.data.cards.length > 0 ? (
            <>
              <h2 className="text-xl font-semibold">
                <Trans>Подходящие подрядчики</Trans>
              </h2>
              <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
                {recommendation.data.cards.map((vendor) => (
                  <VendorCard key={vendor.id} vendor={vendor} />
                ))}
              </div>
            </>
          ) : (
            <div className="grid justify-items-center gap-2 rounded-lg border border-border bg-card p-8 text-center">
              <SearchX className="size-10 text-muted-foreground" aria-hidden="true" />
              <h2 className="text-base font-semibold">
                {recommendation.data.outcome === "no_category_in_city"
                  ? t`В этом городе нет подрядчиков выбранной категории`
                  : t`По этим условиям подрядчиков не нашлось`}
              </h2>
              <p className="text-sm text-muted-foreground">
                <Trans>Попробуйте изменить дату, бюджет или город.</Trans>
              </p>
            </div>
          )}
          {recommendation.data.rejections.length > 0 && (
            <p className="text-sm text-muted-foreground">
              <Trans>
                Не прошли фильтры:{" "}
                {recommendation.data.rejections
                  .map(({ reason, count }) => `${rejectionLabels[reason]}: ${count}`)
                  .join(", ")}
              </Trans>
            </p>
          )}
          {recommendation.data.suggestions.length > 0 && (
            <div className="grid gap-3">
              <h2 className="text-base font-semibold">
                <Trans>Попробуйте другие условия</Trans>
              </h2>
              <div className="flex flex-wrap gap-2">
                {recommendation.data.suggestions.map((suggestion, index) => (
                  <Link
                    key={index}
                    to="/results"
                    search={{
                      ...search,
                      ...(suggestion.event_date ? { event_date: suggestion.event_date } : {}),
                      ...(suggestion.budget_kzt ? { budget_kzt: suggestion.budget_kzt } : {}),
                      ...(suggestion.city ? { city: suggestion.city } : {}),
                    }}
                    className={buttonVariants({
                      variant: "outline",
                      className: "min-h-10 max-md:min-h-11 max-md:w-full",
                    })}
                  >
                    {suggestion.kind === "date"
                      ? t`Дата: ${suggestion.event_date}`
                      : suggestion.kind === "budget"
                        ? t`Бюджет: ${suggestion.budget_kzt} ₸`
                        : t`Город: ${getLabel(options.data?.cities, suggestion.city ?? "")}`}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
