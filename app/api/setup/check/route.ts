import { NextResponse } from "next/server";

const ENV_VARS = [
    "DATABASE_URL",
    "NEXTAUTH_SECRET",
    "NEXTAUTH_URL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "META_APP_ID",
    "META_APP_SECRET",
    "GEMINI_API_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_STARTER_PRICE_ID",
    "STRIPE_GROWTH_PRICE_ID",
    "STRIPE_AGENCY_PRICE_ID",
    "RESEND_API_KEY",
    "CRON_SECRET",
];

export async function GET() {
    // Only allow in development
    if (process.env.NODE_ENV === "production") {
        return NextResponse.json({ error: "Not available in production" }, { status: 403 });
    }

    const results: Record<string, boolean> = {};

    for (const envVar of ENV_VARS) {
        const value = process.env[envVar];
        results[envVar] = !!value && value !== "" && !value.startsWith("your-");
    }

    return NextResponse.json({ results });
}
