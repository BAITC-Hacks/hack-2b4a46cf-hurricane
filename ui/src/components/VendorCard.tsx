import { Trans, useLingui } from "@lingui/react/macro";
import {
  BadgePercent,
  Check,
  Clock,
  Crown,
  Languages,
  MapPin,
  PartyPopper,
  Shuffle,
  Sparkles,
  Tag,
  type LucideIcon,
} from "lucide-react";

import type { Schemas } from "@/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type Vendor = Schemas["VendorOut"] | Schemas["VendorCardOut"];
type Role = Schemas["VendorCardOut"]["role"];
type MatchedOn = Schemas["VendorCardOut"]["matched_on"][number];

const roleIcons: Record<Role, LucideIcon> = {
  best_match: Sparkles,
  best_price: BadgePercent,
  premium: Crown,
  alternative: Shuffle,
};

function Feature({ icon: Icon, children }: { icon: LucideIcon; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-1 text-xs font-medium text-foreground">
      <Icon className="size-3.5 text-muted-foreground" aria-hidden="true" />
      {children}
    </span>
  );
}

export function VendorCard({ vendor }: { vendor: Vendor }) {
  const { t, i18n } = useLingui();
  const isRecommendation = "explanation" in vendor;
  const roleLabels: Record<Role, string> = {
    best_match: t`Лучшее совпадение`,
    best_price: t`Лучшая цена`,
    premium: t`Премиум`,
    alternative: t`Альтернатива`,
  };
  const matchedLabels: Record<MatchedOn, string> = {
    date: t`свободен на дату`,
    format: t`берёт формат`,
    budget: t`в бюджете`,
    duration: t`хватит часов`,
    language: t`нужный язык`,
    description: t`подходит по описанию`,
  };
  const RoleIcon = isRecommendation ? roleIcons[vendor.role] : null;
  const isHighlighted = isRecommendation && vendor.role === "best_match";

  return (
    <Card
      className={
        isHighlighted
          ? "h-full rounded-lg border border-primary py-5 shadow-card ring-0 transition [--card-spacing:--spacing(5)] hover:-translate-y-0.5"
          : "h-full rounded-lg border border-border py-5 ring-0 transition [--card-spacing:--spacing(5)] hover:-translate-y-0.5 hover:shadow-card"
      }
    >
      <CardHeader className="grid gap-3">
        <div className="flex items-start justify-between gap-3">
          {isRecommendation && RoleIcon ? (
            <span
              className={
                vendor.role === "best_match"
                  ? "inline-flex items-center gap-1.5 rounded-full bg-primary px-2.5 py-1 text-xs font-semibold text-primary-foreground"
                  : "inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-xs font-semibold text-foreground"
              }
            >
              <RoleIcon className="size-3.5" aria-hidden="true" />
              {roleLabels[vendor.role]}
            </span>
          ) : (
            <span />
          )}
          <p className="text-right text-lg leading-6 font-semibold tabular-nums whitespace-nowrap">
            <Trans>от {new Intl.NumberFormat(i18n.locale).format(vendor.price_from_kzt)} ₸</Trans>
          </p>
        </div>
        <CardTitle className="text-lg leading-6 font-semibold">{vendor.name}</CardTitle>
        <div className="flex flex-wrap gap-1.5">
          <Feature icon={MapPin}>{vendor.city.label}</Feature>
          <Feature icon={Tag}>
            {vendor.categories.map((category) => category.label).join(", ")}
          </Feature>
          <Feature icon={Languages}>
            {vendor.languages.map((language) => language.label).join(", ")}
          </Feature>
          <Feature icon={Clock}>
            {vendor.max_hours ? t`до ${vendor.max_hours} ч` : t`без привязки к часам`}
          </Feature>
          {"event_formats" in vendor && (
            <Feature icon={PartyPopper}>
              {vendor.event_formats.map((format) => format.label).join(", ")}
            </Feature>
          )}
        </div>
      </CardHeader>
      <CardContent className="grid gap-3">
        {isRecommendation && (
          <ul className="flex flex-wrap gap-1.5" aria-label={t`Что совпало с заказом`}>
            {vendor.matched_on.map((match) => (
              <li
                key={match}
                className="inline-flex items-center gap-1 rounded-full bg-success/10 px-2 py-0.5 text-xs font-medium text-success"
              >
                <Check className="size-3.5" aria-hidden="true" />
                {matchedLabels[match]}
              </li>
            ))}
          </ul>
        )}
        <p
          className={
            isRecommendation
              ? "text-sm leading-6 break-words text-foreground"
              : "text-sm leading-6 break-words whitespace-pre-wrap text-muted-foreground"
          }
        >
          {isRecommendation ? vendor.explanation : vendor.description}
        </p>
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          {vendor.synthetic ? (
            <span className="rounded-full bg-warning/10 px-2 py-0.5 font-medium text-warning">
              <Trans>Синтетический профиль</Trans>
            </span>
          ) : (
            <span className="rounded-full border border-border px-2 py-0.5">
              <Trans>Профиль из каталога</Trans>
            </span>
          )}
          {vendor.price_imputed && (
            <span className="rounded-full border border-border px-2 py-0.5">
              <Trans>цена оценочная</Trans>
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function VendorCardSkeleton() {
  return (
    <Card
      aria-hidden="true"
      className="h-full rounded-lg border border-border py-5 ring-0 [--card-spacing:--spacing(5)]"
    >
      <CardHeader className="grid gap-2">
        <div className="flex gap-2">
          <Skeleton className="h-5 w-28 rounded-full" />
          <Skeleton className="h-5 w-32 rounded-full" />
        </div>
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-4 w-1/2" />
      </CardHeader>
      <CardContent className="grid gap-3">
        <Skeleton className="h-4 w-32" />
        <div className="grid gap-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </CardContent>
    </Card>
  );
}
