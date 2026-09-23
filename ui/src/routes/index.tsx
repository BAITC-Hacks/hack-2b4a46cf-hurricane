import { Trans } from "@lingui/react/macro";
import { useQuery } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { SearchX } from "lucide-react";
import { useState } from "react";

import { fetchCatalogOptions, fetchVendors } from "@/api";
import { SearchForm, type SearchFilters } from "@/components/SearchForm";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { VendorCard, VendorCardSkeleton } from "@/components/VendorCard";
import {
  getSearchFilters,
  getSearchParams,
  validateSearchParams,
  type SearchParams,
} from "@/search-params";

export const Route = createFileRoute("/")({
  validateSearch: (search: Record<string, unknown>): Partial<SearchParams> =>
    search.city ? validateSearchParams(search) : {},
  component: HomePage,
});

function SearchFormSkeleton() {
  return (
    <Card
      aria-busy="true"
      className="rounded-lg border border-border bg-card py-6 ring-0 [--card-spacing:--spacing(6)] max-md:py-4 max-md:[--card-spacing:--spacing(4)]"
    >
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-3 gap-3 max-md:grid-cols-1">
          {Array.from({ length: 5 }, (_, index) => (
            <div key={index} className="grid gap-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-10 w-full max-md:h-11" />
            </div>
          ))}
        </div>
        <Skeleton className="h-10 w-full max-md:h-11" />
        <div className="flex gap-3 max-md:flex-col">
          <Skeleton className="h-10 w-36 max-md:h-11 max-md:w-full" />
          <Skeleton className="h-10 w-48 max-md:h-11 max-md:w-full" />
        </div>
      </CardContent>
    </Card>
  );
}

function HomePage() {
  const navigate = useNavigate();
  const defaultFilters = getSearchFilters(Route.useSearch());
  const [showAllVendors, setShowAllVendors] = useState(false);
  const options = useQuery({ queryKey: ["catalog", "options"], queryFn: fetchCatalogOptions });
  const vendors = useQuery({ queryKey: ["vendors"], queryFn: fetchVendors });

  async function handleSearch(filters: SearchFilters) {
    const search = getSearchParams(filters);
    // Filters go into the home URL too, so browser Back from results restores them.
    await navigate({ to: "/", search, replace: true });
    navigate({ to: "/results", search });
  }

  return (
    <div className="grid gap-8 pb-12">
      {options.isPending ? (
        <SearchFormSkeleton />
      ) : options.isError ? (
        <div className="grid gap-3 rounded-lg border border-border bg-card p-6">
          <p className="text-sm text-destructive">
            <Trans>Не удалось загрузить фильтры. Попробуйте ещё раз.</Trans>
          </p>
          <Button
            variant="outline"
            onClick={() => options.refetch()}
            className="w-fit max-md:w-full"
          >
            <Trans>Повторить</Trans>
          </Button>
        </div>
      ) : (
        <SearchForm
          options={options.data}
          defaultFilters={defaultFilters}
          onSearch={handleSearch}
        />
      )}
      <section className="grid gap-4" aria-live="polite">
        <h2 className="text-xl font-semibold">
          <Trans>Подрядчики</Trans>
        </h2>
        {vendors.isPending ? (
          <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1" aria-busy="true">
            {Array.from({ length: 6 }, (_, index) => (
              <VendorCardSkeleton key={index} />
            ))}
          </div>
        ) : vendors.isError ? (
          <div className="grid gap-3 rounded-lg border border-border bg-card p-6">
            <p className="text-sm text-destructive">
              <Trans>Не удалось загрузить подрядчиков. Попробуйте ещё раз.</Trans>
            </p>
            <Button
              variant="outline"
              onClick={() => vendors.refetch()}
              className="w-fit max-md:w-full"
            >
              <Trans>Повторить</Trans>
            </Button>
          </div>
        ) : vendors.data.length === 0 ? (
          <div className="grid justify-items-center gap-2 rounded-lg border border-border bg-card p-8 text-center">
            <SearchX className="size-10 text-muted-foreground" aria-hidden="true" />
            <p className="font-semibold">
              <Trans>Подрядчиков пока нет</Trans>
            </p>
            <p className="text-sm text-muted-foreground">
              <Trans>Попробуйте вернуться позже.</Trans>
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
              {(showAllVendors ? vendors.data : vendors.data.slice(0, 6)).map((vendor) => (
                <VendorCard key={vendor.id} vendor={vendor} />
              ))}
            </div>
            {!showAllVendors && vendors.data.length > 6 && (
              <Button
                variant="outline"
                onClick={() => setShowAllVendors(true)}
                className="w-fit max-md:w-full"
              >
                <Trans>Показать всех подрядчиков ({vendors.data.length})</Trans>
              </Button>
            )}
          </>
        )}
      </section>
    </div>
  );
}
