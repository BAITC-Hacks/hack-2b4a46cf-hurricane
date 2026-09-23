import { Trans, useLingui } from "@lingui/react/macro";
import { useMutation, useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";

import { askLlm, fetchHealth } from "@/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

export const Route = createFileRoute("/")({ component: HomePage });

function HomePage() {
  const { t } = useLingui();
  const [prompt, setPrompt] = useState("");
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth });
  const ask = useMutation({ mutationFn: askLlm });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    ask.mutate(prompt);
  }

  return (
    <Card className="shadow-card">
      <CardHeader>
        <CardDescription>
          <Trans>Статус API:</Trans>{" "}
          {health.isPending ? (
            "…"
          ) : (
            <span className={health.isSuccess ? "text-success" : "text-destructive"}>
              {health.isSuccess ? t`онлайн` : t`офлайн`}
            </span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <form className="grid gap-3" onSubmit={handleSubmit}>
          <Textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder={t`Спросите что-нибудь`}
            rows={4}
            maxLength={4000}
            required
          />
          <Button
            type="submit"
            disabled={ask.isPending}
            className="justify-self-start max-md:w-full"
          >
            {ask.isPending ? t`Думаю…` : t`Отправить`}
          </Button>
        </form>
        {ask.isError && <p className="text-sm text-destructive">{ask.error.message}</p>}
        {ask.isSuccess && <p className="whitespace-pre-wrap leading-relaxed">{ask.data.answer}</p>}
      </CardContent>
    </Card>
  );
}
