/**
 * InfluxDB Configuration Module
 *
 * This module provides environment-specific configuration for InfluxDB connections.
 * The deployment environment is determined by the DEPLOYMENT_ENV environment variable.
 */

type DeploymentEnvironment = "itc" | "zih";

const DEPLOYMENT_ENV = (process.env.NEXT_PUBLIC_DEPLOYMENT_ENV ||
  "itc") as DeploymentEnvironment;

const HOST_MAP: Record<DeploymentEnvironment, string> = {
  itc: "localhost",
  zih: "localhost",
};

// Each deployment env writes/reads its own InfluxDB database so the dashboard
// only shows variables of the current env. Must match the database name used
// by the backend coordinator and the iot-platform influx_agent.
const DB_NAME_MAP: Record<DeploymentEnvironment, string> = {
  itc: "influx_db_itc",
  zih: "influx_db_zih",
};

export const influxConfig = {
  HOST: HOST_MAP[DEPLOYMENT_ENV] || HOST_MAP.itc,
  INFLUX_PORT: 8086,
  INFLUX_DB_NAME: DB_NAME_MAP[DEPLOYMENT_ENV] || DB_NAME_MAP.itc,
  DEPLOYMENT_ENV,
};

// Log the current configuration (for debugging)
if (typeof window !== "undefined") {
  console.log(
    `InfluxDB Config - Environment: ${DEPLOYMENT_ENV}, Host: ${influxConfig.HOST}`,
  );
}
