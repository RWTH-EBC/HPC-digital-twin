/**
 * Validation utilities for input configurations
 * Provides type guards and validation functions
 */

import {
  InputConfig,
  NumericInputConfig,
  BooleanInputConfig,
  ConfigKey,
} from "@/types/config";

/**
 * Type guard to check if config is numeric
 */
const isNumericConfig = (config: InputConfig): config is NumericInputConfig =>
  config.unit !== "bool";

/**
 * Type guard to check if config is boolean
 */
export const isBooleanConfig = (
  config: InputConfig
): config is BooleanInputConfig => "unit" in config && config.unit === "bool";

/**
 * Validate a single numeric input value
 * @param config - The input configuration
 * @param value - The value to validate
 * @returns Error message or empty string if valid
 */
export const validateNumericInput = (
  config: InputConfig,
  value: number
): string => {
  if (!isNumericConfig(config)) return ""; // Skip validation for boolean configs

  if (isNaN(value)) {
    return "Please enter a valid number";
  }

  if (config.min_value !== undefined || config.max_value !== undefined) {
    if (config.min_value !== undefined && config.max_value !== undefined) {
      // Both boundaries exist
      if (value < config.min_value || value > config.max_value) {
        return `Value must be between ${config.min_value} and ${config.max_value}`;
      }
    } else {
      // Only one boundary exists
      if (config.min_value !== undefined && value < config.min_value) {
        return `Value must be at least ${config.min_value}`;
      }
      if (config.max_value !== undefined && value > config.max_value) {
        return `Value must be at most ${config.max_value}`;
      }
    }
  }

  return "";
};

/**
 * Validate all inputs in a configuration
 * @param inputs - Current input values
 * @param configs - Input configurations
 * @returns Object with validation errors
 */
export const validateAllInputs = (
  inputs: { [key: string]: number | boolean },
  configs: { [key: string]: InputConfig }
): { [key: string]: string } => {
  const errors: { [key: string]: string } = {};
  let hasErrors = false;

  Object.entries(configs).forEach(([field, config]) => {
    if (!isBooleanConfig(config)) {
      const error = validateNumericInput(config, Number(inputs[field]));
      errors[field] = error;
      if (error) hasErrors = true;
    }
  });

  return errors;
};
