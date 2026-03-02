import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { createBenchmarkPageData } from "@/agents/ceo/tools";

/**
 * GET /api/benchmarks — Public benchmark data for lead magnet page
 */
export async function GET() {
    try {
        const data = await createBenchmarkPageData();
        return NextResponse.json({ success: true, ...data });
    } catch (error: unknown) {
        const message = error instanceof Error ? error.message : "Unknown error";
        return NextResponse.json({ success: false, error: message }, { status: 500 });
    }
}

/**
 * POST /api/benchmarks — Capture lead email from benchmark page
 */
export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { email, industry, country } = body as {
            email: string;
            industry?: string;
            country?: string;
        };

        if (!email || !email.includes("@")) {
            return NextResponse.json({ error: "Email válido requerido" }, { status: 400 });
        }

        await prisma.benchmarkLead.create({
            data: { email, industry: industry || null, country: country || null },
        });

        return NextResponse.json({
            success: true,
            message: "¡Gracias! Te enviaremos el reporte completo de benchmarks.",
        });
    } catch (error: unknown) {
        const message = error instanceof Error ? error.message : "Unknown error";
        return NextResponse.json({ success: false, error: message }, { status: 500 });
    }
}
