import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({ component: HomePage });

// STUB: the recommendation form lands here once `POST /recommend` exists.
function HomePage() {
  return null;
}
