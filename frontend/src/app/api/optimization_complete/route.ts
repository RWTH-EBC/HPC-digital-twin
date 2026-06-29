export const dynamic = "force-dynamic";

import { NextResponse } from "next/server";
import {
  getCache,
  saveCache,
  broadcastCacheUpdate,
  broadcastOptimizationResult,
  broadcastOptimizationProgress,
  getSSEClients,
  addToCache,
} from "@/lib/cache-utils";

/**
 * Handles SSE for optimization updates and
 * POST notifications from backend optimization process.
 */

// GET endpoint — used by frontend to listen via SSE
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const sse = searchParams.get("sse");

  if (sse === "true") {
    const sseClients = getSSEClients();
    const stream = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder();
        sseClients.add(controller);

        console.log(
          `[SSE] Optimization client connected (${sseClients.size} total)`
        );

        // Send initial message
        const initialMessage = `data: ${JSON.stringify({
          type: "connected",
          message: "SSE connection established for optimization updates",
        })}\n\n`;
        controller.enqueue(encoder.encode(initialMessage));

        // Send keepalive every 30 seconds
        const keepAlive = setInterval(() => {
          try {
            controller.enqueue(encoder.encode(": keepalive\n\n"));
          } catch (err) {
            console.error("SSE keepalive error:", err);
            clearInterval(keepAlive);
            sseClients.delete(controller);
          }
        }, 30000);

        // Cleanup on disconnect
        req.signal.addEventListener("abort", () => {
          console.log("❌ [SSE] Optimization client disconnected");
          clearInterval(keepAlive);
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

  // Regular GET (non-SSE)
  return NextResponse.json({
    success: true,
    scenarioCache: getCache(),
  });
}

// POST endpoint — backend sends optimization results here
export async function POST(req: Request) {
  try {
    const body = await req.json();
    console.log("Received optimization update:", body);

    // Handle progress updates
    if (body.type === "progress") {
      broadcastOptimizationProgress({
        progress: body.progress,
        remainingTime: body.remainingTime,
      });
      return NextResponse.json({ success: true, message: "Progress broadcasted" });
    }

    if (!body || !body.optimized_values) {
      return NextResponse.json(
        {
          success: false,
          error: "Invalid payload. Expected 'optimized_values' field or type='progress'.",
        },
        { status: 400 }
      );
    }

    // Example expected payload:
    // {
    //   "templateName": "Scenario_A",
    //   "optimized_values": { "temperature": 24.5, "pressure": 1.2, ... },
    //   "kpis": { "energy": 12.3 }
    // }
    const newTemplate = {
      templateName: body.templateName,
      scenario_settings: body.optimized_values,
      kpis: body.kpis || {},
    };

    // Save in cache
    addToCache(newTemplate);
    saveCache(getCache());

    // Broadcast optimization result to SSE clients
    broadcastOptimizationResult(newTemplate);

    console.log("✅ Optimization result broadcast to SSE clients");

    return NextResponse.json({
      success: true,
      message: "Optimization result processed successfully",
      optimizedTemplate: newTemplate,
    });
  } catch (error) {
    console.error("Error in optimization_complete POST:", error);
    return NextResponse.json(
      {
        success: false,
        error: (error as Error).message,
      },
      { status: 500 }
    );
  }
}
