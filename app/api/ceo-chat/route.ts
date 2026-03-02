import { NextResponse } from "next/server";
import { chatWithCEO } from "@/agents/ceo/orchestrator";

/**
 * CEO Chat API — Interactive conversation between Marcos and Alex Rivera
 */
export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { message, history } = body as {
            message: string;
            history: Array<{ role: "user" | "ceo"; message: string }>;
        };

        if (!message || typeof message !== "string") {
            return NextResponse.json({ error: "Message is required" }, { status: 400 });
        }

        const response = await chatWithCEO(message, history || []);

        return NextResponse.json({ success: true, response });
    } catch (error: unknown) {
        const message = error instanceof Error ? error.message : "Unknown error";
        console.error("[CEO CHAT] Error:", message);
        return NextResponse.json({ success: false, error: message }, { status: 500 });
    }
}
