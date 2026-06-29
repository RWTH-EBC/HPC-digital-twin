/**
 * Custom hook for managing input state
 * Handles input values, errors, and selected input tracking
 */

import { useState } from "react";
import {
  InputConfigs,
  InputValues,
  InputErrors,
  ConfigKey,
} from "@/types/config";
import { isBooleanConfig, validateNumericInput } from "@/lib/validation-utils";

export const useInputState = (inputConfigs: InputConfigs) => {
  // Initialize inputs with default values from config
  const [inputs, setInputs] = useState<InputValues>(() => {
    const initialState: InputValues = {};
    Object.entries(inputConfigs).forEach(([key, config]) => {
      initialState[key] = config.default_value;
    });
    return initialState;
  });

  const [inputErrors, setInputErrors] = useState<InputErrors>({});
  const [selectedInput, setSelectedInput] = useState<string | null>(null);

  /**
   * Handle input value changes with validation
   */
  const handleInputChange = (
    field: ConfigKey,
    value: string | number | boolean
  ) => {
    const config = inputConfigs[field];

    if (isBooleanConfig(config)) {
      setInputs((prev) => ({
        ...prev,
        [field]: value as boolean,
      }));
      return;
    }

    // Numeric input
    const numberValue = typeof value === "number" ? value : Number(value);
    setInputs((prev) => ({
      ...prev,
      [field]: numberValue,
    }));

    const error = validateNumericInput(config, numberValue);
    setInputErrors((prev) => ({
      ...prev,
      [field]: error,
    }));
  };

  return {
    inputs,
    setInputs,
    inputErrors,
    setInputErrors,
    selectedInput,
    setSelectedInput,
    handleInputChange,
  };
};
