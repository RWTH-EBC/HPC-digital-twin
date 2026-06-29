import { create } from "zustand";
import { Template } from "@/types";
import { optimizerDefaults } from "@/config/optimizer-defaults";

interface AppliedSettings {
  templates: string[];
  simulationFrequency: number;
  simulationTimeInDays: number;
  stepsize: number;
}

// Global SSE connection reference
let sseConnection: EventSource | null = null;

interface DashboardState {
  simulationUnit: string;
  simulationFrequency: number;
  simulationTimeInDays: number;
  stepsize: number;
  isConnected: boolean;
  startDate: string;
  selectedMeasurement: string;
  selectedTemplates: string[];
  selectedTemplateObjects: Template[];
  allMeasurements: string[];
  appliedSettings: AppliedSettings | null;
  templateCache: Template[];
  templateNames: string[];
  meanPue: number | null;
  sseConnected: boolean;

  setIsConnected: (connected: boolean) => void;
  setSimulationUnit: (unit: string) => void;
  setSimulationFrequency: (frequency: number) => void;
  setSimulationTimeInDays: (days: number) => void;
  setStepsize: (stepsize: number) => void;
  setStartDate: (date: string) => void;
  setSelectedMeasurement: (measurement: string) => void;
  setSelectedTemplates: (templates: string[]) => void;
  setAllMeasurements: (measurements: string[]) => void;
  setAppliedSettings: (settings: AppliedSettings | null) => void;
  setTemplateCache: (templates: Template[]) => void;
  setTemplateNames: (names: string[]) => void;
  setMeanPue: (meanPue: number | null) => void;
  fetchTemplateCache: () => Promise<void>;
  connectToSSE: () => void;
  disconnectSSE: () => void;
}

export const useDashboardStore = create<DashboardState>(
  (set, get): DashboardState => ({
    simulationUnit: "minutes",
    simulationFrequency: 15,
    simulationTimeInDays: optimizerDefaults.simDays,
    stepsize: optimizerDefaults.stepsize * 60, // Convert minutes to seconds
    isConnected: false,
    startDate: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000)
      .toISOString()
      .split("T")[0],
    selectedMeasurement: "",
    selectedTemplates: [],
    selectedTemplateObjects: [],
    allMeasurements: [],
    appliedSettings: null,
    templateCache: [],
    templateNames: [],
    meanPue: null,
    sseConnected: false,

    setIsConnected: (connected: boolean) => set({ isConnected: connected }),
    setSimulationUnit: (unit) => set({ simulationUnit: unit }),
    setSimulationFrequency: (frequency) =>
      set({ simulationFrequency: frequency }),
    setSimulationTimeInDays: (days) => set({ simulationTimeInDays: days }),
    setStepsize: (stepsize) => set({ stepsize: stepsize }),
    setStartDate: (date) => set({ startDate: date }),
    setSelectedMeasurement: (measurement) =>
      set({ selectedMeasurement: measurement }),

    setSelectedTemplates: (templates) => {
      const { templateCache } = get();
      const selectedTemplateObjects = templates
        .map((templateName) =>
          templateCache.find(
            (template) => template.templateName === templateName,
          ),
        )
        .filter((template): template is Template => template !== undefined);

      set({
        selectedTemplates: templates,
        selectedTemplateObjects: selectedTemplateObjects,
      });
    },
    setAllMeasurements: (measurements) =>
      set({ allMeasurements: measurements }),
    setAppliedSettings: (settings) => set({ appliedSettings: settings }),
    setTemplateCache: (templates) => {
      const { selectedTemplates } = get();
      const templateNames = templates.map((template) => template.templateName);

      // Update selectedTemplateObjects based on current selectedTemplates
      const selectedTemplateObjects = selectedTemplates
        .map((templateName) =>
          templates.find((template) => template.templateName === templateName),
        )
        .filter((template): template is Template => template !== undefined);

      set({
        templateCache: templates,
        templateNames,
        selectedTemplateObjects: selectedTemplateObjects,
      });
    },
    setTemplateNames: (names) => set({ templateNames: names }),
    setMeanPue: (meanPue) => set({ meanPue }),

    fetchTemplateCache: async () => {
      console.log("Fetching template cache from API");
      try {
        const res = await fetch("/api/cache-handling");
        if (res.ok) {
          const data = await res.json();
          if (data.success && data.scenarioCache) {
            const { selectedTemplates } = get();
            const templateNames = data.scenarioCache.map(
              (template: Template) => template.templateName,
            );

            // Update selectedTemplateObjects based on current selectedTemplates
            const selectedTemplateObjects = selectedTemplates
              .map((templateName) =>
                data.scenarioCache.find(
                  (template: Template) =>
                    template.templateName === templateName,
                ),
              )
              .filter(
                (template): template is Template => template !== undefined,
              );

            set({
              templateCache: data.scenarioCache,
              templateNames,
              selectedTemplateObjects: selectedTemplateObjects,
            });
          }
        }
      } catch (error) {
        console.error("Error fetching template cache:", error);
      }
    },

    connectToSSE: () => {
      // Prevent multiple connections
      if (sseConnection) {
        console.log("SSE already connected");
        return;
      }

      console.log("Connecting to SSE...");
      sseConnection = new EventSource("/api/cache-handling?sse=true");

      sseConnection.onopen = () => {
        console.log("SSE connection established");
        set({ sseConnected: true });
      };

      sseConnection.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("SSE message received:", data.type);

          if (data.type === "initial" || data.type === "cache_update") {
            const { selectedTemplates } = get();
            const scenarioCache = data.scenarioCache || [];
            const templateNames = scenarioCache.map(
              (template: Template) => template.templateName,
            );

            // Update selectedTemplateObjects based on current selectedTemplates
            const selectedTemplateObjects = selectedTemplates
              .map((templateName) =>
                scenarioCache.find(
                  (template: Template) =>
                    template.templateName === templateName,
                ),
              )
              .filter(
                (template): template is Template => template !== undefined,
              );

            console.log("Updating store with new cache data");
            set({
              templateCache: scenarioCache,
              templateNames,
              selectedTemplateObjects: selectedTemplateObjects,
            });
          }
        } catch (error) {
          console.error("Error parsing SSE message:", error);
        }
      };

      sseConnection.onerror = (error) => {
        console.error("SSE error:", error);
        set({ sseConnected: false });

        // Close and cleanup on error
        if (sseConnection) {
          sseConnection.close();
          sseConnection = null;
        }

        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          console.log("Attempting to reconnect SSE...");
          get().connectToSSE();
        }, 5000);
      };
    },

    disconnectSSE: () => {
      if (sseConnection) {
        console.log("Disconnecting SSE...");
        sseConnection.close();
        sseConnection = null;
        set({ sseConnected: false });
      }
    },
  }),
);
