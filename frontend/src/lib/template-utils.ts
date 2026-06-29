/**
 * Template validation utilities
 * Functions for checking template name uniqueness and input duplication
 */

import { Template } from "@/types";

/**
 * Check if a template name exists in the cache
 * @param templateName - Name to check
 * @param templateNames - Array of existing template names
 * @returns "EmptyString" if empty, true if exists, false otherwise
 */
export const checkTemplateNameExists = (
  templateName: string,
  templateNames: string[]
): boolean | "EmptyString" => {
  if (!templateName.trim()) {
    return "EmptyString";
  }
  return templateNames.includes(templateName);
};

/**
 * Check if identical input settings already exist under a different template name
 * @param inputs - Current input values
 * @param templateCache - Array of existing templates
 * @returns Template name if duplicate found, false otherwise
 */
export const checkDuplicateInputs = (
  inputs: Record<string, number | boolean>,
  templateCache: Template[]
): string | false => {
  const templateSettingsExists = templateCache.find((template) =>
    Object.entries(inputs).every(
      ([key, value]) => template.scenario_settings[key] === value
    )
  );

  if (templateSettingsExists) {
    return templateSettingsExists.templateName;
  }
  return false;
};

// Generate optimized template name
export const getOptimizedTemplateName = (name: string) => {
  const optimizedDatePattern =
    /_optimized(_\d{2}\.\d{2}\.\d{4}(_\d{2}:\d{2}:\d{2})?)?$/;
  if (optimizedDatePattern.test(name)) {
    return name;
  }
  return `${name}_optimized`;
};
