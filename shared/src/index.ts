export type InterestriageMode = "local" | "server";

export interface RuntimeDefaults {
  bindHost: string;
  requireTls: boolean;
  rateLimitPerMinute: number;
  externalFetchEnabled: boolean;
}

export const DEFAULT_DASHBOARD_ORIGIN = "http://localhost:8080";
