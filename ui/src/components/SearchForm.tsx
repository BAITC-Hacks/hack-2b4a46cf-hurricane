import { Trans, useLingui } from "@lingui/react/macro";
import { RotateCcw, Search, SlidersHorizontal } from "lucide-react";
import { useState, type FormEvent } from "react";

import type { Schemas } from "@/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export type SearchFilters = Schemas["RecommendIn"];
type CatalogOptions = Schemas["CatalogOptionsOut"];
type Option = Schemas["OptionOut"];

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
  return (
    <label className="grid min-w-0 gap-2 text-sm font-medium">
      {label}
      <Select value={value} onValueChange={(selected) => selected && onChange(selected)}>
        <SelectTrigger className="min-h-10 w-full bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 max-md:min-h-11">
          <SelectValue>
            {value === "any" ? anyLabel : options.find((option) => option.value === value)?.label}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {anyLabel && (
            <SelectItem value="any" className="min-h-11 px-3">
              {anyLabel}
            </SelectItem>
          )}
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value} className="min-h-11 px-3">
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
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
  const { t } = useLingui();
  const [filters, setFilters] = useState<SearchFilters>(() => getInitialFilters(options));

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSearch(filters);
  }

  return (
    <Card className="rounded-lg border border-border bg-card py-6 ring-0 [--card-spacing:--spacing(6)] max-md:py-4 max-md:[--card-spacing:--spacing(4)]">
      <CardHeader>
        <CardTitle className="text-xl font-semibold">
          <Trans>Параметры события</Trans>
        </CardTitle>
      </CardHeader>
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
