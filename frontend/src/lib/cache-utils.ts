/**
 * Shared cache utilities for SSE and cache management
 * Used by both /api/cache-handling and /api/change_kpi_values
 */

import fs from "fs";
import path from "path";

// Global type declarations
declare global {
  var scenarioCache: any[];
  var sseClients: Set<ReadableStreamDefaultController>;
}

// File paths for cache
const CACHE_DIR = path.join(process.cwd(), ".cache");
const SCENARIO_CACHE_FILE = path.join(CACHE_DIR, "scenarioCache.json");
const OPTIMIZATION_CACHE_FILE = path.join(
  CACHE_DIR,
  "optimizationSettings.json"
);

// Initialize cache directory
if (!fs.existsSync(CACHE_DIR)) {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
}

// Initialize SSE clients set
if (!global.sseClients) {
  global.sseClients = new Set();
}

/**
 * Load cache from disk
 */
const loadCache = (): any[] => {
  try {
    if (fs.existsSync(SCENARIO_CACHE_FILE)) {
      const data = fs.readFileSync(SCENARIO_CACHE_FILE, "utf-8");
      return JSON.parse(data);
    }
  } catch (error) {
    console.error(`Error loading cache:`, error);
  }
  return [];
};

/** Load optimization cache from disk
 */
const loadOptimizationCache = (): any[] => {
  try {
    if (fs.existsSync(OPTIMIZATION_CACHE_FILE)) {
      const data = fs.readFileSync(OPTIMIZATION_CACHE_FILE, "utf-8");
      return JSON.parse(data);
    }
  } catch (error) {
    console.error("Error loading optimization cache:", error);
  }
  return [];
};

// Initialize global cache if not already loaded
if (!global.scenarioCache) {
  global.scenarioCache = loadCache();
}

/**
 * Save cache to disk and update global reference
 */
export const saveCache = (data: any[]) => {
  try {
    fs.writeFileSync(SCENARIO_CACHE_FILE, JSON.stringify(data, null, 2));
    global.scenarioCache = data;
  } catch (error) {
    console.error(`Error saving cache:`, error);
  }
};

/** Save optimization cache to disk
 */
const saveOptimizationCache = (data: any[]) => {
  try {
    fs.writeFileSync(OPTIMIZATION_CACHE_FILE, JSON.stringify(data, null, 2));
  } catch (error) {
    console.error("Error saving optimization cache:", error);
  }
};

/** Delete a single optimization setting
 */
export const deleteSingleOptimizationSetting = (templateName: string) => {
  const cache = loadOptimizationCache();
  const filtered = cache.filter(
    (optimizationSavedSettings: any) =>
      optimizationSavedSettings.opt_name !== templateName
  );
  saveOptimizationCache(filtered);
};

/** Clear all optimization settings
 */
export const clearOptimizationCache = () => {
  saveOptimizationCache([]);
};

/**
 * Broadcast cache update to all connected SSE clients
 */
export const broadcastCacheUpdate = (updatedCache: any[]) => {
  const message = `data: ${JSON.stringify({
    type: "cache_update",
    scenarioCache: updatedCache,
  })}\n\n`;

  global.sseClients.forEach((controller) => {
    try {
      controller.enqueue(new TextEncoder().encode(message));
    } catch (error) {
      console.error("Error broadcasting to client:", error);
      global.sseClients.delete(controller);
    }
  });
};
/**
 * Broadcast optimization result to all connected SSE clients
 */

export const broadcastOptimizationResult = (optimizedTemplate: any) => {
  const message = `data: ${JSON.stringify({
    type: "optimizer_result",
    optimizedTemplate,
  })}\n\n`;

  global.sseClients.forEach((controller) => {
    try {
      controller.enqueue(new TextEncoder().encode(message));
    } catch (error) {
      console.error("Error broadcasting optimization result:", error);
      global.sseClients.delete(controller);
    }
  });
};

/**
 * Broadcast optimization progress to all connected SSE clients
 */
export const broadcastOptimizationProgress = (progressData: any) => {
  const message = `data: ${JSON.stringify({
    type: "progress",
    ...progressData,
  })}\n\n`;

  global.sseClients.forEach((controller) => {
    try {
      controller.enqueue(new TextEncoder().encode(message));
    } catch (error) {
      console.error("Error broadcasting optimization progress:", error);
      global.sseClients.delete(controller);
    }
  });
};

/**
 * Add a template to cache with size limit, overwriting if name already exists
 */
export const addToCache = (template: any, maxSize: number = 100) => {
  const index = global.scenarioCache.findIndex(
    (t: any) => t.templateName === template.templateName
  );

  if (index !== -1) {
    // Overwrite existing entry
    global.scenarioCache[index] = template;
    console.log("Updated existing template in cache:", template.templateName);
  } else {
    // No existing entry → append
    if (global.scenarioCache.length >= maxSize) {
      global.scenarioCache.shift();
    }
    global.scenarioCache.push(template);
    console.log("Added new template to cache:", template.templateName);
  }

  saveCache(global.scenarioCache);
};

/**
 * Get the global cache reference
 */
export const getCache = () => global.scenarioCache;

/**
 * Get SSE clients set
 */
export const getSSEClients = () => global.sseClients;
