"use client";

import { useState, useEffect } from "react";
import PerformanceCard from "@/components/charts/PerformanceCard";
import { LineChartCard } from "@/components/charts/LineChartCardOptimized";
import { SetValueCard } from "@/components/charts/SetValueCard";
import { BooleanValuesCard } from "@/components/charts/BooleanValuesCard";
import PageTitle from "@/components/PageTitle";
import { Input } from "@/components/ui/input";
import { Check, ChevronsUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

import { useDashboardStore } from "@/stores/store";
import { getBackendUrl } from "@/lib/backend-url";

export default function Scenario() {
  const {
    simulationUnit,
    simulationFrequency,
    simulationTimeInDays,
    stepsize,
    selectedTemplates,
    selectedTemplateObjects,
    appliedSettings,
    templateNames,
    templateCache,
    setSimulationFrequency,
    setSimulationUnit,
    setSimulationTimeInDays,
    setStepsize,
    setSelectedTemplates,
    setAppliedSettings,
    fetchTemplateCache,
  } = useDashboardStore();

  const [open, setOpen] = useState(false);
  const isSelected = (templateName: string) =>
    selectedTemplates.includes(templateName);

  const clearAll = () => setSelectedTemplates([]);
  const selectAll = () => setSelectedTemplates(templateNames);

  // Add new state variables for the Apply button
  const [applyEnabled, setApplyEnabled] = useState<boolean>(true);
  const [countdownActive, setCountdownActive] = useState<boolean>(false);
  const [countdownSeconds, setCountdownSeconds] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  // Track settings changes
  useEffect(() => {
    // Apply is only possible, if templates are selected, and frequency and days is > 0
    if (
      selectedTemplates.length === 0 ||
      simulationFrequency <= 0 ||
      simulationTimeInDays <= 0 ||
      stepsize <= 0
    ) {
      console.log("Invalid settings");
      setApplyEnabled(false);
      return;
    }

    // If countdown is active, keep button disabled
    if (countdownActive) {
      setApplyEnabled(false);
      return;
    }

    // if no current applied settings --> apply enabled
    if (!appliedSettings) {
      setApplyEnabled(true);
      return;
    }

    const settingsChanged =
      getSimulationFrequencyInSeconds() !==
        appliedSettings.simulationFrequency ||
      simulationTimeInDays !== appliedSettings.simulationTimeInDays ||
      stepsize !== appliedSettings.stepsize ||
      selectedTemplates !== appliedSettings.templates;
    setApplyEnabled(settingsChanged);
  }, [
    selectedTemplates,
    simulationFrequency,
    simulationUnit,
    simulationTimeInDays,
    stepsize,
    countdownActive,
  ]);

  // Countdown effect
  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    if (countdownActive && countdownSeconds > 0) {
      intervalId = setInterval(() => {
        setCountdownSeconds((prev) => {
          if (prev <= 1) {
            setCountdownActive(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [countdownActive, countdownSeconds]);

  // Fetch template cache when component mounts
  useEffect(() => {
    fetchTemplateCache();
    console.log(templateNames);
    console.log(templateCache);
  }, [fetchTemplateCache]);

  // Convert simulation frequency from user defined units to seconds
  const getSimulationFrequencyInSeconds = () => {
    switch (simulationUnit) {
      case "minutes":
        return simulationFrequency * 60;
      case "hours":
        return simulationFrequency * 3600;
      default:
        return simulationFrequency;
    }
  };

  // Run simulation function - uses current appliedSettings from store
  const runSimulation = async () => {
    console.log(templateNames);
    console.log(templateCache);
    // Check if we have applied settings and templates
    if (
      !appliedSettings ||
      !appliedSettings.templates ||
      appliedSettings.templates.length === 0
    ) {
      console.log("No applied settings or templates found");
      return;
    }

    // Build payloads for all templates in appliedSettings
    const payloads = [];

    for (const templateName of appliedSettings.templates) {
      // Find the corresponding template from cache
      const template = templateCache.find(
        (t) => t.templateName === templateName,
      );

      if (!template) {
        console.warn(`Template '${templateName}' not found in cache`);
        continue;
      }

      // Build payload for this template
      const payload = {
        templateName: template.templateName,
        scenario_settings: {
          ...template.scenario_settings,
        },
        fmu_settings: {
          stepsize: appliedSettings.stepsize,
          sim_days: appliedSettings.simulationTimeInDays,
        },
      };

      payloads.push(payload);
      console.log(`Prepared payload for template: ${template.templateName}`);
    }

    if (payloads.length === 0) {
      console.log("No valid templates found to run simulation");
      return;
    }
    // Send all payloads to the Python-API
    try {
      console.log(`Running simulation for ${payloads.length} templates`);

      const res = await fetch(getBackendUrl("/predict"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          scenarios: payloads, // Send array of payloads directly as dict
        }),
      });

      // Check for HTTP errors
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      // Check for errors in the response
      const data = await res.json();
      console.log("Simulation response:", data);

      // Check if response has success property and it's false, or if there's an error property
      if (data.success === false || data.error) {
        throw new Error(data.error || "Simulation failed");
      }

      console.log("Simulation published successfully for all templates");
      setError(null); // Clear any previous errors
    } catch (error: any) {
      console.error("Error running simulation:", error);
      setError(error.message);
    }
  };

  // Handle apply button selection
  const handleApply = () => {
    if (selectedTemplates.length === 0 || countdownActive) return;

    // Store the applied settings
    setAppliedSettings({
      templates: selectedTemplates,
      simulationFrequency: getSimulationFrequencyInSeconds(),
      simulationTimeInDays: simulationTimeInDays,
      stepsize: stepsize,
    });

    // Start countdown
    setCountdownActive(true);
    setCountdownSeconds(20);
    setApplyEnabled(false);
  };

  // Run Simulation with periodic execution
  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    if (appliedSettings) {
      // Run simulation immediately when applied settings change
      runSimulation();

      // Set up interval to run simulation every appliedSettings.simulationFrequency seconds
      intervalId = setInterval(() => {
        runSimulation();
      }, appliedSettings.simulationFrequency * 1000);
    }

    // Cleanup interval when appliedSettings change or component unmounts
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [appliedSettings]);

  return (
    <div className="grid gap-4">
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <strong>Error:</strong> {error}
        </div>
      )}
      <div className="flex items-center justify-between">
        <PageTitle title="Live Data" />

        <div className="flex items-center gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Simulation Frequency
            </label>
            <div className="flex items-center w-fit rounded-md border border-input focus-within:ring-2 focus-within:ring-ring">
              <Input
                type="number"
                value={simulationFrequency}
                onChange={(e) => setSimulationFrequency(Number(e.target.value))}
                placeholder="Enter frequency in seconds"
                className="rounded-r-none border-none focus-visible:ring-0 focus-visible:ring-offset-0 w-20"
              ></Input>

              <Select value={simulationUnit} onValueChange={setSimulationUnit}>
                <SelectTrigger className="rounded-l-none border-l border-input border-t-0 border-b-0 border-r-0 w-28 focus:ring-0 focus:ring-offset-0">
                  <SelectValue placeholder="Unit" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="seconds">Seconds</SelectItem>
                  <SelectItem value="minutes">Minutes</SelectItem>
                  <SelectItem value="hours">Hours</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Simulation Time
            </label>
            <div className="flex items-center w-fit rounded-md border border-input focus-within:ring-2 focus-within:ring-ring">
              <Input
                type="number"
                value={simulationTimeInDays}
                onChange={(e) =>
                  setSimulationTimeInDays(Number(e.target.value))
                }
                placeholder="Enter time"
                className="rounded-r-none border-none focus-visible:ring-0 focus-visible:ring-offset-0 w-20"
              ></Input>

              <span className="px-3 py-2 text-sm rounded-l-none rounded-md border-l border-input w-16">
                days
              </span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Stepsize
            </label>
            <div className="flex items-center w-fit rounded-md border border-input focus-within:ring-2 focus-within:ring-ring">
              <Input
                type="number"
                value={stepsize}
                onChange={(e) => setStepsize(Number(e.target.value))}
                placeholder="Enter stepsize"
                className="rounded-r-none border-none focus-visible:ring-0 focus-visible:ring-offset-0 w-20"
              ></Input>

              <span className="px-3 py-2 text-sm rounded-l-none rounded-md border-l border-input w-16">
                sec
              </span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Select Template
            </label>
            <Popover open={open} onOpenChange={setOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={open}
                  className="w-[200px] justify-between overflow-hidden text-ellipsis whitespace-nowrap"
                >
                  {selectedTemplates.length > 0
                    ? `${selectedTemplates.length} template${
                        selectedTemplates.length > 1 ? "s" : ""
                      } selected`
                    : "Select template..."}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[200px] p-0">
                <Command>
                  <CommandInput placeholder="Search template..." />
                  <CommandList>
                    <CommandEmpty>No template found.</CommandEmpty>
                    <CommandGroup>
                      <CommandItem onSelect={selectAll}>
                        ✅ Select All
                      </CommandItem>
                      <CommandItem onSelect={clearAll}>
                        ❌ Clear All
                      </CommandItem>
                    </CommandGroup>
                    <CommandGroup heading="Templates">
                      {templateNames.map((template) => (
                        <CommandItem
                          key={template}
                          value={template}
                          onSelect={(currentValue) => {
                            if (selectedTemplates.includes(currentValue)) {
                              // Deselect
                              setSelectedTemplates(
                                selectedTemplates.filter(
                                  (t) => t !== currentValue,
                                ),
                              );
                            } else {
                              // Select
                              setSelectedTemplates([
                                ...selectedTemplates,
                                currentValue,
                              ]);
                            }
                          }}
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              isSelected(template)
                                ? "opacity-100"
                                : "opacity-0",
                            )}
                          />
                          {template}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>
          <div>
            <Button
              className="mt-4"
              onClick={handleApply}
              disabled={!applyEnabled || countdownActive}
              variant={applyEnabled && !countdownActive ? "default" : "outline"}
            >
              {countdownActive ? `Apply (${countdownSeconds}s)` : "Apply"}
            </Button>
          </div>
        </div>
      </div>
      <div className="grid flex-1 items-stretch gap-4 sm:grid-cols-4">
        <LineChartCard />
        <PerformanceCard />
        <BooleanValuesCard />
        <SetValueCard />
      </div>
    </div>
  );
}
