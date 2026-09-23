import { Trans } from "@lingui/react/macro";
import { Check, Link2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

export function CopyLinkButton() {
  const [isCopied, setIsCopied] = useState(false);

  async function handleClick() {
    await navigator.clipboard.writeText(window.location.href);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  }

  return (
    <Button
      type="button"
      variant="ghost"
      onClick={handleClick}
      aria-live="polite"
      className="h-10 w-fit gap-2 px-3 transition active:scale-[0.98] max-md:h-11"
    >
      {isCopied ? (
        <Check className="size-4" aria-hidden="true" />
      ) : (
        <Link2 className="size-4" aria-hidden="true" />
      )}
      {isCopied ? <Trans>Скопировано</Trans> : <Trans>Скопировать ссылку</Trans>}
    </Button>
  );
}
