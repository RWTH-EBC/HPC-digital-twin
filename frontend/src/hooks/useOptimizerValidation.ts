import { useDashboardStore } from "@/stores/store";
import { InputConfigs, InputValues } from "@/types/config";
import { validateAllInputs } from "@/lib/validation-utils";

interface ValidationResult {
  isValid: boolean;
  errorType?:
    | "validation"
    | "emptyName"
    | "bothExists"
    | "optimizedExists"
    | "optimizedDateTimeExists";
  errorData?: any;
}

export const useOptimizerValidation = () => {
  const { templateCache } = useDashboardStore();

  const validateOptimizerName = (
    templateName: string,
    inputs: InputValues,
    configs: InputConfigs
  ): ValidationResult => {
    console.log("Validating optimizer name:", templateName);
    // 1. Validate all inputs
    const errors = validateAllInputs(inputs, configs);
    const hasValidationErrors = Object.values(errors).some(
      (error) => error !== ""
    );

    if (hasValidationErrors) {
      return {
        isValid: false,
        errorType: "validation",
        errorData: errors,
      };
    }

    // 2. Check for empty name
    if (!templateName.trim()) {
      return { isValid: false, errorType: "emptyName" };
    }

    // Helper
    const allTemplateNames = templateCache.map((t) => t.templateName);

    // regex patterns
    const optimizedDateTimeRegex =
      /^(.+)_optimized_(\d{2}\.\d{2}\.\d{4}_\d{2}:\d{2}:\d{2})$/;

    let baseTemplateName: string;
    let inputIsTemplateName_Opt_DateTime = false;
    let inputIsTemplateName_Opt = false;

    if (optimizedDateTimeRegex.test(templateName)) {
      baseTemplateName = templateName.replace(
        /_optimized_\d{2}\.\d{2}\.\d{4}_\d{2}:\d{2}:\d{2}$/,
        ""
      );
      inputIsTemplateName_Opt_DateTime = true;
    } else if (templateName.endsWith("_optimized")) {
      baseTemplateName = templateName.replace(/_optimized$/, "");
      inputIsTemplateName_Opt = true;
    } else {
      baseTemplateName = templateName;
    }

    const baseOptimized = `${baseTemplateName}_optimized`;

    const dateTimePattern = new RegExp(
      `^${baseTemplateName}_optimized_\\d{2}\\.\\d{2}\\.\\d{4}_\\d{2}:\\d{2}:\\d{2}$`
    );

    const dateTimeVersions = allTemplateNames.filter((n) =>
      dateTimePattern.test(n)
    );
    const hasBaseOptimized = allTemplateNames.includes(baseOptimized);

    // CASES

    // ---User input: TemplateName_optimized_dateTime
    if (inputIsTemplateName_Opt_DateTime) {
      if (allTemplateNames.includes(templateName) && hasBaseOptimized) {
        return {
          isValid: false,
          errorType: "bothExists",
          errorData: baseOptimized,
        };
      }
      if (allTemplateNames.includes(templateName)) {
        return {
          isValid: false,
          errorType: "optimizedDateTimeExists",
          errorData: templateName,
        };
      }
      return { isValid: true }; // allow new date
      // TO DO: Don't allow date as user input by returning errorType and errorData
    }

    // --- User input: TemplateName_optimized
    if (inputIsTemplateName_Opt) {
      // TemplateName_optimized and TemplateName_optimized_dateTime templates exist
      if (hasBaseOptimized && dateTimeVersions.length > 0) {
        return {
          isValid: false,
          errorType: "bothExists",
          errorData: baseOptimized,
        };
      }
      // Only TemplateName_optimized templates exist
      if (hasBaseOptimized) {
        return {
          isValid: false,
          errorType: "optimizedExists",
          errorData: baseOptimized,
        };
      }
      // Only TemplateName_optimized_dateTime templates exist
      if (dateTimeVersions.length > 0) {
        return {
          isValid: false,
          errorType: "optimizedDateTimeExists",
          errorData: baseOptimized,
        };
      }
      return { isValid: true };
    }

    // --- User input: TemplateName
    if (hasBaseOptimized && dateTimeVersions.length > 0) {
      return {
        isValid: false,
        errorType: "bothExists",
        errorData: baseOptimized,
      };
    }
    if (hasBaseOptimized) {
      return {
        isValid: false,
        errorType: "optimizedExists",
        errorData: baseOptimized,
      };
    }
    if (dateTimeVersions.length > 0) {
      return {
        isValid: false,
        errorType: "optimizedDateTimeExists",
        errorData: baseOptimized,
      };
    }

    return { isValid: true };
  };

  return { validateOptimizerName };
};
