/**
 * InfrastructurePlan Component
 *
 * A visual interface for configuring infrastructure settings through an interactive map.
 * The component overlays input fields and checkboxes on top of an infrastructure diagram.
 *
 * Configuration:
 * - Infrastructure layouts are defined in: src/config/infrastructure/
 * - Each environment (itc, zih, etc.) has its own configuration
 * - Image path, positions, and hints are loaded based on DEPLOYMENT_ENV
 *
 * Image Requirements:
 * - Place infrastructure diagram images in: /public/images/
 * - Recommended format: PNG with transparent background
 * - Minimum resolution: 1200px width for good scaling
 */

import * as React from "react";
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import { Input } from "@/components/ui/input";
import { useForm } from "react-hook-form";
import { Checkbox } from "@/components/ui/checkbox";
import { Card } from "@/components/ui/card";
import { ArrowDownLeft } from "lucide-react";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { cn } from "@/lib/utils";
import Latex from "@matejmazur/react-katex";
import { infrastructureConfig } from "@/config/infrastructure-config";

interface InfrastructurePlanProps {
  inputs?: {
    [key: string]: number | boolean;
  };
  selectedInput?: string | null;
  onInputSelect?: (key: string) => void;
  inputErrors?: { [key: string]: string };
  onInputChange?: (key: string, value: string | boolean) => void;
  configs?: { [key: string]: any };
}

interface InfrastructureForm {
  inputs: string[];
  checkboxes: boolean[];
}

const onSubmit = (data: InfrastructureForm) => {
  console.log("Form data:", data);
};

export function InfrastructurePlan({
  inputs = {},
  configs = {},
  onInputSelect = () => {},
  inputErrors = {},
  onInputChange,
  selectedInput,
}: InfrastructurePlanProps) {
  const { register, handleSubmit } = useForm<InfrastructureForm>();
  const [showHints, setShowHints] = React.useState(true);
  const [scale, setScale] = React.useState(1);
  const [imageSize, setImageSize] = React.useState({ width: 0, height: 0 });
  const imageRef = React.useRef<HTMLImageElement>(null);

  React.useEffect(() => {
    const updateImageSize = () => {
      if (imageRef.current) {
        setImageSize({
          width: imageRef.current.offsetWidth,
          height: imageRef.current.offsetHeight,
        });
      }
    };

    updateImageSize();
    window.addEventListener("resize", updateImageSize);
    return () => window.removeEventListener("resize", updateImageSize);
  }, []);

  return (
    <div className="2xl:col-span-5 md:col-span-7 h-full flex-grow">
      <Card className="rounded-md border h-[970px] overflow-auto">
        <TransformWrapper
          panning={{ excluded: ["input", "Checkbox"] }}
          onTransformed={(e) => {
            setScale(e.state.scale);
          }}
        >
          <TransformComponent>
            <div className="relative w-full">
              <img
                ref={imageRef}
                src={infrastructureConfig.imagePath}
                alt="Infrastructure Plan"
                className="w-full h-auto"
                onLoad={(e) => {
                  setImageSize({
                    width: e.currentTarget.offsetWidth,
                    height: e.currentTarget.offsetHeight,
                  });
                }}
              />
              <div className="absolute inset-0">
                {Object.entries(inputs).map(([key, value]) =>
                  infrastructureConfig.positions[key] ? (
                    <div
                      key={key}
                      className="absolute"
                      style={{
                        left: `${
                          (parseFloat(
                            infrastructureConfig.positions[key].left,
                          ) *
                            imageSize.width) /
                          100
                        }px`,
                        top: `${
                          (parseFloat(infrastructureConfig.positions[key].top) *
                            imageSize.height) /
                          100
                        }px`,
                        transform: `scale(${1 / scale})`,
                        transformOrigin: "top left",
                      }}
                      onClick={() => onInputSelect(key)}
                    >
                      {typeof value === "boolean" ? (
                        <div className="flex items-center gap-2 ">
                          <div className="relative">
                            <Checkbox
                              checked={value}
                              onCheckedChange={(checked) =>
                                onInputChange?.(key, checked)
                              }
                            />
                          </div>
                          {showHints && (
                            <InfoTooltip
                              showHints={showHints}
                              name={configs?.[key]?.name || key}
                              hint={
                                infrastructureConfig.hints[key] ||
                                "No hint available"
                              }
                            />
                          )}
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 ">
                          <div className="relative">
                            <div className="flex items-center relative">
                              <Input
                                type="number"
                                value={value}
                                onChange={(e) =>
                                  onInputChange?.(key, e.target.value)
                                }
                                className={cn(
                                  "focus:border-transparent",
                                  "w-20 border-2 bg-transparent border-transparent focus-visible:bg-white text-black",
                                  "[&::-webkit-inner-spin-button]:appearance-none",
                                  selectedInput === key && "border-primary",
                                )}
                                min={
                                  configs &&
                                  configs[key] &&
                                  "min_value" in configs[key]
                                    ? configs[key].min_value
                                    : undefined
                                }
                                max={
                                  configs &&
                                  configs[key] &&
                                  "max_value" in configs[key]
                                    ? configs[key].max_value
                                    : undefined
                                }
                              />
                              {configs?.[key]?.unit && (
                                <span className="absolute right-5 text-black text-base">
                                  {configs[key].unit}
                                </span>
                              )}
                            </div>
                            <ArrowDownLeft
                              color="#036568"
                              className={cn(
                                "absolute w-6 h-6 -left-2 -top-2 -translate-y-1/1 rotate-90",
                              )}
                            />
                          </div>
                          {showHints && (
                            <InfoTooltip
                              showHints={showHints}
                              name={configs?.[key]?.name || key}
                              hint={
                                infrastructureConfig.hints[key] ||
                                "No hint available"
                              }
                            />
                          )}
                        </div>
                      )}
                      {inputErrors[key] && (
                        <p className="text-sm text-red-500 mt-1">
                          {inputErrors[key]}
                        </p>
                      )}
                    </div>
                  ) : null,
                )}
              </div>
            </div>
          </TransformComponent>
        </TransformWrapper>
      </Card>
    </div>
  );
}
