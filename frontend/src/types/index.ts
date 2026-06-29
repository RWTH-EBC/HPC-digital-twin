export interface ProcessedPoint {
  time: Date;
  time_as_number: number;
  value: number | null;
  value_pred: number | null;
  [key: string]: any; // To allow for dynamic template fields
}

export interface Template {
  templateName: string;
  scenario_settings: Record<string, number | boolean>;
  kpis?: {
    pue_scenario: number | null;
    pue_baseline: number | null;
  };
}

