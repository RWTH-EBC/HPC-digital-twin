/**
 * Infrastructure Configuration Loader
 *
 * This module provides environment-specific configuration for the infrastructure plan component.
 * It automatically selects the correct infrastructure settings (image, positions, hints) and
 * input configuration based on the DEPLOYMENT_ENV environment variable.
 */

import { influxConfig } from "./influx-config";
import itcInfraConfig from "./infrastructure/itc.json";
import zihInfraConfig from "./infrastructure/zih.json";
import inputConfigITC from "./input_config_itc.json";
import inputConfigZIH from "./input_config_zih.json";

export type InfrastructureConfig = {
  imagePath: string;
  positions: Record<string, { left: string; top: string }>;
  hints: Record<string, string>;
};

// Map deployment environments to infrastructure configurations
const INFRA_CONFIG_MAP: Record<string, InfrastructureConfig> = {
  itc: itcInfraConfig as InfrastructureConfig,
  zih: zihInfraConfig as InfrastructureConfig,
};

// Map deployment environments to input configurations
const INPUT_CONFIG_MAP: Record<string, any> = {
  itc: inputConfigITC,
  zih: inputConfigZIH,
};

/**
 * Get infrastructure configuration for the current deployment environment
 */
export const infrastructureConfig: InfrastructureConfig =
  INFRA_CONFIG_MAP[influxConfig.DEPLOYMENT_ENV] || INFRA_CONFIG_MAP.itc;

/**
 * Get input configuration for the current deployment environment
 */
export const inputConfig =
  INPUT_CONFIG_MAP[influxConfig.DEPLOYMENT_ENV] || INPUT_CONFIG_MAP.itc;

// Log current configuration (for debugging)
if (typeof window !== "undefined") {
  console.log(
    `Infrastructure Config - Environment: ${influxConfig.DEPLOYMENT_ENV}, Image: ${infrastructureConfig.imagePath}`,
  );
}
