"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, XAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltipContent,
  ChartTooltip,
  ChartLegend,
} from "@/components/ui/chart";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Gauge } from "lucide-react";
import { useDashboardStore } from "@/stores/store";

interface KPIData {
  name: string;
  description: string;
  Measurement: number | null;
  [key: string]: string | number | null | undefined;
}

interface KPIConfigItem {
  label: string;
  color: string;
}

interface KPIConfig {
  [key: string]: KPIConfigItem;
}

// Generate KPI configuration from KPIData
const createKpiConfig = (kpiData: KPIData[]): KPIConfig => {
  // Find all keys that have at least one non-null value
  const keys = kpiData.length
    ? Object.keys(kpiData[0]).filter(
        (key) =>
          key !== "name" &&
          key !== "description" &&
          kpiData.some((item) => item[key] !== null)
      )
    : [];
  return keys.reduce((config, key, index) => {
    let label = key;

    // Create clean labels
    if (key === "Measurement") {
      label = "Current PUE";
    } else if (key === "Baseline") {
      label = "Baseline";
    } else {
      // For template names, use them directly (clean: "test", "test2")
      label = key;
    }

    return {
      ...config,
      [key]: {
        label,
        color: `hsl(var(--chart-${(index % 5) + 1}))`, // Cycle through 5 colors
      },
    };
  }, {} as KPIConfig);
};

export function PerformanceCard() {
  // Get data directly from dashboard store - much simpler!
  // Update only when these specific values change
  const meanPue = useDashboardStore((state) => state.meanPue);
  const selectedTemplateObjects = useDashboardStore(
    (state) => state.selectedTemplateObjects
  );

  const kpiData = useMemo(() => {
    // Create the row with measurement from dashboard store
    const row: KPIData = {
      name: "KPI Values",
      description: "Power Usage Effectiveness",
      Measurement: meanPue,
    };

    // Add just ONE baseline (since they're all the same)
    if (selectedTemplateObjects.length > 0) {
      const firstTemplateWithBaseline = selectedTemplateObjects.find(
        (template) =>
          template.kpis?.pue_baseline !== undefined &&
          template.kpis?.pue_baseline !== null
      );

      if (firstTemplateWithBaseline?.kpis?.pue_baseline !== undefined) {
        row.Baseline = firstTemplateWithBaseline.kpis.pue_baseline;
      }
    }

    // Add scenario values with clean template names (no prefixes)
    selectedTemplateObjects.forEach((template) => {
      if (
        template.kpis?.pue_scenario !== undefined &&
        template.kpis?.pue_scenario !== null
      ) {
        // Use template name directly as key (clean names: "test", "test2")
        row[template.templateName] = template.kpis.pue_scenario;
      }
    });

    return [row];
  }, [meanPue, selectedTemplateObjects]); // Much cleaner dependencies

  const kpiConfig = useMemo(() => createKpiConfig(kpiData), [kpiData]);
  const dataKeys = useMemo(() => Object.keys(kpiConfig), [kpiConfig]);

  // Custom bar chart legend to have color in sync with the line chart
  const CustomChartLegend = (props: any) => {
    const { payload } = props;
    return (
      <ul
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 16,
          listStyle: "none",
          margin: 0,
          padding: 0,
          maxWidth: "100%",
          width: "100%",
          boxSizing: "border-box",
          justifyContent: "center",
        }}
      >
        {payload.map((entry: any, idx: number) => (
          <li
            key={entry.value}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              whiteSpace: "normal",
            }}
          >
            <span
              style={{
                display: "inline-block",
                width: 12,
                height: 12,
                background: entry.color,
                borderRadius: 2,
                marginRight: 6,
              }}
            />
            <span style={{ color: entry.color }}>
              {kpiConfig[entry.dataKey]?.label ?? entry.value}
            </span>
          </li>
        ))}
      </ul>
    );
  };

  return (
    <Card className="2xl:col-span-2 md:col-span-4 h-full flex-grow">
      <CardHeader className="flex items-left justify-between pb-2">
        <CardTitle className="flex items-left gap-2">
          <Gauge />
          Performance
        </CardTitle>
      </CardHeader>
      <CardContent className="text-2xl font-bold">
        <ChartContainer
          config={kpiConfig}
          className="h-[250px] w-full m-2 flex-grow"
        >
          <BarChart data={kpiData} margin={{ top: 20 }}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="name"
              tickLine={false}
              tickMargin={10}
              axisLine={false}
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            {dataKeys.map((key, index) => (
              <Bar
                key={index}
                dataKey={key}
                fill={kpiConfig[key].color}
                radius={4}
              >
                <LabelList
                  dataKey={key}
                  position="top"
                  offset={12}
                  className="fill-foreground"
                  fontSize={12}
                  formatter={(value: number | null) =>
                    value !== null && value !== undefined
                      ? value.toFixed(3)
                      : ""
                  }
                />
              </Bar>
            ))}
            <ChartLegend content={<CustomChartLegend />} />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}

export default PerformanceCard;
