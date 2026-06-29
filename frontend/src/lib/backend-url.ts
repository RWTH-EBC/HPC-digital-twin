/**
 * Backend URL Configuration
 *
 * Provides environment-specific backend service URLs.
 * The host is automatically determined from DEPLOYMENT_ENV.
 */

import { influxConfig } from "@/config/influx-config";

const BACKEND_PORT = 8000;

const HOST_MAP: Record<string, string> = {
  itc: "localhost",
  zih: "localhost",
};

/**
 * Get the backend host for the current deployment environment
 */
const getBackendHost = (): string => {
  return HOST_MAP[influxConfig.DEPLOYMENT_ENV] || HOST_MAP.itc;
};

/**
 * Get the full backend service URL
 * @param endpoint - The API endpoint path (e.g., '/optimize', '/predict')
 * @returns Full URL for the backend service
 */
export const getBackendUrl = (endpoint: string): string => {
  const host = getBackendHost();
  return `http://${host}:${BACKEND_PORT}${endpoint}`;
};

// Log current backend configuration (for debugging)
if (typeof window !== "undefined") {
  console.log(
    `Backend URL - Environment: ${influxConfig.DEPLOYMENT_ENV}, Host: ${getBackendHost()}`,
  );
}
