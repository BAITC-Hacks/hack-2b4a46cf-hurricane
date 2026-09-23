import { Trans, useLingui } from "@lingui/react/macro";
import { useQuery } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { LoaderCircle, SearchX } from "lucide-react";
import { useState } from "react";

import { fetchCatalogOptions, fetchRecommendations, type Schemas } from "@/api";
import { ResultsFilters } from "@/components/ResultsFilters";
import { SearchForm, type SearchFilters } from "@/components/SearchForm";
import { SearchHints } from "@/components/SearchHints";
import { buttonVariants } from "@/components/ui/button";
import { VendorCard, VendorCardSkeleton } from "@/components/VendorCard";
import { formatEventDate } from "@/i18n";
import { getSearchFilters, getSearchParams, validateSearchParams } from "@/search-params";

type OptionKind = "cities" | "event_formats" | "categories" | "languages";
type VendorCardOut = Schemas["VendorCardOut"];

// Pricing-page order: cheapest on the left, the highlighted pick in the middle, premium on the right.
const roleOrder: Record<VendorCardOut["role"], number> = {
  best_price: 0,
  best_match: 1,
  alternative: 2,
  premium: 3,
};

function sortCardsByRole(cards: VendorCardOut[]): VendorCardOut[] {
  return [...cards].sort((a, b) => roleOrder[a.role] - roleOrder[b.role]);
}

// An incomplete row stays centered instead of stretching one card across the screen.
function getCardsGridClassName(count: number): string {
  if (count >= 3) return "grid grid-cols-3 gap-4 max-md:grid-cols-1";
  if (count === 2) return "mx-auto grid w-full max-w-4xl grid-cols-2 gap-4 max-md:grid-cols-1";
  return "mx-auto grid w-full max-w-xl grid-cols-1 gap-4";
}

export const Route = createFileRoute("/results")({
  validateSearch: validateSearchParams,
  component: ResultsPage,
});

function ResultsPage() {
  const { t, i18n } = useLingui();
  const navigate = useNavigate();
  const search = Route.useSearch();
  const filters = getSearchFilters(search);
  const formKey = JSON.stringify(search);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const options = useQuery({ queryKey: ["catalog", "options"], queryFn: fetchCatalogOptions });
  const recommendation = useQuery({
    queryKey: ["recommend", filters],
    queryFn: () => fetchRecommendations(filters!),
    enabled: filters !== null,
    retry: false,
  });
  const isEmpty = recommendation.isSuccess && recommendation.data.cards.length === 0;

  function getLabel(kind: OptionKind, value: string) {
    return options.data?.[kind].find((option) => option.value === value)?.label ?? value;
  }

  // Re-search stays on this page: the URL changes in place so browser Back still returns home.
  function handleSearch(nextFilters: SearchFilters) {
    setIsFormOpen(false);
    navigate({ to: "/results", search: getSearchParams(nextFilters), replace: true });
  }

  // The empty screen names the blocking condition and the way out, not a generic "try again".
  function getEmptyStateHint(recommendation: Schemas["RecommendOut"]) {
    if (!filters) return "";
    if (recommendation.outcome === "no_category_in_city")
      return recommendation.suggestions.length > 0
        ? t`В других городах эта категория есть, подсказки ниже.`
        : t`Такой категории нет ни в одном городе каталога.`;
    const top = [...recommendation.rejections].sort((a, b) => b.count - a.count)[0];
    if (!top) return t`Попробуйте изменить дату, бюджет или город.`;
    const date = formatEventDate(filters.event_date, i18n.locale);
    const format = getLabel("event_formats", filters.event_format);
    const budget = new Intl.NumberFormat(i18n.locale).format(filters.budget_kzt);
    const hints: Record<Schemas["RejectionOut"]["reason"], string> = {
      busy: t`На ${date} в этой категории все заняты. Соседние даты ниже.`,
      format: t`Формат «${format}» здесь никто из этой категории не берёт. Попробуйте другой город.`,
      budget: t`Все варианты дороже ${budget} ₸. Подсказка по бюджету ниже.`,
      duration: t`Никто не работает ${filters.duration_hours ?? 0} ч подряд. Уберите ограничение по часам.`,
      language: t`Никто не ведёт на выбранных языках. Уберите требование к языку.`,
    };
    return hints[top.reason];
  }

  return (
    <div className="grid gap-6 pb-12">
      {filters && !isEmpty && (
        <ResultsFilters
          options={options.data}
          filters={filters}
          formKey={formKey}
          isOpen={isFormOpen}
          onToggle={() => setIsFormOpen(!isFormOpen)}
          onSearch={handleSearch}
          getLabel={getLabel}
        />
      )}
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
        <section className="grid gap-5" aria-busy="true">
          <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
            <LoaderCircle className="size-5 animate-spin" aria-hidden="true" />
            <Trans>Подбираю подрядчиков…</Trans>
          </p>
          <div className={getCardsGridClassName(3)}>
            {Array.from({ length: 3 }, (_, index) => (
              <VendorCardSkeleton key={index} />
            ))}
          </div>
        </section>
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
              className: "h-10 w-fit transition active:scale-[0.98] max-md:h-12 max-md:w-full",
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
              <div className={getCardsGridClassName(recommendation.data.cards.length)}>
                {sortCardsByRole(recommendation.data.cards).map((vendor) => (
                  <VendorCard key={vendor.id} vendor={vendor} />
                ))}
              </div>
            </>
          ) : (
            <>
              <div className="grid justify-items-center gap-2 rounded-lg border border-border bg-card p-8 text-center">
                <SearchX className="size-10 text-muted-foreground" aria-hidden="true" />
                <h2 className="text-base font-semibold">
                  {recommendation.data.outcome === "no_category_in_city"
                    ? t`В этом городе нет подрядчиков выбранной категории`
                    : t`По этим условиям подрядчиков не нашлось`}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {getEmptyStateHint(recommendation.data)}
                </p>
              </div>
              {/* Nothing found: the form is open right here so the fix does not need a page change. */}
              {options.data && (
                <SearchForm
                  key={formKey}
                  options={options.data}
                  defaultFilters={filters}
                  onSearch={handleSearch}
                />
              )}
            </>
          )}
          <SearchHints
            recommendation={recommendation.data}
            filters={filters}
            search={search}
            getLabel={getLabel}
          />
        </section>
      )}
    </div>
  );
}
