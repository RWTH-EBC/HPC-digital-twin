"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown } from "lucide-react";
import { Template } from "@/types";

export const columns: ColumnDef<Template, any>[] = [
  {
    accessorKey: "templateName",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Template Name
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      return (
        <div className="ml-4 text-left font-medium">
          {row.getValue("templateName")}
        </div>
      );
    },
    size: 200,
  },
  {
    accessorKey: "scenario_settings",
    header: "Template Settings",
    cell: ({ row }) => {
      const settings = row.original.scenario_settings;
      return (
        <div className="ml-4 text-left">
          {Object.entries(settings).map(([key, value]) => (
            <div key={key}>
              <span className="font-semibold">{key}:</span> {value.toString()}
            </div>
          ))}
        </div>
      );
    },
    size: 300,
  },
];
