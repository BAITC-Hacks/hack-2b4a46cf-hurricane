import { useEffect, useRef } from "react";

import type { TelegramAuthPayload } from "@/api";

declare global {
  interface Window {
    onTelegramAuth?: (payload: TelegramAuthPayload) => void;
  }
}

const BOT_USERNAME = import.meta.env.VITE_TG_BOT_USERNAME ?? "";

type Props = { onAuth: (payload: TelegramAuthPayload) => void };

/** Renders the official Telegram Login Widget. Requires /setdomain in @BotFather. */
export function TelegramLoginButton({ onAuth }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !BOT_USERNAME) return;
    window.onTelegramAuth = onAuth;

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.dataset.telegramLogin = BOT_USERNAME;
    script.dataset.size = "medium";
    script.dataset.radius = "6";
    script.dataset.requestAccess = "write";
    script.dataset.onauth = "onTelegramAuth(user)";
    container.replaceChildren(script);

    return () => {
      container.replaceChildren();
      delete window.onTelegramAuth;
    };
  }, [onAuth]);

  return <div ref={containerRef} className="flex h-10 items-center" />;
}
