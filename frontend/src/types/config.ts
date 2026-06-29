/**
 * Shared type definitions for input configurations
 * Used across optimizer and template settings pages
 */

export interface NumericInputConfig {
  name: string;
  default_value: number;
  unit?: string;
  min_value?: number;
  max_value?: number;
}

export interface BooleanInputConfig {
  name: string;
  default_value: boolean;
  unit: string;
}

export type InputConfig = NumericInputConfig | BooleanInputConfig;

export interface InputConfigs {
  [key: string]: InputConfig;
}

export type ConfigKey = string;

export type InputValues = { [key: string]: number | boolean };
export type InputErrors = { [key: string]: string };
