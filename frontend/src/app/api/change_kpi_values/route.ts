export const dynamic = "force-dynamic";

import { NextResponse } from "next/server";
import { getCache, saveCache, broadcastCacheUpdate } from "@/lib/cache-utils";
import { cache } from "react";

// POST endpoint to update KPI values
export async function POST(req: Request) {
  try {
    const body = await req.json();
    console.log("Received KPI update request:", body);

    // Validate input format
    // Expected format: {"TemplateName": {"kpi_key": value, ...}}
    if (!body || typeof body !== "object") {
      return NextResponse.json(
        {
          success: false,
          error: "Invalid request format. Expected object with template names as keys.",
        },
        { status: 400 }
      );
    }

    const updatedTemplates: string[] = [];
    const notFoundTemplates: string[] = [];

    const cache = getCache();
    // Process each template update
    for (const [templateName, kpiUpdates] of Object.entries(body)) {
      console.log(`Updating template: ${templateName}`, kpiUpdates);

      // Find the template in the cache
      const templateIndex = cache.findIndex(
        (template: any) => template.templateName === templateName
      );

      if (templateIndex === -1) {
        console.warn(`Template not found: ${templateName}`);
        notFoundTemplates.push(templateName);
        continue;
      }

      // Update KPI values in the template
      const template = cache[templateIndex];
      
      if (!template.scenario_settings) {
        template.scenario_settings = {};
      }

      // Merge the KPI updates into kpis
      if (!template.kpis) {
        template.kpis = {};
      }
      Object.assign(template.kpis, kpiUpdates);

      // Update the template in cache
      cache[templateIndex] = template;
      updatedTemplates.push(templateName);

      console.log(`Updated template ${templateName}:`, template.scenario_settings);
    }
    console.log("Cache after updates:", cache);

    // Save the updated cache
    saveCache(getCache());

    // Broadcast the update to all SSE clients
    broadcastCacheUpdate(getCache());

    return NextResponse.json({
      success: true,
      message: "KPI values updated successfully",
      updatedTemplates,
      notFoundTemplates: notFoundTemplates.length > 0 ? notFoundTemplates : undefined,
      scenarioCache: getCache(),
    });
  } catch (error) {
    console.error("Error updating KPI values:", error);
    return NextResponse.json(
      {
        success: false,
        error: (error as Error).message,
      },
      { status: 500 }
    );
  }
}
