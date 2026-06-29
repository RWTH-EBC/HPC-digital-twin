export const dynamic = "force-dynamic";

import { NextResponse } from "next/server";
import {
  getCache,
  getSSEClients,
  saveCache,
  broadcastCacheUpdate,
  addToCache,
  deleteSingleOptimizationSetting,
  clearOptimizationCache,
} from "@/lib/cache-utils";

// GET endpoint - primarily for SSE
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const sse = searchParams.get("sse");

  // SSE endpoint
  if (sse === "true") {
    const sseClients = getSSEClients();
    const stream = new ReadableStream({
      start(controller) {
        // Add client to the set
        sseClients.add(controller);
        console.log(`SSE client connected. Total clients: ${sseClients.size}`);

        // Send initial cache data
        const initialMessage = `data: ${JSON.stringify({
          type: "initial",
          scenarioCache: getCache(),
        })}\n\n`;
        controller.enqueue(new TextEncoder().encode(initialMessage));

        // Send keepalive every 30 seconds
        const keepAliveInterval = setInterval(() => {
          try {
            controller.enqueue(new TextEncoder().encode(": keepalive\n\n"));
          } catch (error) {
            console.error("Error sending keepalive:", error);
            clearInterval(keepAliveInterval);
            sseClients.delete(controller);
          }
        }, 30000);

        // Cleanup on close
        req.signal.addEventListener("abort", () => {
          console.log("SSE client disconnected");
          clearInterval(keepAliveInterval);
          sseClients.delete(controller);
          controller.close();
        });
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }

  // Regular GET endpoint for cache
  return NextResponse.json({
    success: true,
    scenarioCache: getCache(),
  });
}

// POST endpoint to publish messages
export async function POST(req: Request) {
  const body = await req.json();
  console.log("Received POST request:", body);

  try {
    const parsedMessage =
      typeof body.message === "string"
        ? JSON.parse(body.message)
        : body.message;

    // Validate the message format - handle both single object and array
    const validateTemplate = (template: any) => {
      if (!template.templateName || !template.scenario_settings) {
        return false;
      }
      return true;
    };

    // Check if parsedMessage is an array or single object
    if (Array.isArray(parsedMessage)) {
      // Validate each template in the array
      for (let i = 0; i < parsedMessage.length; i++) {
        if (!validateTemplate(parsedMessage[i])) {
          return NextResponse.json(
            {
              success: false,
              error: `Invalid message format at index ${i}. Required fields: templateName, scenario_settings`,
            },
            { status: 400 }
          );
        }
      }

      if (parsedMessage.length === 0) {
        return NextResponse.json(
          {
            success: false,
            error: "Empty array provided. At least one template is required.",
          },
          { status: 400 }
        );
      }
    } else {
      // Validate single object
      if (!validateTemplate(parsedMessage)) {
        return NextResponse.json(
          {
            success: false,
            error:
              "Invalid message format. Required fields: templateName, scenario_settings",
          },
          { status: 400 }
        );
      }
    }

    // Only add to cache, don't publish via MQTT
    console.log("Saving to cache without publishing to MQTT");

    if (Array.isArray(parsedMessage)) {
      // Add each template to cache
      parsedMessage.forEach((template) => addToCache(template));
    } else {
      // Add single template to cache
      addToCache(parsedMessage);
    }

    // Broadcast the update to all SSE clients
    broadcastCacheUpdate(getCache());

    return NextResponse.json({
      success: true,
      message: "Message(s) added to cache successfully",
      scenarioCache: getCache(), // Return the updated cache in the response
    });
  } catch (error) {
    console.error("Error in POST:", error);
    return NextResponse.json(
      {
        success: false,
        error: (error as Error).message,
      },
      { status: 500 }
    );
  }
}

// TODO: Direct Influx deletion, not in agent
// DELETE endpoint to remove scenarios
export async function DELETE(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const templateName = searchParams.get("templateName");

    if (templateName) {
      // Delete specific template
      console.log(`Deleting template: ${templateName}`);

      // Filter out the template from the cache
      const updatedCache = getCache().filter(
        (entry: any) => entry.templateName !== templateName
      );
      saveCache(updatedCache);

      // Also clear related optimization settings
      deleteSingleOptimizationSetting(templateName);

      // Broadcast the update to all SSE clients
      broadcastCacheUpdate(getCache());

      return NextResponse.json({
        success: true,
        message: `Deleted template: ${templateName}`,
        scenarioCache: getCache(),
      });
    } else {
      // Delete all templates
      saveCache([]);
      // Clear all optimization settings
      clearOptimizationCache();

      // Broadcast the update to all SSE clients
      broadcastCacheUpdate(getCache());

      return NextResponse.json({
        success: true,
        message: "All templates deleted",
        scenarioCache: getCache(),
      });
    }
  } catch (error) {
    console.error("Error in DELETE:", error);
    return NextResponse.json(
      {
        success: false,
        error: (error as Error).message,
      },
      { status: 500 }
    );
  }
}
