/**
 * Custom hook for template validation
 * Combines all validation checks for template creation/submission
 */

import { useDashboardStore } from "@/stores/store";
import { InputConfigs, InputValues } from "@/types/config";
import { validateAllInputs } from "@/lib/validation-utils";
import { checkTemplateNameExists, checkDuplicateInputs } from "@/lib/template-utils";

interface ValidationResult {
  isValid: boolean;
  errorType?: "validation" | "emptyName" | "duplicateName" | "duplicateInputs";
  errorData?: any;
}

export const useTemplateValidation = () => {
  const { templateCache, templateNames } = useDashboardStore();

  /**
   * Validate template before submission
   * Checks input validation, name uniqueness, and input duplication
   */
  const validateTemplate = (
    templateName: string,
    inputs: InputValues,
    configs: InputConfigs
  ): ValidationResult => {
    // Validate all inputs
    const errors = validateAllInputs(inputs, configs);
    const hasValidationErrors = Object.values(errors).some((error) => error !== "");

    if (hasValidationErrors) {
      return {
        isValid: false,
        errorType: "validation",
        errorData: errors,
      };
    }
    // Check template name
    const nameExists = checkTemplateNameExists(templateName, templateNames);
    if (nameExists === "EmptyString") {
      return {
        isValid: false,
        errorType: "emptyName",
      };
    }

    if (nameExists === true) {
      return {
        isValid: false,
        errorType: "duplicateName",
        errorData: templateName,
      };
    }

    // Check for duplicate inputs
    const duplicateTemplate = checkDuplicateInputs(inputs, templateCache);
    if (duplicateTemplate) {
      return {
        isValid: false,
        errorType: "duplicateInputs",
        errorData: duplicateTemplate,
      };
    }

    return { isValid: true };
  };

  return {
    validateTemplate,
  };
};
