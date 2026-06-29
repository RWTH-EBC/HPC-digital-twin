import React, { useMemo } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Wrench, ClipboardList } from "lucide-react";
import { useDashboardStore } from "../../stores/store";
import { inputConfig as inputConfigs } from "@/config/infrastructure-config";

// Function to extract short name from LaTeX formatted string mentioned in input_config.json
function getShortName(key: string): string {
  const latexName = inputConfigs[key as keyof typeof inputConfigs]?.name ?? key;
  const match = latexName.match(/\\text\{(CT\d+)/);
  return match ? match[1] : latexName;
}

// Component to display boolean values in a table format when selected templates change
export function BooleanValuesCard() {
  const selectedTemplates = useDashboardStore(
    (state) => state.selectedTemplateObjects,
  );

  // Get all unique boolean keys when selected templates change
  const allBooleanKeys = useMemo(
    () =>
      Array.from(
        new Set(
          selectedTemplates.flatMap((template) =>
            Object.entries(template.scenario_settings)
              .filter(([_, value]) => typeof value === "boolean")
              .map(([key]) => key),
          ),
        ),
      ),
    [selectedTemplates],
  );

  // Render the card with a table of boolean values or a message to select temaplates if no templates are selected
  return (
    <Card className="2xl:col-span-2 md:col-span-4 h-full flex-grow">
      <CardHeader className="flex items-center gap-2 space-y-0 pb-4 sm:flex-row">
        <CardTitle className="flex items-center gap-2">
          <Wrench />
          Template Boolean Set Values
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Show message if no templates are selected */}
        {selectedTemplates.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground rounded-lg border border-dashed border-border bg-muted/50">
            <ClipboardList className="mb-2 h-10 w-10 text-muted-foreground" />
            <span className="text-lg font-medium">No templates selected</span>
            <span className="text-sm text-muted-foreground mt-1">
              Please select a template to view boolean values
            </span>
          </div>
        ) : (
          // Render table of boolean values
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm border border-border">
              <thead className="bg-muted">
                <tr>
                  <th
                    scope="col"
                    className="px-2 py-1 border border-border text-center font-semibold text-muted-foreground"
                  >
                    Template Name
                  </th>
                  {allBooleanKeys.map((key) => (
                    <th
                      key={key}
                      scope="col"
                      className="px-2 py-1 border border-border text-center font-semibold text-muted-foreground"
                    >
                      {getShortName(key)}
                    </th>
                  ))}
                </tr>
              </thead>
              {/* Table body with boolean values for each selected template */}
              <tbody>
                {selectedTemplates.map((template, idx) => (
                  <tr key={template.templateName}>
                    <td
                      scope="row"
                      className="px-2 py-1 border border-border font-semibold text-center"
                      style={{
                        color: `hsl(var(--chart-${idx + 3}))`,
                      }}
                    >
                      {template.templateName}
                    </td>
                    {allBooleanKeys.map((key) => {
                      const value = template.scenario_settings[key];
                      return (
                        <td
                          key={key}
                          className="px-2 py-1 border border-border text-center"
                        >
                          {typeof value === "boolean" ? (
                            <span
                              className={`inline-block px-2 py-0.5 rounded text-white text-xs ${
                                value ? "bg-green-500" : "bg-gray-400"
                              }`}
                            >
                              {value ? "On" : "Off"}
                            </span>
                          ) : (
                            "-"
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
