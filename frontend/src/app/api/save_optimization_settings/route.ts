import { NextResponse } from "next/server";
import { readFile, writeFile, mkdir } from "fs/promises";
import path from "path";

const CACHE_DIR = path.join(process.cwd(), ".cache");
const FILE_PATH = path.join(CACHE_DIR, "optimizationSettings.json");

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const opt_name = searchParams.get("opt_name");

    const file = await readFile(FILE_PATH, "utf8");
    const arr = JSON.parse(file);

    if (!opt_name) {
      return NextResponse.json({ success: true, settingsArray: arr ?? [] });
    }

    const item =
      (arr || []).find((it: any) => it.opt_name === opt_name) ?? null;
    return NextResponse.json({ success: true, settings: item });
  } catch (err: any) {
    // If file not found, return empty
    if ((err as any).code === "ENOENT") {
      return NextResponse.json({ success: true, settings: null });
    }
    console.error("Error reading optimizationSettings.json:", err);
    return NextResponse.json(
      { success: false, error: err.message },
      { status: 500 }
    );
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const payload = body?.data ?? body;

    if (!payload || !payload.opt_name) {
      return NextResponse.json(
        { success: false, error: "Missing payload or payload.opt_name" },
        { status: 400 }
      );
    }

    await mkdir(CACHE_DIR, { recursive: true });

    // Load existing array (if file exists / valid)
    let arr: any[] = [];
    try {
      const file = await readFile(FILE_PATH, "utf8");
      arr = JSON.parse(file);
      if (!Array.isArray(arr)) arr = [];
    } catch (err) {
      // File missing or invalid -> start fresh
      arr = [];
    }

    // Find index by opt_name
    const idx = arr.findIndex((it) => it?.opt_name === payload.opt_name);

    if (idx >= 0) {
      // Overwrite existing entry
      arr[idx] = payload;
    } else {
      // Append new entry
      arr.push(payload);
    }

    // Save back
    await writeFile(FILE_PATH, JSON.stringify(arr, null, 2), "utf8");

    return NextResponse.json({ success: true, message: "Saved" });
  } catch (err: any) {
    console.error("Error saving optimizationSettings.json:", err);
    return NextResponse.json(
      { success: false, error: err.message ?? String(err) },
      { status: 500 }
    );
  }
}

// Partial update of existing entry by opt_name
export async function PATCH(req: Request) {
  try {
    const body = await req.json();

    const { opt_name, ...updates } = body;

    if (!opt_name) {
      return NextResponse.json(
        { success: false, error: "Missing opt_name" },
        { status: 400 }
      );
    }

    await mkdir(CACHE_DIR, { recursive: true });

    let arr: any[] = [];
    try {
      const file = await readFile(FILE_PATH, "utf8");
      arr = JSON.parse(file);
      if (!Array.isArray(arr)) arr = [];
    } catch {
      return NextResponse.json(
        { success: false, error: "No optimization settings found" },
        { status: 404 }
      );
    }

    const idx = arr.findIndex((it) => it?.opt_name === opt_name);

    if (idx < 0) {
      return NextResponse.json(
        { success: false, error: `opt_name '${opt_name}' not found` },
        { status: 404 }
      );
    }

    // Merge updates (partial overwrite)
    arr[idx] = {
      ...arr[idx],
      ...updates,
    };

    await writeFile(FILE_PATH, JSON.stringify(arr, null, 2), "utf8");

    return NextResponse.json({ success: true, message: "Updated" });
  } catch (err: any) {
    console.error("Error patching optimizationSettings.json:", err);
    return NextResponse.json(
      { success: false, error: err.message ?? String(err) },
      { status: 500 }
    );
  }
}
