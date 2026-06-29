/**
 * Optimizer Default Values Configuration
 *
 * Provides environment-specific default values for optimizer settings.
 * These defaults are used in the optimizer dashboard when initializing state.
 */

import { influxConfig } from "./influx-config";

export type OptimizerDefaults = {
  stepsize: number; // in minutes
  simDays: number; // number of simulation days
  optimizationDuration: number; // in minutes (constant across environments)
  nCores: number; // number of cores (constant across environments)
};

const OPTIMIZER_DEFAULTS_MAP: Record<string, OptimizerDefaults> = {
  local: {
    stepsize: 15, // 900 seconds = 15 minutes
    simDays: 4,
    optimizationDuration: 1,
    nCores: 1,
  },
  itc: {
    stepsize: 15, // 900 seconds = 15 minutes
    simDays: 4,
    optimizationDuration: 1,
    nCores: 1,
  },
  ebc: {
    stepsize: 15, // 900 seconds = 15 minutes (uses ITC defaults)
    simDays: 4,
    optimizationDuration: 1,
    nCores: 1,
  },
  zih: {
    stepsize: 2, // 120 seconds = 2 minutes
    simDays: 4,
    optimizationDuration: 1,
    nCores: 1,
  },
};

/**
 * Get optimizer default values for the current deployment environment
 */
export const optimizerDefaults: OptimizerDefaults =
  OPTIMIZER_DEFAULTS_MAP[influxConfig.DEPLOYMENT_ENV] ||
  OPTIMIZER_DEFAULTS_MAP.itc;

// Log current optimizer defaults (for debugging)
if (typeof window !== "undefined") {
  console.log(
    `Optimizer Defaults - Environment: ${influxConfig.DEPLOYMENT_ENV}, Stepsize: ${optimizerDefaults.stepsize} min, Sim Days: ${optimizerDefaults.simDays}`,
  );
}
