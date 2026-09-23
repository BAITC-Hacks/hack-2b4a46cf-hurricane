// Whole Railway project in one file: a resource missing here is deleted on `railway config apply`.
import { defineRailway, postgres, preserve, project, service, volume } from "railway/iac";

export default defineRailway(() => {
  const Postgres = postgres("Postgres", { region: "europe-west4" });
  Postgres.networking = { privateNetworkEndpoint: "postgres" };
  const postgresVolume = volume("postgres-volume", {
    alerts: { usage: { "100": {}, "80": {}, "95": {} } },
    allowOnlineResize: true,
    region: "europe-west4",
    sizeMB: 50000,
  });

  // Code arrives via `railway up` from app/ and ui/, so paths are relative to those folders.
  const app = service("app", {
    replicas: { "europe-west4": 1 },
    build: { builder: "DOCKERFILE", dockerfilePath: "Dockerfile" },
    deploy: {
      preDeployCommand: ["alembic upgrade head", "python -m src.seed"],
      healthcheckPath: "/health",
      restartPolicyType: "ON_FAILURE",
    },
    // Values stay in Railway: DATABASE_URL is the Postgres reference with the asyncpg scheme.
    env: {
      CORS_ORIGINS: preserve(),
      DATABASE_URL: preserve(),
      OPENAI_API_KEY: preserve(),
      OPENAI_MODEL: preserve(),
    },
  });

  const ui = service("ui", {
    replicas: { "europe-west4": 1 },
    build: { builder: "DOCKERFILE", dockerfilePath: "Dockerfile" },
    deploy: { healthcheckPath: "/", restartPolicyType: "ON_FAILURE" },
    env: { VITE_API_URL: preserve() },
  });

  return project("hurricane", {
    resources: [Postgres, postgresVolume, app, ui],
  });
});
