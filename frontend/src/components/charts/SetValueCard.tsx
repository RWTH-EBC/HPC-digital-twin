import React, { useEffect, useMemo, useState, useCallback } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { ChartContainer } from "../ui/chart";
import { Wrench, ClipboardList } from "lucide-react";
import type { Template } from "@/types";
import { inputConfig as inputConfigs } from "@/config/infrastructure-config";
import Latex from "@matejmazur/react-katex";
import "katex/dist/katex.min.css";
import { useDashboardStore } from "../../stores/store";

interface ChartData {
  name: string;
  value: number;
  [key: string]: number | string;
}

function removeLatexUnits(latexString: string): string {
  // Remove everything from \left[ ... \right] (including the brackets)
  return latexString.replace(/\\left\[.*?\\right\]/g, "").trim();
}

export function SetValueCard() {
  // Use Zustand store to get selected templates
  const selectedTemplates = useDashboardStore(
    (state) => state.selectedTemplateObjects,
  );

  const [temperatureChartData, setTemperatureChartData] = useState<ChartData[]>(
    [],
  );
  const [pressureChartData, setPressureChartData] = useState<ChartData[]>([]);

  // Process selected template settings into chart data
  useEffect(() => {
    if (!selectedTemplates) {
      setTemperatureChartData([]);
      return;
    }

    // Use a Set to collect unique temperatureSettingMachineNames that are numbers and contain "temperature"
    const temperatureSettingMachineNames = new Set<string>();
    // Iterate through each selected template and its scenario_settings to find relevant values
    selectedTemplates.forEach((template) => {
      Object.entries(template.scenario_settings).forEach(([key, value]) => {
        if (typeof value === "number" && key.includes("temperature")) {
          temperatureSettingMachineNames.add(key);
        }
      });
    });

    // Build chart data: one row per template setting, columns for each template
    // Each row contains the template setting name and its value from each template
    const temperatureChartRows: ChartData[] = Array.from(
      temperatureSettingMachineNames,
    ).map((temperatureSettingMachineName) => {
      // Use inputConfigs to get a more user-friendly display name by removing LaTeX units
      const temperatureSettingDisplayName = removeLatexUnits(
        temperatureSettingMachineName in inputConfigs
          ? (inputConfigs as Record<string, { name: string }>)[
              temperatureSettingMachineName
            ].name
          : temperatureSettingMachineName,
      );
      // Create the row with the user-friendly display name of variables and values from each template
      const row: any = { name: temperatureSettingDisplayName };
      // Add values from each template for this template setting
      selectedTemplates.forEach((template) => {
        row[`value_${template.templateName}`] =
          typeof template.scenario_settings[temperatureSettingMachineName] ===
          "number"
            ? template.scenario_settings[temperatureSettingMachineName]
            : null;
      });
      return row;
    });

    // Use a Set to collect unique pressureSettingMachineNames that are numbers and contain "pressure"
    const pressureSettingMachineNames = new Set<string>();
    selectedTemplates.forEach((template) => {
      Object.entries(template.scenario_settings).forEach(([key, value]) => {
        if (typeof value === "number" && key.includes("pressure")) {
          pressureSettingMachineNames.add(key);
        }
      });
    });

    // Build chart data for pressure
    const pressureChartRows: ChartData[] = Array.from(
      pressureSettingMachineNames,
    ).map((pressureSettingMachineName) => {
      const displayName = removeLatexUnits(
        pressureSettingMachineName in inputConfigs
          ? (inputConfigs as Record<string, { name: string }>)[
              pressureSettingMachineName
            ].name
          : pressureSettingMachineName,
      );
      const row: any = { name: displayName };
      selectedTemplates.forEach((template) => {
        row[`value_${template.templateName}`] =
          typeof template.scenario_settings[pressureSettingMachineName] ===
          "number"
            ? template.scenario_settings[pressureSettingMachineName]
            : null;
      });
      return row;
    });

    setTemperatureChartData(temperatureChartRows);
    setPressureChartData(pressureChartRows);
  }, [selectedTemplates]);

  // Memoize chartConfig from temperatureChartData; only compute if temperatureChartData exists
  const chartConfig = useMemo(() => {
    if (!temperatureChartData.length) return {};
    return Object.fromEntries(
      Object.keys(temperatureChartData[0])
        .filter((key) => key !== "name" && key !== "description")
        .map((key, index) => [
          key,
          { label: key, color: `hsl(var(--chart-${index + 1}))` },
        ]),
    );
  }, [temperatureChartData]);

  // Compute minimum value for xAxis domain
  const minTempValueX = useMemo(() => {
    if (!temperatureChartData.length) return 0;
    // Get all numeric values from all value_* keys in all rows
    const allValues = temperatureChartData.flatMap((item) =>
      Object.keys(item)
        .filter((key) => key.startsWith("value_"))
        .map((key) => item[key])
        .filter((val) => typeof val === "number"),
    );
    return allValues.length ? Math.min(...allValues) : 0;
  }, [temperatureChartData]);

  // Compute maximum value for xAxis domain
  const maxTempValueX = useMemo(() => {
    if (!temperatureChartData.length) return 0;
    // Get all numeric values from all value_* keys in all rows
    const allValues = temperatureChartData.flatMap((item) =>
      Object.keys(item)
        .filter((key) => key.startsWith("value_"))
        .map((key) => item[key])
        .filter((val) => typeof val === "number"),
    );
    return allValues.length ? Math.max(...allValues) : 0;
  }, [temperatureChartData]);

  // Compute min and max values for pressure
  const minPressureValueX = useMemo(() => {
    if (!pressureChartData.length) return 0;
    const allValues = pressureChartData.flatMap((item) =>
      Object.keys(item)
        .filter((key) => key.startsWith("value_"))
        .map((key) => item[key])
        .filter((val) => typeof val === "number"),
    );
    return allValues.length ? Math.min(...allValues) : 0;
  }, [pressureChartData]);

  const maxPressureValueX = useMemo(() => {
    if (!pressureChartData.length) return 0;
    const allValues = pressureChartData.flatMap((item) =>
      Object.keys(item)
        .filter((key) => key.startsWith("value_"))
        .map((key) => item[key])
        .filter((val) => typeof val === "number"),
    );
    return allValues.length ? Math.max(...allValues) : 0;
  }, [pressureChartData]);

  // Calculate total chart height based on number of templates and bar size
  // Size of each bar in the chart
  const barSize = 14;
  // No spacing between templates bars
  const interBarGap = 0;
  // space between different 'set value' rows for temperature chart
  const groupGap = 30;
  // space between different 'set value' rows for pressure chart
  const groupGapPressure = 75;

  // Determine row height based on number of selected templates
  const rowHeight =
    selectedTemplates.length * barSize +
    (selectedTemplates.length - 1) * interBarGap;

  // Calculate total temperature chart height based on number of templates and bar size
  const totalTemperatureChartHeight =
    temperatureChartData.length * rowHeight +
    (temperatureChartData.length - 1) * groupGap;

  // Calculate total pressure chart height based on number of templates and bar size
  const totalPressureChartHeight =
    pressureChartData.length * rowHeight +
    (pressureChartData.length - 1) * groupGapPressure;

  // Legend component to map colors to template names
  const TemplateLegend = ({ templates }: { templates: Template[] }) => (
    <div
      style={{
        display: "flex",
        gap: 16,
        justifyContent: "center",
        marginBottom: 8,
      }}
    >
      {templates.map((template, idx) => (
        <div
          key={template.templateName}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          <span
            style={{
              display: "inline-block",
              width: 14,
              height: 14,
              background: `hsl(var(--chart-${idx + 3}))`,
              borderRadius: 2,
              marginRight: 6,
            }}
          />
          <span
            style={{
              color: `hsl(var(--chart-${idx + 3}))`,
              fontWeight: 500,
            }}
          >
            {template.templateName}
          </span>
        </div>
      ))}
    </div>
  );

  return (
    <Card className="col-span-4 h-full w-full flex-grow">
      <CardHeader className="flex items-center gap-2 space-y-0 pb-4 sm:flex-row">
        <div className="grid flex-1 gap-1 text-center md:text-left">
          <CardTitle className="flex items-center gap-2">
            <Wrench />
            Set Values
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="text-2xl font-bold">
        {/* Show placeholder if no templates are selected */}
        {!selectedTemplates || selectedTemplates.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground rounded-lg border border-dashed border-border bg-muted/50 h-full">
            <ClipboardList className="mb-2 h-10 w-10 text-muted-foreground" />
            <span className="text-lg font-medium">No templates selected</span>
            <span className="text-sm text-muted-foreground mt-1">
              Please select a template to view set values
            </span>
          </div>
        ) : (
          <>
            {/* Render BarChart with temmperature set values */}
            <ChartContainer
              style={{ height: `${totalTemperatureChartHeight}px` }}
              className="w-full m-2"
              config={chartConfig}
            >
              <TemplateLegend templates={selectedTemplates} />
              <BarChart
                data={temperatureChartData}
                layout="vertical"
                margin={{ top: 20, right: 30, left: 30, bottom: 50 }}
                barGap={0}
                barSize={14}
              >
                <CartesianGrid horizontal={false} />{" "}
                {/* Change to horizontal grid lines */}
                <XAxis
                  type="number"
                  domain={[minTempValueX - 5, maxTempValueX + 10]}
                  label={{
                    value: "Temperature in °C",
                    position: "insideBottom",
                    style: { textAnchor: "middle" },
                  }}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tickLine={false}
                  tickMargin={10}
                  axisLine={false}
                  width={150}
                  tick={({ x, y, payload }) => (
                    <foreignObject
                      x={x - 130}
                      y={y - 10}
                      width={150}
                      height={24}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "right",
                          height: "24px",
                        }}
                      >
                        <Latex>{payload.value}</Latex>
                      </div>
                    </foreignObject>
                  )}
                />
                {selectedTemplates.map((template, idx) => (
                  <Bar
                    key={template.templateName}
                    dataKey={`value_${template.templateName}`}
                    fill={`hsl(var(--chart-${idx + 3}))`}
                    radius={4}
                    barSize={14}
                  >
                    <LabelList
                      position="right"
                      content={(props) => {
                        const { x = 0, y = 0, width = 0, value } = props;

                        return (
                          <text
                            x={Number(x) + Number(width) + 6}
                            y={Number(y) + 11}
                            fontSize={12}
                            fill={`hsl(var(--chart-${idx + 3}))`}
                          >
                            {typeof value === "number"
                              ? value.toFixed(2)
                              : value}
                          </text>
                        );
                      }}
                    />
                  </Bar>
                ))}
              </BarChart>
            </ChartContainer>

            {/* Render BarChart with pressure set values */}
            <ChartContainer
              style={{ height: `${totalPressureChartHeight}px` }}
              className="w-full m-2"
              config={chartConfig}
            >
              <TemplateLegend templates={selectedTemplates} />
              <BarChart
                data={pressureChartData}
                layout="vertical"
                margin={{ top: 20, right: 30, left: 30, bottom: 50 }}
                barGap={0}
                barSize={14}
              >
                <CartesianGrid horizontal={false} />
                <XAxis
                  type="number"
                  domain={[0, maxPressureValueX + 2]}
                  label={{
                    value: "Pressure in bar",
                    position: "insideBottom",
                    style: { textAnchor: "middle" },
                  }}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tickLine={false}
                  tickMargin={10}
                  axisLine={false}
                  width={150}
                  tick={({ x, y, payload }) => (
                    <foreignObject
                      x={x - 130}
                      y={y - 10}
                      width={150}
                      height={24}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "right",
                          height: "24px",
                        }}
                      >
                        <Latex>{payload.value}</Latex>
                      </div>
                    </foreignObject>
                  )}
                />
                {selectedTemplates.map((template, idx) => (
                  <Bar
                    key={template.templateName}
                    dataKey={`value_${template.templateName}`}
                    fill={`hsl(var(--chart-${idx + 3}))`}
                    radius={4}
                    barSize={14}
                  >
                    <LabelList
                      position="right"
                      content={(props) => {
                        const { x = 0, y = 0, width = 0, value } = props;
                        return (
                          <text
                            x={Number(x) + Number(width) + 6}
                            y={Number(y) + 11}
                            fontSize={12}
                            fill={`hsl(var(--chart-${idx + 3}))`}
                          >
                            {typeof value === "number"
                              ? value.toFixed(2)
                              : value}
                          </text>
                        );
                      }}
                    />
                  </Bar>
                ))}
              </BarChart>
            </ChartContainer>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default SetValueCard;
