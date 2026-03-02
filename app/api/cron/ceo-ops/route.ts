import { NextResponse } from "next/server";
import { runOpsHeartbeat } from "@/agents/ceo/orchestrator";

/**
 * CEO Operations Heartbeat — Runs every 1 hour
 * Checks for errors, stuck reports, and system issues.
 * Alex Rivera decides what to fix, pause, or escalate.
 */
export async function POST(req: Request) {
    const authHeader = req.headers.get("Authorization");
    if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
        const result = await runOpsHeartbeat();
        return NextResponse.json({
            success: true,
            layer: "operations",
            ...result,
        });
    } catch (error: unknown) {
        const message = error instanceof Error ? error.message : "Unknown error";
        console.error("[CEO OPS] Heartbeat failed:", message);
        return NextResponse.json({ success: false, error: message }, { status: 500 });
    }
}
