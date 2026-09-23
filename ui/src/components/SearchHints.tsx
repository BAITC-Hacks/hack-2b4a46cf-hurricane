import { plural } from "@lingui/core/macro";
import { Trans, useLingui } from "@lingui/react/macro";
import { Link } from "@tanstack/react-router";
import { CalendarDays, Clock, Languages, MapPin, Wallet, type LucideIcon } from "lucide-react";

import type { Schemas } from "@/api";
import { buttonVariants } from "@/components/ui/button";
import { formatEventDate } from "@/i18n";
import type { SearchParams } from "@/search-params";

type Recommendation = Schemas["RecommendOut"];
type Filters = Schemas["RecommendIn"];

interface Hint {
  key: string;
  icon: LucideIcon;
  title: string;
  detail: string;
  search: SearchParams;
}

function getVendorCount(count: number) {
  return plural(count, {
    one: "# подрядчик",
    few: "# подрядчика",
    many: "# подрядчиков",
    other: "# подрядчика",
  });
}

export function SearchHints({
  recommendation,
  filters,
  search,
  getLabel,
}: {
  recommendation: Recommendation;
  filters: Filters;
  search: SearchParams;
  getLabel: (kind: "cities" | "event_formats" | "languages", value: string) => string;
}) {
  const { t, i18n } = useLingui();
  const money = new Intl.NumberFormat(i18n.locale);
  const date = formatEventDate(filters.event_date, i18n.locale);
  const languages = (filters.languages ?? []).map((value) => getLabel("languages", value));
  const format = getLabel("event_formats", filters.event_format);

  const reasons: Record<Schemas["RejectionOut"]["reason"], (count: number) => string> = {
    busy: (count) => t`Заняты ${date}: ${getVendorCount(count)}.`,
    format: (count) => t`Не берут формат «${format}»: ${getVendorCount(count)}.`,
    budget: (count) =>
      t`Цена от выше ${money.format(filters.budget_kzt)} ₸: ${getVendorCount(count)}.`,
    duration: (count) =>
      t`Указанный предел работы меньше ${filters.duration_hours ?? 0} ч: ${getVendorCount(count)}.`,
    language: (count) => t`Не ведут на языках ${languages.join(", ")}: ${getVendorCount(count)}.`,
  };

  const shouldShowCount = recommendation.pool_size > 0 && recommendation.passed_count < 3;
  const hints: Hint[] = recommendation.suggestions.map((suggestion, index) => {
    const found = t`найдётся ${getVendorCount(suggestion.count)}`;
    if (suggestion.kind === "date" && suggestion.event_date)
      return {
        key: `date-${index}`,
        icon: CalendarDays,
        title: formatEventDate(suggestion.event_date, i18n.locale),
        detail: found,
        search: { ...search, event_date: suggestion.event_date },
      };
    if (suggestion.kind === "budget" && suggestion.budget_kzt)
      return {
        key: `budget-${index}`,
        icon: Wallet,
        title: t`Бюджет ${money.format(suggestion.budget_kzt)} ₸`,
        detail: found,
        search: { ...search, budget_kzt: suggestion.budget_kzt },
      };
    return {
      key: `city-${index}`,
      icon: MapPin,
      title: getLabel("cities", suggestion.city ?? ""),
      detail: found,
      search: { ...search, city: suggestion.city ?? search.city },
    };
  });
  const rejectedBy = new Set(recommendation.rejections.map((rejection) => rejection.reason));
  if (rejectedBy.has("language") && languages.length) {
    hints.push({
      key: "languages",
      icon: Languages,
      title: t`Любой язык`,
      detail: t`убрать требование к языку`,
      search: { ...search, languages: undefined },
    });
  }
  if (rejectedBy.has("duration") && filters.duration_hours) {
    hints.push({
      key: "duration",
      icon: Clock,
      title: t`Любая длительность`,
      detail: t`не ограничивать часы`,
      search: { ...search, duration_hours: undefined },
    });
  }

  return (
    <>
      {shouldShowCount && (
        <section className="grid gap-3 rounded-lg border border-border bg-card p-5 max-md:p-4">
          <h2 className="text-base font-semibold">
            {recommendation.passed_count === recommendation.pool_size
              ? t`В ${getLabel("cities", filters.city)} в этой категории всего ${getVendorCount(recommendation.pool_size)}. Все подходят.`
              : t`Подходят ${recommendation.passed_count} из ${recommendation.pool_size} профилей в ${getLabel("cities", filters.city)}.`}
          </h2>
          {recommendation.rejections.length > 0 && (
            <ul className="grid gap-2 text-sm leading-6 text-muted-foreground">
              {recommendation.rejections.map(({ reason, count }) => (
                <li key={reason}>{reasons[reason](count)}</li>
              ))}
            </ul>
          )}
        </section>
      )}
      {hints.length > 0 && (
        <section className="grid gap-3">
          <h2 className="text-base font-semibold">
            <Trans>Попробуйте другие условия</Trans>
          </h2>
          <div className="grid grid-cols-3 gap-2 max-md:grid-cols-1">
            {hints.map((hint) => (
              <Link
                key={hint.key}
                to="/results"
                search={hint.search}
                className={buttonVariants({
                  variant: "outline",
                  className:
                    "h-auto min-h-12 justify-start gap-3 px-4 py-2 text-left transition hover:border-foreground/30 hover:bg-accent active:scale-[0.98] max-md:min-h-14",
                })}
              >
                <hint.icon className="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
                <span className="grid">
                  <span className="text-sm font-semibold">{hint.title}</span>
                  <span className="text-xs font-normal text-muted-foreground">{hint.detail}</span>
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
