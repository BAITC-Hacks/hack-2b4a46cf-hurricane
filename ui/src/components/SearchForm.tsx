import { Trans, useLingui } from "@lingui/react/macro";
import { RotateCcw, Search, SlidersHorizontal } from "lucide-react";
import { useState, type FormEvent } from "react";

import type { Schemas } from "@/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/components/ui/combobox";

export type SearchFilters = Schemas["RecommendIn"];
type CatalogOptions = Schemas["CatalogOptionsOut"];
type Option = Schemas["OptionOut"];

// Prices differ 60x between gifts and banquet halls, so presets follow each category's catalog range.
const budgetPresets: Partial<Record<SearchFilters["category"], number[]>> = {
  host: [600_000, 1_000_000, 1_500_000, 2_000_000],
  "ceremony-host": [200_000, 250_000],
  photographer: [200_000, 300_000, 450_000, 600_000],
  videographer: [300_000, 500_000, 800_000],
  "photo-booth": [300_000, 400_000, 450_000],
  florist: [200_000, 250_000, 300_000],
  decorator: [1_800_000, 2_000_000, 2_200_000],
  gifts: [100_000, 150_000],
  "live-band": [800_000, 1_000_000, 1_500_000],
  instrumentalist: [350_000, 450_000, 500_000],
  "national-ensemble": [400_000, 500_000],
  "dance-group": [400_000, 500_000],
  show: [400_000, 500_000],
  "banquet-hall": [2_000_000, 3_000_000, 4_500_000, 6_000_000],
  restaurant: [2_000_000, 3_000_000, 4_500_000, 6_000_000],
  hotel: [3_000_000, 4_500_000, 6_000_000],
  "country-venue": [2_500_000, 3_000_000, 4_000_000],
};

function getInitialFilters(options: CatalogOptions): SearchFilters {
  return {
    city: options.cities[0].value as SearchFilters["city"],
    event_date: options.date_from,
    event_format: options.event_formats[0].value as SearchFilters["event_format"],
    category: options.categories[0].value as SearchFilters["category"],
    budget_kzt: 1_500_000,
    duration_hours: null,
    languages: [],
  };
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
  anyLabel,
}: {
  label: string;
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  anyLabel?: string;
}) {
  const items = anyLabel ? [{ value: "any", label: anyLabel }, ...options] : options;

  return (
    <label className="grid min-w-0 gap-2 text-sm font-medium">
      {label}
      <Combobox
        items={items}
        value={items.find((option) => option.value === value) ?? null}
        onValueChange={(selected) => selected && onChange(selected.value)}
        itemToStringLabel={(option) => option.label}
        itemToStringValue={(option) => option.value}
      >
        <ComboboxInput className="h-10 w-full bg-background text-sm max-md:h-11" />
        <ComboboxContent>
          <ComboboxEmpty>
            <Trans>Ничего не найдено</Trans>
          </ComboboxEmpty>
          <ComboboxList>
            {(option: Option) => (
              <ComboboxItem key={option.value} value={option} className="min-h-11 px-3">
                {option.label}
              </ComboboxItem>
            )}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>
    </label>
  );
}

export function SearchForm({
  options,
  onSearch,
}: {
  options: CatalogOptions;
  onSearch: (filters: SearchFilters) => void;
}) {
  const { t, i18n } = useLingui();
  const compactKzt = new Intl.NumberFormat(i18n.locale, { notation: "compact" });
  const [filters, setFilters] = useState<SearchFilters>(() => getInitialFilters(options));

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSearch(filters);
  }

  return (
    <Card className="rounded-lg border border-border bg-card py-6 ring-0 [--card-spacing:--spacing(6)] max-md:py-4 max-md:[--card-spacing:--spacing(4)]">
      <CardContent>
        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className="grid grid-cols-3 gap-3 max-md:grid-cols-1">
            <FilterSelect
              label={t`Город`}
              value={filters.city}
              options={options.cities}
              onChange={(city) => setFilters({ ...filters, city: city as SearchFilters["city"] })}
            />
            <label className="grid min-w-0 gap-2 text-sm font-medium">
              <Trans>Дата</Trans>
              <input
                type="date"
                required
                min={options.date_from}
                max={options.date_to}
                value={filters.event_date}
                onChange={(event) => setFilters({ ...filters, event_date: event.target.value })}
                className="h-10 min-w-0 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 max-md:h-11"
              />
            </label>
            <FilterSelect
              label={t`Формат`}
              value={filters.event_format}
              options={options.event_formats}
              onChange={(event_format) =>
                setFilters({
                  ...filters,
                  event_format: event_format as SearchFilters["event_format"],
                })
              }
            />
            <FilterSelect
              label={t`Категория`}
              value={filters.category}
              options={options.categories}
              onChange={(category) =>
                setFilters({ ...filters, category: category as SearchFilters["category"] })
              }
            />
            <div className="grid content-start gap-2">
              <label className="grid min-w-0 gap-2 text-sm font-medium">
                <Trans>Бюджет, ₸</Trans>
                <input
                  type="number"
                  required
                  min="1"
                  max="50000000"
                  step="1"
                  inputMode="numeric"
                  value={filters.budget_kzt}
                  onChange={(event) =>
                    setFilters({ ...filters, budget_kzt: Number(event.target.value) })
                  }
                  className="h-10 min-w-0 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 max-md:h-11"
                />
              </label>
              <div className="flex flex-wrap gap-1.5">
                {(budgetPresets[filters.category] ?? []).map((amount) => (
                  <Button
                    key={amount}
                    type="button"
                    variant={filters.budget_kzt === amount ? "secondary" : "outline"}
                    aria-pressed={filters.budget_kzt === amount}
                    size="sm"
                    onClick={() => setFilters({ ...filters, budget_kzt: amount })}
                    className="rounded-full max-md:h-9"
                  >
                    {t`до ${compactKzt.format(amount)} ₸`}
                  </Button>
                ))}
              </div>
            </div>
          </div>
          <details className="group border-t border-border pt-2">
            <summary className="flex min-h-10 cursor-pointer list-none items-center gap-2 text-sm font-medium max-md:min-h-11 [&::-webkit-details-marker]:hidden">
              <SlidersHorizontal className="size-4 text-muted-foreground" />
              <Trans>Дополнительные условия</Trans>
              <span className="ml-auto text-xs text-muted-foreground group-open:rotate-180">⌄</span>
            </summary>
            <div className="grid grid-cols-2 gap-3 pb-3 max-md:grid-cols-1">
              <label className="grid min-w-0 gap-2 text-sm font-medium">
                <Trans>Длительность, ч</Trans>
                <input
                  type="number"
                  min="1"
                  max="24"
                  inputMode="numeric"
                  placeholder={t`Не важно`}
                  value={filters.duration_hours ?? ""}
                  onChange={(event) =>
                    setFilters({
                      ...filters,
                      duration_hours: event.target.value ? Number(event.target.value) : null,
                    })
                  }
                  className="h-10 min-w-0 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 max-md:h-11"
                />
              </label>
              <FilterSelect
                label={t`Язык работы`}
                value={filters.languages?.[0] ?? "any"}
                options={options.languages}
                anyLabel={t`Не важно`}
                onChange={(language) =>
                  setFilters({
                    ...filters,
                    languages: language === "any" ? [] : [language as Schemas["Language"]],
                  })
                }
              />
            </div>
          </details>
          <div className="flex items-center gap-3 max-md:flex-col max-md:items-stretch">
            <Button type="submit" size="lg" className="h-10 px-6 max-md:h-11 max-md:w-full">
              <Search className="size-4" />
              <Trans>Подобрать</Trans>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="lg"
              onClick={() => setFilters(getInitialFilters(options))}
              className="h-10 px-6 max-md:h-11 max-md:w-full"
            >
              <RotateCcw className="size-4" />
              <Trans>Сбросить фильтры</Trans>
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
