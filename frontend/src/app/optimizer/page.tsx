"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogPortal,
  AlertDialogOverlay,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { InfrastructurePlan } from "@/components/infrastructure/InfrastructurePlan";
import "katex/dist/katex.min.css";
import Latex from "@matejmazur/react-katex";
import { cn } from "@/lib/utils";
import { Slider } from "@/components/ui/slider";
import { ButtonGroup } from "@/components/ui/button-group";
import PageTitle from "@/components/PageTitle";
import { useDashboardStore } from "@/stores/store";
import { InputConfigs } from "@/types/config";
import { useInputState } from "@/hooks/useInputState";
import { useAlertDialog } from "@/hooks/useAlertDialog";
import { useOptimizerValidation } from "@/hooks/useOptimizerValidation";
import { Separator } from "@/components/ui/separator";
import { Timer, LoaderCircleIcon } from "lucide-react";
import { formatTimeRemaining } from "@/lib/formatTimeRemaining";
import { inputConfig as inputConfigsRaw } from "@/config/infrastructure-config";
import useTemplateNameAutocomplete from "@/hooks/useTemplateNameAutocomplete";
import { getBackendUrl } from "@/lib/backend-url";
import { optimizerDefaults } from "@/config/optimizer-defaults";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import { getOptimizedTemplateName } from "@/lib/template-utils";

const inputConfigs: InputConfigs = inputConfigsRaw;

export default function ScenarioSettingsPage() {
  // Use store for template cache
  const { templateCache, fetchTemplateCache } = useDashboardStore();
  // Ref for template name input
  const inputRef = useRef<HTMLInputElement | null>(null);
  // Ref for clicking outside suggestions menu
  const wrapperRef = useRef<HTMLDivElement>(null);
  // Ref to track if results have been saved for the current optimization run
  const hasSavedResultsRef = useRef(false);

  // Use custom hooks for state management
  const {
    inputs,
    inputErrors,
    setInputErrors,
    selectedInput,
    setSelectedInput,
    handleInputChange,
  } = useInputState(inputConfigs);

  // Alert dialog hook
  const {
    alertBoxOpen,
    setAlertBoxOpen,
    templateCreationError,
    alertMessage,
    countdown,
    showError,
    showSuccess,
  } = useAlertDialog();

  const { validateOptimizerName } = useOptimizerValidation();

  // Local state for optimizer-specific features
  const [error, setError] = useState<string | null>(null);
  const [templateName, setTemplateName] = useState<string>("");
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [optimizationDuration, setOptimizationDuration] = useState<number>(
    optimizerDefaults.optimizationDuration,
  );
  const [simDays, setSimDays] = useState<number>(optimizerDefaults.simDays);
  const [stepsize, setStepsize] = useState<number>(optimizerDefaults.stepsize);
  const [nCores, setNCores] = useState<number>(optimizerDefaults.nCores);
  const [optimizationRunning, setOptimizationRunning] = useState(false);
  const [sliderRanges, setSliderRanges] = useState<Record<string, number[]>>(
    {},
  );
  const [progress, setProgress] = useState<number>(0);
  const [optimizationRemainingTime, setOptimizationRemainingTime] =
    useState<number>(0);
  const [nEvals, setNEvals] = useState<number>(0);
  const [bestPue, setBestPue] = useState<number | undefined>(undefined);
  const [optimizedValues, setOptimizedValues] = useState<Record<string, any>>(
    {},
  );
  const [optimizationStartTime, setOptimizationStartTime] = useState<
    string | null
  >(null);
  const [optimizationEndTime, setOptimizationEndTime] = useState<string | null>(
    null,
  );
  const [optimizationRunName, setOptimizationRunName] = useState<string | null>(
    null,
  );
  const optimizationStatusRef = useRef<HTMLDivElement | null>(null);
  const [backendAvailable, setBackendAvailable] = useState(true);
  const [isLoading, setIsLoading] = useState(true);

  const [conflictDialogOpen, setConflictDialogOpen] = useState(false);
  const [stopDialogOpen, setStopDialogOpen] = useState(false);
  const [conflictType, setConflictType] = useState<
    "optimizedExists" | "optimizedDateTimeExists" | "bothExists" | null
  >(null);
  const [conflictData, setConflictData] = useState<any>(null);
  const optimizationPayloadRef = useRef<any>(null);
  const [pendingSubmit, setPendingSubmit] = useState<any>(null);

  type InputMode = "off" | "range" | "value";
  const [enabledInputs, setEnabledInputs] = useState<Record<string, InputMode>>(
    () =>
      Object.fromEntries(
        Object.entries(inputConfigs).map(([key, config]) => [key, "range"]),
      ),
  );

  // Fetch template cache on mount
  useEffect(() => {
    console.log("Component mounted");
    fetchTemplateCache();
    return () => console.log("Component unmounted");
  }, [fetchTemplateCache]);

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  // Function to check if optimization is currently running
  const checkOptimizationStatus = async () => {
    try {
      const res = await fetch(getBackendUrl("/optimize/status"));
      if (!res.ok) throw new Error("Failed to check optimization status");
      const data = await res.json();
      return data.is_running;
    } catch (err) {
      console.error("Error checking optimization status:", err);
      return false;
    }
  };

  // Function to start optimization
  const startOptimization = async (payload: any) => {
    const response = await fetch(getBackendUrl("/optimize"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const err = await response.json();

      if (response.status === 409) {
        throw new Error(
          "An optimization is already running. Please wait for it to complete before starting a new one.",
        );
      }

      throw new Error(err.detail || "Failed to start optimization");
    }

    const data = await response.json();
    return data;
  };

  // Function to handle optimization start with user input validation
  const handleStartOptimizationValidation = async () => {
    // First, check if optimization is already running
    const isOptimizationRunning = await checkOptimizationStatus();
    // If already running, show error and return
    if (isOptimizationRunning) {
      showError(
        "An optimization is already running. The optimization status is now visible.",
      );
      setOptimizationRunning(true);
      return;
    }

    // Build scenario settings based on enabled inputs
    const scenario_settings: Record<string, any> = {};

    // Iterate over enabled inputs to build scenario settings
    Object.entries(enabledInputs).forEach(([key, mode]) => {
      // Set scenario settings based on selected mode

      // If mode is "off", do not include this setting in the payload
      // Value will be defaulted by backend
      if (mode === "off") {
        return;
      }

      const config = inputConfigs[key];

      // If mode is "range", include lower and upper bounds
      if (mode === "range") {
        if (config.unit === "bool") {
          // For boolean, send true/false for upper/lower bounds
          scenario_settings[key] = [true, false];
        } else {
          // Include user-defined value lower and upper bounds or defaults
          let [lower, upper] = sliderRanges[key] ?? [
            "min_value" in config ? (config.min_value ?? 0) : 0,
            "max_value" in config ? (config.max_value ?? 1) : 1,
          ];

          scenario_settings[key] = [lower, upper];
        }
      }

      // If mode is "value", include specific value
      if (mode === "value") {
        // Include user-defined value
        let value = inputs[key];
        scenario_settings[key] = value;
      }
    });

    const optimizedName = getOptimizedTemplateName(templateName);

    // Construct payload to send to backend
    const payload = {
      opt_name: optimizedName,
      opt_variable_settings: scenario_settings,
      fmu_settings: {
        stepsize: stepsize * 60, // convert minutes to seconds
        sim_days: simDays,
      },
      optimization_settings: {
        opt_time: optimizationDuration * 60, // convert minutes to seconds
        n_cores: nCores,
      },
    };

    console.log("Optimizer Payload", payload);
    optimizationPayloadRef.current = payload;

    // If not running, proceed to validate inputs and start optimization
    // Validate template using the validation hook

    const validationResult = validateOptimizerName(
      templateName,
      inputs,
      inputConfigs,
    );
    if (!validationResult.isValid) {
      optimizationPayloadRef.current = payload;
      console.log("Validation Result:", validationResult);
      console.log("Handling validation error:", validationResult.errorType);
      switch (validationResult.errorType) {
        case "validation":
          setInputErrors(validationResult.errorData);
          showError(<>Please correct the errors in template settings.</>);
          break;
        case "emptyName":
          showError(
            <>
              Optimizer run name is empty.
              <br />
              Please choose an optimization run name to save the optimized
              settings.
            </>,
          );
          break;
        case "bothExists":
        case "optimizedExists":
        case "optimizedDateTimeExists":
          setConflictType(validationResult.errorType);
          setConflictData(validationResult.errorData);
          setPendingSubmit(() => async (overridePayload?: any) => {
            const finalPayload =
              overridePayload ?? optimizationPayloadRef.current;
            try {
              await fetch("/api/save_optimization_settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  data: finalPayload,
                }),
              });

              console.log("Saved optimization Settings");
            } catch (err) {
              console.error("Failed to save optimization settings:", err);
            }

            proceedStartOptimization(finalPayload);
          });
          console.log("Opening conflict dialog");
          setConflictDialogOpen(true);
          return;
      }
      return;
    }
    if (validationResult.isValid) {
      try {
        await fetch("/api/save_optimization_settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            data: payload,
          }),
        });

        console.log("Saved optimization Settings");
      } catch (err) {
        console.error("Failed to save optimization settings:", err);
      }
      proceedStartOptimization(payload);
      return;
    }
  };

  // Function to actually start optimization after validation
  const proceedStartOptimization = async (payload: any) => {
    console.log("Starting Optimization");
    hasSavedResultsRef.current = false;
    setOptimizationRunning(true);
    setProgress(0);
    setNEvals(0);
    setOptimizationRunName(payload.opt_name);
    setOptimizationRemainingTime(optimizationDuration * 60);

    // Send request to start optimization
    try {
      const result = await startOptimization(payload);
      console.log("Optimization started:", result);
      setOptimizedValues({});

      setOptimizationStartTime(result.start_time);
      setOptimizationEndTime(result.expected_end_time);

      // Update optimization settings with start and end time
      await fetch("/api/save_optimization_settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          opt_name: payload.opt_name,
          start_time: result.start_time,
          end_time: result.expected_end_time,
        }),
      });
    } catch (error: any) {
      setOptimizationRunning(false);
      setOptimizationRunName(null);
      showError(
        <>
          ❌ Failed to start optimization:{" "}
          <strong style={{ color: "red" }}>{error.message}</strong>
        </>,
      );
    }
  };

  // Auto-scroll page to optimization status when optimization starts
  useEffect(() => {
    if (optimizationRunning && optimizationStatusRef.current) {
      optimizationStatusRef.current.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [optimizationRunning]);

  // Function to save optimization results
  const saveOptimizationResults = async (
    templateName: string,
    optimizedValues: any,
    kpis: any,
    startedAt: string,
    nEvals: number,
    bestPue: number | undefined,
    showNotification: boolean = true,
  ) => {
    try {
      console.log("Saving optimization results for:", templateName);

      // Update end_time in optimization settings
      await fetch("/api/save_optimization_settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          opt_name: templateName,
          end_time: new Date().toISOString(),
          nEvals: nEvals,
          bestPue: bestPue,
        }),
      });

      // Save optimization results to template cache
      const response = await fetch("/api/optimization_complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          templateName: templateName,
          optimized_values: optimizedValues,
          kpis: kpis || {},
        }),
      });

      const data = await response.json();
      if (data.success) {
        console.log("Results saved successfully!");
        if (showNotification) {
          showSuccess("Optimization results saved to template cache.");
        }
        localStorage.setItem("lastSavedOptimizationStart", startedAt);
        fetchTemplateCache();
      } else {
        console.error("Failed to save results:", data.error);
      }
    } catch (error) {
      console.error("Failed to save results:", error);
    }
  };

  // Function to stop optimization
  const handleStopOptimization = async () => {
    try {
      const res = await fetch(getBackendUrl("/optimize/stop"), {
        method: "DELETE",
      });

      if (!res.ok) {
        throw new Error("Failed to stop optimization");
      }

      const data = await res.json();

      // Save results if available
      if (
        data.res_obj.optimized_values &&
        Object.keys(data.res_obj.optimized_values).length > 0
      ) {
        await saveOptimizationResults(
          data.res_obj.opt_name || optimizationRunName || "stopped_run",
          data.res_obj.optimized_values,
          data.res_obj.kpis,
          data.res_obj.started_at ||
            optimizationStartTime ||
            new Date().toISOString(),
          data.res_obj.n_evals || nEvals,
          data.res_obj.best_pue,
          false, // No success message as requested
        );
      }

      // Null the status
      setOptimizationRunning(false);
      setOptimizationStartTime(null);
      setOptimizationEndTime(null);
      setOptimizationRunName(null);
      setProgress(0);
      setOptimizationRemainingTime(0);
      setNEvals(0);
      setOptimizedValues({});
      hasSavedResultsRef.current = false;

      setStopDialogOpen(false);
    } catch (err) {
      console.error("Error stopping optimization:", err);
      showError("Failed to stop optimization");
      setStopDialogOpen(false);
    }
  };

  // Restore state from backend on component mount and poll every 20 seconds
  useEffect(() => {
    const fetchBackendStatus = async (isInitial = false) => {
      try {
        const res = await fetch(getBackendUrl("/optimize/status"));

        if (!res.ok) {
          if (isInitial) throw new Error("Backend unreachable");
          return;
        }

        const data = await res.json();
        setBackendAvailable(true);
        if (isInitial) console.log("Fetched backend optimization state:", data);

        if (data.is_running) {
          if (isInitial)
            console.log(
              "Backend optimization is running. Restoring optimizer state.",
            );
          setOptimizationRunning(true);
          setOptimizationStartTime(data.started_at);
          setOptimizationEndTime(data.expected_end_time);
          setOptimizationRunName(data.opt_name);
          setProgress(data.progress || 0);
          setOptimizationRemainingTime(data.remaining_time || 0);
          setNEvals(data.n_evals || 0);
          setBestPue(data.best_pue);

          if (data.optimized_values) {
            setOptimizedValues(data.optimized_values);
          }
          // Reset saved flag while running
          hasSavedResultsRef.current = false;
        } else if (data.is_finished) {
          // Optimization finished
          setOptimizationRunning(false);
          setProgress(100);
          setOptimizationRemainingTime(0);
          setNEvals(data.n_evals || 0);

          // Update values if available
          if (data.optimized_values) {
            setOptimizedValues(data.optimized_values);
          }
          if (data.opt_name) setOptimizationRunName(data.opt_name);
          if (data.started_at) setOptimizationStartTime(data.started_at);
          if (data.expected_end_time)
            setOptimizationEndTime(data.expected_end_time);

          // Save results if not already saved
          const lastSavedStart = localStorage.getItem(
            "lastSavedOptimizationStart",
          );
          const isSavedInStorage = lastSavedStart === data.started_at;

          if (!hasSavedResultsRef.current && !isSavedInStorage) {
            await saveOptimizationResults(
              data.opt_name,
              data.optimized_values,
              data.kpis,
              data.started_at,
              data.n_evals,
              data.best_pue,
            );
            hasSavedResultsRef.current = true;
          } else {
            hasSavedResultsRef.current = true;
          }
        } else {
          if (isInitial) console.log("No optimization running on backend.");
          setOptimizationRunning(false);
          setOptimizationStartTime(null);
          setOptimizationEndTime(null);
          setOptimizationRunName(null);
          setProgress(0);
          setOptimizationRemainingTime(0);
          setNEvals(0);
          hasSavedResultsRef.current = false;
        }
      } catch (err) {
        console.error("Error connecting to backend:", err);
        if (isInitial) {
          setBackendAvailable(false);
          setOptimizationRunning(false);
        }
      } finally {
        if (isInitial) setIsLoading(false);
      }
    };

    // Initial fetch
    fetchBackendStatus(true);

    // Poll every 20 seconds
    const interval = setInterval(() => {
      fetchBackendStatus(false);
    }, 20000);

    return () => clearInterval(interval);
  }, []);

  // Use autocomplete hook for template name input
  const {
    searchValue,
    suggestions,
    activeSuggestion,
    isOpen,
    setIsOpen,
    setActiveSuggestion,
    setActiveItemRef,
    handleChange,
    handleKeyDown,
    handleClick,
    handleFocus,
  } = useTemplateNameAutocomplete(templateCache, inputRef, {
    onInputChange: setTemplateName,
    onConfirm: setSelectedTemplate,
  });

  // Auto-focus input when suggestions appear
  useEffect(() => {
    if (suggestions.length > 0 && inputRef.current) {
      inputRef.current.focus();
    }
  }, [suggestions]);

  // Function to apply optimization settings to the UI
  const applyOptimizationSettingsToUI = (optimizationSavedSettings: any) => {
    const {
      opt_name,
      opt_variable_settings = {},
      optimization_settings = {},
      fmu_settings = {},
      start_time,
      end_time,
      nEvals,
      bestPue,
    } = optimizationSavedSettings;

    const newEnabled: Record<string, InputMode> = {};
    const newRanges: Record<string, number[]> = {};
    const newValues: Record<string, any> = {};

    Object.entries(inputConfigs).forEach(([key, config]) => {
      const saved = opt_variable_settings[key];

      // OFF
      if (saved === undefined) {
        newEnabled[key] = "off";
        return;
      }

      // RANGE MODE → [lower, upper]
      if (Array.isArray(saved) && saved.length === 2) {
        newEnabled[key] = "range";

        if (config.unit !== "bool") {
          newRanges[key] = [saved[0], saved[1]];
        }
        return;
      }

      // VALUE MODE → number | boolean
      newEnabled[key] = "value";
      newValues[key] = saved;
    });

    // Apply modes
    setEnabledInputs((prev) => ({
      ...prev,
      ...newEnabled,
    }));

    // Apply ranges
    setSliderRanges((prev) => ({
      ...prev,
      ...newRanges,
    }));

    // Apply fixed values
    Object.entries(newValues).forEach(([key, value]) => {
      handleInputChange(key, value);
    });

    // Set saved optimization run name
    if (opt_name) {
      setOptimizationRunName(opt_name);
    }

    // Optimization duration
    if (typeof optimization_settings.opt_time === "number") {
      setOptimizationDuration(optimization_settings.opt_time / 60);
    }
    // Number of cores
    if (typeof optimization_settings.n_cores === "number") {
      setNCores(optimization_settings.n_cores);
    }

    // Stepsize
    if (typeof fmu_settings.stepsize === "number") {
      setStepsize(fmu_settings.stepsize / 60);
    }

    // Number of sim days
    if (typeof fmu_settings.sim_days === "number") {
      setSimDays(fmu_settings.sim_days);
    }

    // Set saved optimization start time
    if (start_time) {
      setOptimizationStartTime(start_time);
    }

    // Set saved optimization end time
    if (end_time) {
      setOptimizationEndTime(end_time);
    }

    // Set number of evaluations
    if (typeof nEvals === "number") {
      setNEvals(nEvals);
    }

    // Set best PUE
    if (typeof bestPue === "number") {
      setBestPue(bestPue);
    }
  };

  // Function to load optimized values into the UI
  const loadOptimizedValues = (scenarioSettings: Record<string, any>) => {
    setOptimizedValues({ ...scenarioSettings });
  };

  // Function to reset optimizer UI to default states
  const resetOptimizerUIToDefaults = () => {
    // Reset modes → default to RANGE
    setEnabledInputs(
      Object.fromEntries(
        Object.keys(inputConfigs).map((key) => [key, "range"]),
      ),
    );

    // Clear sliders (Fall back to config min/max)
    setSliderRanges({});

    // Reset optimized results
    setOptimizedValues({});

    // Reset optimization duration
    setOptimizationDuration(optimizerDefaults.optimizationDuration);

    // Reset number of cores
    setNCores(optimizerDefaults.nCores);

    // Reset stepsize
    setStepsize(optimizerDefaults.stepsize);

    // Reset number of sim days
    setSimDays(optimizerDefaults.simDays);

    // Clear optimization run name
    setOptimizationRunName(null);

    // Clear optimization start/end time
    setOptimizationStartTime(null);
    setOptimizationEndTime(null);

    // Clear number of evaluations and best PUE
    setNEvals(0);
    setBestPue(undefined);
  };

  // Load optimization settings and optimized values when templateName changes
  useEffect(() => {
    if (!selectedTemplate || templateCache.length === 0) return;

    const loadOptimizerState = async () => {
      try {
        // Fetch saved optimization settings
        const res = await fetch("/api/save_optimization_settings");
        const data = await res.json();

        // Load saved optimization settings for the selected template
        const optimizationSavedSettings = data.settingsArray.find(
          (e: any) => e.opt_name === selectedTemplate,
        );

        if (optimizationSavedSettings) {
          applyOptimizationSettingsToUI(optimizationSavedSettings);
        } else {
          resetOptimizerUIToDefaults();
        }

        // Load optimized values if available
        const optimizedTemplate = templateCache.find(
          (t) => t.templateName === selectedTemplate,
        );

        if (optimizedTemplate?.scenario_settings) {
          loadOptimizedValues(optimizedTemplate.scenario_settings);
        } else {
          setOptimizedValues({});
        }
      } catch (err) {
        console.error("Failed to load optimizer state:", err);
      }
    };

    loadOptimizerState();
  }, [selectedTemplate, templateCache]);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {isLoading && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-2">
            <LoaderCircleIcon className="w-10 h-10 text-primary animate-spin" />
            <p className="text-muted-foreground">Connecting to backend...</p>
          </div>
        </div>
      )}
      {!isLoading && !backendAvailable && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background">
          <div className="p-6 bg-destructive/10 border border-destructive rounded-lg shadow-lg text-center">
            <h3 className="text-lg font-semibold text-destructive mb-2">
              Backend Unavailable
            </h3>
            <p className="text-muted-foreground">
              The optimization backend is not running or unreachable.
              <br />
              Please check the backend service.
            </p>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => window.location.reload()}
            >
              Retry Connection
            </Button>
          </div>
        </div>
      )}
      <div className="flex items-center justify-between">
        <PageTitle title="Optimizer Settings" />
      </div>
      <div className="grid gap-4 flex-1 min-h-0 relative overflow-hidden">
        <div className="grid flex-1 gap-4 min-h-0 sm:grid-cols-10 overflow-hidden">
          <Card className="2xl:col-span-5 md:col-span-10 h-full flex flex-col min-h-0">
            <CardContent className="flex-1 min-h-0 overflow-y-auto">
              <div
                ref={wrapperRef}
                className="grid w-full items-center gap-1.5 mt-4 relative"
              >
                <label className="block">
                  <span>Optimization run name:</span>
                </label>
                <Popover open={isOpen} onOpenChange={setIsOpen}>
                  <PopoverTrigger asChild>
                    <Input
                      type="text"
                      value={searchValue}
                      onChange={handleChange}
                      onKeyDown={handleKeyDown}
                      onFocus={() => {
                        handleFocus();
                        setIsOpen(true);
                      }}
                      onBlur={(e) => {
                        // close only if click is outside popover
                        if (
                          !wrapperRef.current?.contains(e.relatedTarget as Node)
                        ) {
                          setIsOpen(false);
                        }
                      }}
                      ref={inputRef}
                      placeholder="Type an optimization template name..."
                      disabled={optimizationRunning}
                      className={cn(
                        optimizationRunning
                          ? "bg-gray-200 cursor-not-allowed"
                          : "",
                      )}
                    />
                  </PopoverTrigger>
                  <PopoverContent
                    className="w-[var(--radix-popover-trigger-width)] max-h-40 overflow-y-auto scroll-smooth"
                    align="start"
                    onMouseDown={(e) => e.preventDefault()}
                  >
                    {suggestions.map((template, idx) => {
                      const isActive = idx === activeSuggestion;

                      return (
                        <div
                          key={idx}
                          ref={isActive ? setActiveItemRef : null}
                          className={cn(
                            "w-full px-2 py-1 rounded-md cursor-pointer",
                            isActive
                              ? "bg-accent text-accent-foreground"
                              : "hover:bg-accent hover:text-accent-foreground",
                          )}
                          onMouseEnter={() => setActiveSuggestion(idx)}
                          onClick={() => handleClick(template)}
                        >
                          {template.templateName}
                        </div>
                      );
                    })}
                  </PopoverContent>
                </Popover>
                <div className="mt-1 space-y-1 text-sm italic text-gray-500">
                  <div className="flex gap-2">
                    <span className="before:content-['•'] before:mr-2 before:text-gray-400">
                      The optimized settings will be saved and be available as
                      template on the scenario dashboard. Click or press Enter
                      on the listed template name suggestions to load the saved
                      optimization settings and optimized values.
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <span className="before:content-['•'] before:mr-2 before:text-gray-400">
                      For a new and unique run names, the{" "}
                      <code>'_optimized'</code> suffix will be appended to the
                      run name
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <span className=" before:mr-4 before:text-gray-400">
                      eg. Run name = 'MyTemplate'; Saved template name =
                      'MyTemplate_optimized'.
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <span className="before:content-['•'] before:mr-2 before:text-gray-400">
                      Subsequent optimizations with the same run name can be
                      saved with an appended datetime (eg.
                      'MyTemplate_optimized_01.01.2026_00:00:00')
                    </span>
                  </div>
                </div>
              </div>
              <Separator className="my-4" />
              <div className="space-y-4">
                <div className="grid grid-cols-[192px_192px_96px_150px_96px] gap-4 items-center">
                  <div>Parameter</div>
                  <div className="text-center font-medium text-gray-600">
                    Optimization mode
                  </div>
                  <div className="text-center font-medium text-gray-600">
                    Value
                  </div>
                  <div className="text-center font-medium text-gray-600">
                    Range
                  </div>
                  <div className="text-center font-medium text-gray-600">
                    Optimized values
                  </div>
                </div>
                {Object.entries(inputConfigs).map(([key, config], idx) => (
                  <div
                    key={key}
                    className="grid grid-cols-[192px_192px_96px_150px_96px] gap-4 items-center"
                  >
                    <label className="w-48 text-sm font-medium shrink-0">
                      <Latex math={config.name} />
                    </label>
                    <div className="w-[200px] shrink-0">
                      {config.unit === "bool" ? (
                        <ButtonGroup className="w-full">
                          <Button
                            className="flex-1"
                            variant={
                              enabledInputs[key] === "off"
                                ? "default"
                                : "outline"
                            }
                            onClick={() =>
                              setEnabledInputs((prev) => ({
                                ...prev,
                                [key]: "off",
                              }))
                            }
                            disabled={optimizationRunning}
                          >
                            Off
                          </Button>
                          <Button
                            className="min-w-[4.7rem] flex-1"
                            variant={
                              enabledInputs[key] === "range"
                                ? "default"
                                : "outline"
                            }
                            onClick={() =>
                              setEnabledInputs((prev) => ({
                                ...prev,
                                [key]: "range",
                              }))
                            }
                            disabled={optimizationRunning}
                          >
                            Opt
                          </Button>
                          <Button
                            className="flex-1"
                            variant={
                              enabledInputs[key] === "value"
                                ? "default"
                                : "outline"
                            }
                            onClick={() =>
                              setEnabledInputs((prev) => ({
                                ...prev,
                                [key]: "value",
                              }))
                            }
                            disabled={optimizationRunning}
                          >
                            Value
                          </Button>
                        </ButtonGroup>
                      ) : (
                        <ButtonGroup className="w-full">
                          <Button
                            className="flex-1"
                            variant={
                              enabledInputs[key] === "off"
                                ? "default"
                                : "outline"
                            }
                            onClick={() =>
                              setEnabledInputs((prev) => ({
                                ...prev,
                                [key]: "off",
                              }))
                            }
                            disabled={optimizationRunning}
                          >
                            Off
                          </Button>
                          <Button
                            className="min-w-[4.7rem] flex-1"
                            variant={
                              enabledInputs[key] === "range"
                                ? "default"
                                : "outline"
                            }
                            onClick={() =>
                              setEnabledInputs((prev) => ({
                                ...prev,
                                [key]: "range",
                              }))
                            }
                            disabled={optimizationRunning}
                          >
                            Range
                          </Button>
                          <Button
                            className="flex-1"
                            variant={
                              enabledInputs[key] === "value"
                                ? "default"
                                : "outline"
                            }
                            onClick={() =>
                              setEnabledInputs((prev) => ({
                                ...prev,
                                [key]: "value",
                              }))
                            }
                            disabled={optimizationRunning}
                          >
                            Value
                          </Button>
                        </ButtonGroup>
                      )}
                    </div>
                    <div className="w-[90px] flex justify-center shrink-0">
                      {config.unit === "bool" ? (
                        <Checkbox
                          checked={inputs[key] as boolean}
                          onCheckedChange={(checked) =>
                            handleInputChange(key, checked)
                          }
                          disabled={
                            enabledInputs[key] !== "value" ||
                            optimizationRunning
                          }
                          className={cn(
                            optimizationRunning
                              ? "bg-gray-200 cursor-not-allowed"
                              : "",
                          )}
                        />
                      ) : (
                        <Input
                          type="number"
                          value={inputs[key] as number}
                          onClick={() => setSelectedInput(key)}
                          onChange={(e) =>
                            handleInputChange(key, e.target.value)
                          }
                          disabled={
                            enabledInputs[key] !== "value" ||
                            optimizationRunning
                          }
                          className={cn(
                            "w-20 text-center border border-gray-300 focus:border-primary rounded-md px-2 py-1 transition-colors",
                            selectedInput === key && "border-primary",
                            optimizationRunning &&
                              "bg-gray-200 cursor-not-allowed",
                          )}
                          min={
                            "min_value" in config ? config.min_value : undefined
                          }
                          max={
                            "max_value" in config ? config.max_value : undefined
                          }
                          step={idx < 11 ? 0.2 : 0.05}
                        />
                      )}
                    </div>
                    <div className="flex flex-col items-center flex-grow min-w-[150px] max-w-[260px] px-2">
                      {config.unit !== "bool" && (
                        <>
                          <Slider
                            value={
                              sliderRanges[key] ?? [
                                "min_value" in config
                                  ? (config.min_value ?? 0)
                                  : 0,
                                "max_value" in config
                                  ? (config.max_value ?? 100)
                                  : 100,
                              ]
                            }
                            onValueChange={(val) =>
                              setSliderRanges((prev) => ({
                                ...prev,
                                [key]: val as number[],
                              }))
                            }
                            min={
                              "min_value" in config
                                ? (config.min_value ?? 0)
                                : 0
                            }
                            max={
                              "max_value" in config
                                ? (config.max_value ?? 100)
                                : 100
                            }
                            step={idx < 11 ? 0.1 : 0.05}
                            disabled={
                              enabledInputs[key] !== "range" ||
                              optimizationRunning
                            }
                            className={cn(
                              "w-full transition-colors",
                              (enabledInputs[key] !== "range" ||
                                optimizationRunning) &&
                                "opacity-50 cursor-not-allowed",
                            )}
                          />
                          <div className="flex justify-between w-full text-xs text-gray-500 mt-1">
                            <span>
                              {sliderRanges[key]
                                ? sliderRanges[key][0].toFixed(1)
                                : "min_value" in config
                                  ? (config.min_value ?? 0)
                                  : "--"}
                            </span>
                            <span>
                              {sliderRanges[key]
                                ? sliderRanges[key][1].toFixed(1)
                                : "max_value" in config
                                  ? (config.max_value ?? 100)
                                  : "--"}
                            </span>
                          </div>
                        </>
                      )}
                    </div>
                    <div className="w-[96px] text-center font-semibold text-green-700 text-sm bg-green-100 rounded-full px-2 py-1">
                      {optimizedValues[key] !== undefined
                        ? typeof optimizedValues[key] === "number"
                          ? optimizedValues[key].toFixed(2)
                          : optimizedValues[key].toString()
                        : "-"}
                    </div>

                    {inputErrors[key] && (
                      <p className="text-sm text-red-500 ml-48">
                        {inputErrors[key]}
                      </p>
                    )}
                  </div>
                ))}
                <Separator className="my-4" />
                <div className="flex flex-wrap items-center gap-4 justify-between w-full">
                  <div className="flex items-center gap-2">
                    <label className="font-medium whitespace-nowrap text-sm">
                      Sim Days
                    </label>
                    <Input
                      type="number"
                      value={simDays}
                      onChange={(e) => setSimDays(Number(e.target.value))}
                      min={1}
                      disabled={optimizationRunning}
                      className={cn(
                        "w-20",
                        optimizationRunning
                          ? "bg-gray-200 cursor-not-allowed"
                          : "",
                      )}
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <label className="font-medium whitespace-nowrap text-sm">
                      Stepsize (min)
                    </label>
                    <Input
                      type="number"
                      value={stepsize}
                      onChange={(e) => setStepsize(Number(e.target.value))}
                      min={1}
                      disabled={optimizationRunning}
                      className={cn(
                        "w-20",
                        optimizationRunning
                          ? "bg-gray-200 cursor-not-allowed"
                          : "",
                      )}
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <label className="font-medium whitespace-nowrap text-sm">
                      Cores
                    </label>
                    <Input
                      type="number"
                      value={nCores}
                      onChange={(e) => setNCores(Number(e.target.value))}
                      min={1}
                      disabled={optimizationRunning}
                      className={cn(
                        "w-20",
                        optimizationRunning
                          ? "bg-gray-200 cursor-not-allowed"
                          : "",
                      )}
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <label className="font-medium whitespace-nowrap text-sm">
                      Duration (min)
                    </label>
                    <Input
                      type="number"
                      value={optimizationDuration}
                      onChange={(e) =>
                        setOptimizationDuration(Number(e.target.value))
                      }
                      min={0}
                      max={24 * 60}
                      disabled={optimizationRunning}
                      className={cn(
                        "w-20",
                        optimizationRunning
                          ? "bg-gray-200 cursor-not-allowed"
                          : "",
                      )}
                    />
                  </div>

                  <Button
                    onClick={handleStartOptimizationValidation}
                    disabled={optimizationRunning}
                    className={cn(
                      "text-sm ml-auto",
                      optimizationRunning
                        ? "opacity-50 pointer-events-none cursor-not-allowed"
                        : "cursor-pointer",
                    )}
                  >
                    {optimizationRunning
                      ? "Optimizing..."
                      : "Start optimization"}
                  </Button>

                  <AlertDialog
                    open={alertBoxOpen}
                    onOpenChange={setAlertBoxOpen}
                  >
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>
                          {templateCreationError ? "Error Message" : "Success!"}
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                          {alertMessage}
                          {/* For countdown in alert message box */}
                          {!templateCreationError && (
                            <>
                              <br />
                              <span>
                                This message will close in {countdown}{" "}
                                seconds...
                              </span>
                            </>
                          )}
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Close</AlertDialogCancel>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
                <div ref={optimizationStatusRef}>
                  <Separator className="my-4" />
                  <CardHeader className="pb-3 flex flex-row items-center justify-between px-0">
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-lg">
                        Optimization Status
                      </CardTitle>
                      {optimizationRunning && (
                        <LoaderCircleIcon className="w-5 h-5 text-blue-600 animate-spin" />
                      )}
                    </div>
                    {optimizationRunning && (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setStopDialogOpen(true)}
                      >
                        Stop
                      </Button>
                    )}
                  </CardHeader>
                  <Separator className="my-4" />

                  <p className="text-sm text-muted-foreground mt-2">
                    Optimization run name:{" "}
                    <span className="font-medium text-foreground">
                      {optimizationRunName || "-"}
                    </span>
                  </p>

                  <p className="text-sm text-muted-foreground mt-2">
                    Optimization start:{" "}
                    <span className="font-medium text-foreground">
                      {optimizationStartTime &&
                      !isNaN(new Date(String(optimizationStartTime)).getTime())
                        ? new Date(
                            String(optimizationStartTime),
                          ).toLocaleString()
                        : "-"}
                    </span>
                  </p>

                  <p className="text-sm text-muted-foreground mt-2 flex items-center gap-1">
                    Optimization end:
                    <span className="font-medium text-foreground">
                      {optimizationEndTime
                        ? new Date(String(optimizationEndTime)).toLocaleString()
                        : "-"}
                    </span>
                  </p>

                  <p className="text-sm text-muted-foreground mt-2 flex items-center gap-1">
                    Optimization time remaining:
                    <span className="font-medium text-foreground">
                      {formatTimeRemaining(optimizationRemainingTime)}
                    </span>
                    <Timer className="w-4 h-4 text-blue-600 animate-pulse" />
                  </p>

                  <p className="text-sm text-muted-foreground mt-2 flex items-center gap-1">
                    Number of evaluations:
                    <span className="font-medium text-foreground">
                      {nEvals}
                    </span>
                  </p>

                  <p className="text-sm text-muted-foreground mt-2 flex items-center gap-1">
                    Optimized pue:
                    <span className="font-medium text-foreground">
                      {bestPue !== undefined ? bestPue.toFixed(3) : "-"}
                    </span>
                  </p>

                  <div className="w-full mt-4 mb-6">
                    {" "}
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-muted-foreground">
                        Progress
                      </span>
                      <span className="text-sm font-medium text-muted-foreground">
                        {progress}%
                      </span>
                    </div>
                    <div className="h-3 bg-secondary rounded-full overflow-hidden">
                      <div
                        className="h-3 bg-blue-500 rounded-full transition-all duration-300"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
              <AlertDialog
                open={stopDialogOpen}
                onOpenChange={setStopDialogOpen}
              >
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Stop Optimization?</AlertDialogTitle>
                    <AlertDialogDescription>
                      Warning: This will kill the optimization and it cannot be
                      resumed.
                      <br />
                      The last optimized values will be written to the template
                      settings, if there have been some so far.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleStopOptimization}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                      Stop Optimization
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
              <AlertDialog
                open={conflictDialogOpen}
                onOpenChange={setConflictDialogOpen}
              >
                <AlertDialogPortal>
                  <AlertDialogOverlay className="fixed inset-0 bg-black/50" />

                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>
                        Template name conflict
                      </AlertDialogTitle>

                      {/* Both optimized and optimized_(datetime) templates exist */}
                      {conflictType === "bothExists" && (
                        <AlertDialogDescription asChild>
                          <div>
                            The optimized and dated templates already exist:
                            <ul className="list-disc ml-5 mt-2">
                              <li className="font-bold text-red-600">
                                {conflictData}
                              </li>
                              <li className="font-bold text-red-600">
                                {conflictData}_date(s)
                              </li>
                            </ul>
                            <div className="mt-3">
                              What would you like to do?
                            </div>
                          </div>
                        </AlertDialogDescription>
                      )}

                      {/* Only optimized template exists */}
                      {conflictType === "optimizedExists" && (
                        <AlertDialogDescription>
                          The optimized template{" "}
                          <strong style={{ color: "red" }}>
                            {conflictData}
                          </strong>{" "}
                          already exists.
                          <br />
                          What would you like to do?
                        </AlertDialogDescription>
                      )}

                      {/* Optimized date template exists */}
                      {conflictType === "optimizedDateTimeExists" && (
                        <AlertDialogDescription>
                          The optimized dateTime template version(s) of
                          <br />
                          <strong style={{ color: "red" }}>
                            {conflictData}
                          </strong>{" "}
                          <br />
                          already exist. What would you like to do?
                        </AlertDialogDescription>
                      )}
                    </AlertDialogHeader>

                    <AlertDialogFooter className="flex flex-col sm:flex-row flex-wrap gap-2">
                      {/* CANCEL */}
                      <AlertDialogCancel className="w-full sm:flex-1">
                        Cancel
                      </AlertDialogCancel>

                      {/* Overwrite or Save with current dateTime stamp */}
                      <>
                        <AlertDialogAction
                          className="w-full sm:flex-1"
                          onClick={() => {
                            const newName = `${conflictData}`;
                            const updatedPayload = {
                              ...optimizationPayloadRef.current,
                              templateName: newName,
                              opt_name: newName,
                            };
                            setConflictDialogOpen(false);
                            pendingSubmit?.(updatedPayload);
                          }}
                        >
                          Overwrite {conflictData}
                        </AlertDialogAction>

                        <AlertDialogAction
                          className="w-full sm:flex-1"
                          onClick={() => {
                            const now = new Date();
                            const stamp =
                              `${String(now.getDate()).padStart(2, "0")}.` +
                              `${String(now.getMonth() + 1).padStart(2, "0")}.` +
                              `${now.getFullYear()}_` +
                              `${String(now.getHours()).padStart(2, "0")}:` +
                              `${String(now.getMinutes()).padStart(2, "0")}:` +
                              `${String(now.getSeconds()).padStart(2, "0")}`;
                            const newName = `${conflictData}_${stamp}`;
                            const updatedPayload = {
                              ...optimizationPayloadRef.current,
                              templateName: newName,
                              opt_name: newName,
                            };
                            setConflictDialogOpen(false);
                            pendingSubmit?.(updatedPayload);
                          }}
                        >
                          Save a new template with current's datetime stamp as
                          suffix
                        </AlertDialogAction>
                      </>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialogPortal>
              </AlertDialog>
            </CardContent>
          </Card>
          <InfrastructurePlan
            inputs={inputs}
            selectedInput={selectedInput}
            onInputSelect={setSelectedInput}
            inputErrors={inputErrors}
            onInputChange={handleInputChange}
            configs={inputConfigs}
          />
        </div>
      </div>
    </div>
  );
}
