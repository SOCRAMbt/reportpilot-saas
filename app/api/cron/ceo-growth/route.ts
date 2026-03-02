import { NextResponse } from "next/server";
import { runGrowthHeartbeat } from "@/agents/ceo/orchestrator";

/**
 * CEO Growth Heartbeat — Runs every 24 hours
 * Analyzes user behavior, sends onboarding/retention/upsell emails.
 * Alex Rivera thinks about each agency and personalizes outreach.
 */
export async function POST(req: Request) {
    const authHeader = req.headers.get("Authorization");
    if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
        const result = await runGrowthHeartbeat();
        return NextResponse.json({
            success: true,
            layer: "growth",
            ...result,
        });
    } catch (error: unknown) {
        const message = error instanceof Error ? error.message : "Unknown error";
        console.error("[CEO GROWTH] Heartbeat failed:", message);
        return NextResponse.json({ success: false, error: message }, { status: 500 });
    }
}
