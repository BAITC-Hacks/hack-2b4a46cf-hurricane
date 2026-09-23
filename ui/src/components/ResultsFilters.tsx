import { Trans, useLingui } from "@lingui/react/macro";
import { ChevronDown, SlidersHorizontal } from "lucide-react";

import type { Schemas } from "@/api";
import { SearchForm, type SearchFilters } from "@/components/SearchForm";
import { Button } from "@/components/ui/button";
import { formatEventDate } from "@/i18n";

type OptionKind = "cities" | "event_formats" | "categories" | "languages";

export function ResultsFilters({
  options,
  filters,
  formKey,
  isOpen,
  onToggle,
  onSearch,
  getLabel,
}: {
  options: Schemas["CatalogOptionsOut"] | undefined;
  filters: SearchFilters;
  formKey: string;
  isOpen: boolean;
  onToggle: () => void;
  onSearch: (filters: SearchFilters) => void;
  getLabel: (kind: OptionKind, value: string) => string;
}) {
  const { t, i18n } = useLingui();
  const summary = [
    getLabel("cities", filters.city),
    getLabel("event_formats", filters.event_format),
    getLabel("categories", filters.category),
    formatEventDate(filters.event_date, i18n.locale),
    `${new Intl.NumberFormat(i18n.locale).format(filters.budget_kzt)} ₸`,
    ...(filters.duration_hours ? [t`до ${filters.duration_hours} ч`] : []),
    ...(filters.languages ?? []).map((language) => getLabel("languages", language)),
  ];

  return (
    <div className="grid gap-4">
      <div className="flex items-start justify-between gap-3 max-md:flex-col">
        <ul className="flex flex-wrap gap-1.5" aria-label={t`Выбранные фильтры`}>
          {summary.map((label) => (
            <li
              key={label}
              className="cursor-default rounded-md bg-muted px-2 py-0.5 text-sm text-foreground select-none"
            >
              {label}
            </li>
          ))}
        </ul>
        <Button
          type="button"
          variant="outline"
          aria-expanded={isOpen}
          disabled={!options}
          onClick={onToggle}
          className="h-10 shrink-0 gap-2 px-4 transition active:scale-[0.98] max-md:h-12 max-md:w-full"
        >
          <SlidersHorizontal className="size-4" aria-hidden="true" />
          {isOpen ? <Trans>Скрыть фильтры</Trans> : <Trans>Изменить фильтры</Trans>}
          <ChevronDown
            className={`size-4 transition ${isOpen ? "rotate-180" : ""}`}
            aria-hidden="true"
          />
        </Button>
      </div>
      {isOpen && options && (
        <SearchForm key={formKey} options={options} defaultFilters={filters} onSearch={onSearch} />
      )}
    </div>
  );
}
