import React from 'react';
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import Latex from "@matejmazur/react-katex";

interface InfoTooltipProps {
  showHints?: boolean;
  name: string;
  hint: string;
}

export function InfoTooltip({ showHints = true, name, hint }: InfoTooltipProps) {
  if (!showHints) return null;

  return (
    <Tooltip>
      <TooltipTrigger>
        <div className="absolute -right-2 -top-2 w-4 h-4 bg-primary text-xs text-white rounded-full flex items-center justify-center z-20">
          i
        </div>
      </TooltipTrigger>
      <TooltipContent>
        <p className="max-w-xs">
          <Latex math={name} />:
          <br />
          {hint}
        </p>
      </TooltipContent>
    </Tooltip>
  );
}