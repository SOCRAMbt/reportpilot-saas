import { NextResponse } from "next/server";
import { runMarketingHeartbeat } from "@/agents/ceo/orchestrator";

/**
 * CEO Marketing Heartbeat — Runs every 48 hours
 * Generates LinkedIn posts, X threads, newsletter drafts,
 * and updates benchmark data from anonymized platform metrics.
 */
export async function POST(req: Request) {
    const authHeader = req.headers.get("Authorization");
    if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
        const result = await runMarketingHeartbeat();
        return NextResponse.json({
            success: true,
            layer: "marketing",
            ...result,
        });
    } catch (error: unknown) {
        const message = error instanceof Error ? error.message : "Unknown error";
        console.error("[CEO MARKETING] Heartbeat failed:", message);
        return NextResponse.json({ success: false, error: message }, { status: 500 });
    }
}
