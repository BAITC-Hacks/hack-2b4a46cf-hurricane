import { Trans, useLingui } from "@lingui/react/macro";
import { RotateCcw, Search, SlidersHorizontal } from "lucide-react";
import { useState, type FormEvent } from "react";

import type { Schemas } from "@/api";
import { LanguageCombobox } from "@/components/LanguageCombobox";
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
import { Slider } from "@/components/ui/slider";

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

const MAX_BUDGET_KZT = 50_000_000;

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

// Text input instead of type="number": a number input keeps a leading 0 after clearing and cannot show thousands separators.
function getBudgetFromInput(value: string): number {
  return Math.min(Number(value.replace(/\D/g, "")), MAX_BUDGET_KZT);
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Option[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid min-w-0 content-start gap-2 text-sm font-medium">
      {label}
      <Combobox
        items={options}
        value={options.find((option) => option.value === value) ?? null}
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
  defaultFilters,
  onSearch,
}: {
  options: CatalogOptions;
  defaultFilters: SearchFilters | null;
  onSearch: (filters: SearchFilters) => void;
}) {
  const { t, i18n } = useLingui();
  const kzt = new Intl.NumberFormat(i18n.locale);
  const compactKzt = new Intl.NumberFormat(i18n.locale, { notation: "compact" });
  const [filters, setFilters] = useState<SearchFilters>(
    () => defaultFilters ?? getInitialFilters(options),
  );

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
            <label className="grid min-w-0 content-start gap-2 text-sm font-medium">
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
            <div className="col-span-2 grid content-start gap-2 max-md:col-span-1">
              <label className="grid min-w-0 gap-2 text-sm font-medium">
                <Trans>Бюджет, ₸</Trans>
                <input
                  type="text"
                  required
                  inputMode="numeric"
                  autoComplete="off"
                  enterKeyHint="search"
                  value={filters.budget_kzt ? kzt.format(filters.budget_kzt) : ""}
                  onChange={(event) =>
                    setFilters({ ...filters, budget_kzt: getBudgetFromInput(event.target.value) })
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
              <div className="grid min-w-0 content-start gap-2 text-sm font-medium">
                <span id="duration-label" className="flex justify-between gap-2">
                  <Trans>Длительность</Trans>
                  <span className="text-muted-foreground">
                    {filters.duration_hours ? t`до ${filters.duration_hours} ч` : t`Не важно`}
                  </span>
                </span>
                <div className="flex h-10 items-center px-1 max-md:h-11">
                  <Slider
                    aria-labelledby="duration-label"
                    min={0}
                    max={24}
                    step={1}
                    value={[filters.duration_hours ?? 0]}
                    onValueChange={(hours) => {
                      const duration = Array.isArray(hours) ? hours[0] : hours;
                      setFilters({ ...filters, duration_hours: duration || null });
                    }}
                  />
                </div>
              </div>
              <LanguageCombobox
                label={t`Язык работы`}
                placeholder={t`Не важно`}
                options={options.languages}
                value={filters.languages ?? []}
                onChange={(languages) => setFilters({ ...filters, languages })}
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
