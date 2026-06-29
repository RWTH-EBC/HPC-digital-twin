"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { DataTable } from "./data-table";
import { columns } from "./columns";
import { InfrastructurePlan } from "@/components/infrastructure/InfrastructurePlan";
import "katex/dist/katex.min.css";
import Latex from "@matejmazur/react-katex";
import { cn } from "@/lib/utils";
import PageTitle from "@/components/PageTitle";
import { useDashboardStore } from "@/stores/store";
import { Template } from "@/types";
import { InputConfigs } from "@/types/config";
import { useInputState } from "@/hooks/useInputState";
import { useAlertDialog } from "@/hooks/useAlertDialog";
import { useTemplateValidation } from "@/hooks/useTemplateValidation";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import useTemplateNameAutocomplete from "@/hooks/useTemplateNameAutocomplete";
import { inputConfig as inputConfigsRaw } from "@/config/infrastructure-config";

const inputConfigs: InputConfigs = inputConfigsRaw;

export default function ScenarioSettingsPage() {
  // Use store for template cache
  const { templateCache, setTemplateCache, fetchTemplateCache } =
    useDashboardStore();

  // Use custom hooks for state management
  const {
    inputs,
    inputErrors,
    setInputErrors,
    selectedInput,
    setSelectedInput,
    handleInputChange,
  } = useInputState(inputConfigs);

  // Use alert dialog hook
  const {
    alertBoxOpen,
    setAlertBoxOpen,
    templateCreationError,
    alertMessage,
    countdown,
    showError,
    showSuccess,
  } = useAlertDialog();

  const inputRef = useRef<HTMLInputElement | null>(null);

  const { validateTemplate } = useTemplateValidation();

  const [error, setError] = useState<string | null>(null);
  const [templateName, setTemplateName] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

  // Ref for clicking outside suggestions menu
  const wrapperRef = useRef<HTMLDivElement>(null);

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
  } = useTemplateNameAutocomplete<Template>(templateCache, inputRef, {
    onInputChange: (value) => {
      setTemplateName(value);

      // Clear selected template if typed template name changes
      if (value !== selectedTemplate) {
        setSelectedTemplate(null);
      }
    },
    onConfirm: setSelectedTemplate, // Enter or click
  });

  // When templateName is selected, populate inputs if template exists
  useEffect(() => {
    if (!selectedTemplate) return;

    const template = templateCache.find(
      (t) => t.templateName === selectedTemplate,
    );

    // If template or scenario_settings not found, do nothing
    if (!template?.scenario_settings) return;

    // Apply saved values
    Object.entries(template.scenario_settings).forEach(([key, value]) => {
      if (key in inputConfigs) {
        handleInputChange(key, value);
      }
    });
  }, [selectedTemplate, templateCache]);

  // Handler to delete a specific scenario by timestamp and update cache file
  const handleDelete = async (templateName: string) => {
    try {
      const res = await fetch(
        `/api/cache-handling?templateName=${encodeURIComponent(templateName)}`,
        {
          method: "DELETE",
        },
      );
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      // Remove only the scenario with the matching timestamp
      const updatedCache = templateCache.filter(
        (scenario) => scenario.templateName !== templateName,
      );
      setTemplateCache(updatedCache);
    } catch (error: any) {
      console.error(error);
      setError(error.message);
    }
  };

  // Initial fetch of template cache
  useEffect(() => {
    fetchTemplateCache();
  }, [fetchTemplateCache]);

  // Handler to publish new template settings
  const handlePublish = async () => {
    const selectedTemplateName = templateName.trim();
    // Validate template using the validation hook
    const validationResult = validateTemplate(
      selectedTemplateName,
      inputs,
      inputConfigs,
    );

    if (!validationResult.isValid) {
      switch (validationResult.errorType) {
        case "validation":
          setInputErrors(validationResult.errorData);
          showError(<>Please correct the errors in template settings.</>);
          break;
        case "emptyName":
          showError(
            <>
              Template name cannot be empty.
              <br />
              Please type in a template name.
            </>,
          );
          break;
        case "duplicateName":
          showError(
            <>
              Template name:{" "}
              <strong style={{ color: "red" }}>
                {validationResult.errorData}
              </strong>{" "}
              already exists.
              <br />
              Please choose a different template name.
            </>,
          );
          break;
        case "duplicateInputs":
          showError(
            <>
              Template inputs already exist under another template name:{" "}
              <strong style={{ color: "red" }}>
                {validationResult.errorData}
              </strong>
              <br />
              Please choose different template settings.
            </>,
          );
          break;
      }
      return;
    }

    // If validation passes, show success and submit
    showSuccess(
      <>
        ✅{" "}
        <strong style={{ color: "green" }}>
          Successfully created a new template.
        </strong>
      </>,
      5,
    );

    const payload = {
      templateName: selectedTemplateName,
      scenario_settings: {
        ...inputs, // Spread all other inputs directly
      },
    };

    console.log("Payload", payload);
    try {
      const res = await fetch("/api/cache-handling", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: JSON.stringify(payload),
        }),
      });

      const data = await res.json();
      if (!data.success) throw new Error(data.error);
      console.log("Message published successfully");
      console.log(payload);

      // After successful creation, fetch the latest cache to ensure sync
      fetchTemplateCache();
    } catch (error: any) {
      console.error(error);
      setError(error.message);
    }
  };

  // Clear both caches
  const handleClearCaches = async () => {
    try {
      const res = await fetch("/api/cache-handling", {
        method: "DELETE",
      });

      const data = await res.json();
      if (!data.success) throw new Error(data.error);
      setTemplateCache([]);
      console.log("Caches cleared successfully");
    } catch (error: any) {
      console.error(error);
      setError(error.message);
    }
  };

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <PageTitle title="Template Settings" />
        <div className="flex items-center justify-between">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive">Clear all cached Templates</Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action cannot be undone. It will permanently delete your
                  cached template data.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleClearCaches}>
                  Continue
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
      <div className="grid flex-1 gap-4 sm:grid-cols-7">
        <Card className="2xl:col-span-2 md:col-span-7 max-h-[970px] overflow-y-auto">
          <CardContent>
            <div
              ref={wrapperRef}
              className="grid w-full max-w-sm items-center gap-1.5"
            >
              <label>Template Name:</label>
              <Popover open={isOpen} onOpenChange={setIsOpen}>
                <PopoverTrigger asChild>
                  <Input
                    ref={inputRef}
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
                    placeholder="Type a template name..."
                    className="w-full"
                  />
                </PopoverTrigger>

                <PopoverContent
                  className="w-[var(--radix-popover-trigger-width)] max-h-40 overflow-y-auto"
                  align="start"
                  onMouseDown={(e) => e.preventDefault()}
                >
                  {suggestions.map((template, idx) => {
                    const isActive = idx === activeSuggestion;

                    return (
                      <div
                        key={template.templateName}
                        ref={isActive ? setActiveItemRef : null}
                        className={cn(
                          "px-2 py-1 rounded-md cursor-pointer",
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
            </div>
            <div className="border-t border-gray-200 my-4" />
            <div className="space-y-4">
              {Object.entries(inputConfigs).map(([key, config], idx) => (
                <div key={key} className="space-y-1">
                  <div className="flex items-center space-x-4">
                    <label className="w-48 text-sm font-medium">
                      <Latex math={config.name} />
                    </label>

                    {config.unit === "bool" ? (
                      <Checkbox
                        checked={inputs[key] as boolean}
                        onCheckedChange={(checked) =>
                          handleInputChange(key, checked)
                        }
                      />
                    ) : (
                      <Input
                        type="number"
                        value={inputs[key] as number}
                        onClick={() => setSelectedInput(key)}
                        onChange={(e) => handleInputChange(key, e.target.value)}
                        className={cn(
                          "w-20 border-2 focus:border-transparent",
                          selectedInput === key && "border-primary",
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
                  {inputErrors[key] && (
                    <p className="text-sm text-red-500 ml-48">
                      {inputErrors[key]}
                    </p>
                  )}
                </div>
              ))}
              <div className="flex items-center gap-2 space-y-0 sm:flex-row">
                <Button onClick={handlePublish}>Create Template</Button>
                <AlertDialog open={alertBoxOpen} onOpenChange={setAlertBoxOpen}>
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
                              This message will close in {countdown} seconds...
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
            </div>
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
        <DataTable<Template, any>
          columns={columns}
          data={templateCache}
          onDelete={handleDelete}
        />
      </div>
    </div>
  );
}
