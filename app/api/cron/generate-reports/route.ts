import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { fetchGAMetrics } from "@/lib/ga/client";
import { fetchMetaMetrics } from "@/lib/meta/client";
import { generateNarrative } from "@/lib/ai/narrativeGenerator";
import { generateReportPDF } from "@/lib/pdf/reportGenerator";
import { sendReport } from "@/lib/email/sender";
import { getLastMonthRange } from "@/lib/utils";
import type { GenerationResult, GenerationSummary, ReportData } from "@/lib/types";

/**
 * GET /api/cron/generate-reports
 * Monthly cron handler — generates reports for all active clients
 * Protected by CRON_SECRET header check
 * Triggered via Vercel Cron: "0 8 1 * *"
 */
export async function GET(request: Request) {
    // Verify cron secret
    const authHeader = request.headers.get("authorization");
    if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { startDate, endDate, month, year } = getLastMonthRange();

    // Get all active clients with their agency info and integrations
    const clients = await prisma.client.findMany({
        where: { active: true },
        include: {
            agency: {
                include: { user: true },
            },
            integrations: true,
        },
    });

    if (clients.length === 0) {
        return NextResponse.json({ success: 0, failed: 0, errors: [], message: "No active clients found" });
    }

    // Process all clients in parallel
    const results = await Promise.allSettled(
        clients.map((client) => generateClientReport(client, startDate, endDate, month, year))
    );

    // Build summary
    const summary: GenerationSummary = {
        success: 0,
        failed: 0,
        errors: [],
    };

    results.forEach((result, index) => {
        if (result.status === "fulfilled" && result.value.success) {
            summary.success++;
        } else {
            summary.failed++;
            const error: GenerationResult = {
                clientId: clients[index].id,
                clientName: clients[index].name,
                success: false,
                error: result.status === "rejected"
                    ? result.reason?.message || "Unknown error"
                    : result.value.error,
            };
            summary.errors.push(error);
        }
    });

    return NextResponse.json(summary);
}

/**
 * Generates a complete report for a single client
 */
async function generateClientReport(
    client: {
        id: string;
        name: string;
        email: string;
        gaPropertyId: string | null;
        metaAdAccountId: string | null;
        agency: {
            name: string;
            brandColor: string;
            logoUrl: string | null;
            user: { id: string };
        };
    },
    startDate: string,
    endDate: string,
    month: number,
    year: number
): Promise<GenerationResult> {
    try {
        // Check if report already exists for this month
        const existingReport = await prisma.report.findFirst({
            where: { clientId: client.id, month, year },
        });

        if (existingReport && existingReport.status === "sent") {
            return { clientId: client.id, clientName: client.name, success: true };
        }

        // Create or get pending report record
        const report = existingReport || await prisma.report.create({
            data: { clientId: client.id, month, year, status: "generating" },
        });

        // Update status to generating
        await prisma.report.update({
            where: { id: report.id },
            data: { status: "generating" },
        });

        // Fetch data from both platforms
        const [gaMetrics, metaMetrics] = await Promise.all([
            client.gaPropertyId
                ? fetchGAMetrics(client.id, client.gaPropertyId, startDate, endDate)
                : getDefaultGAMetrics(),
            client.metaAdAccountId
                ? fetchMetaMetrics(client.id, client.metaAdAccountId, startDate, endDate)
                : getDefaultMetaMetrics(),
        ]);

        // Generate AI narrative
        const narrative = await generateNarrative(gaMetrics, metaMetrics, client.name);

        // Build report data
        const reportData: ReportData = {
            clientName: client.name,
            clientEmail: client.email,
            agencyName: client.agency.name,
            agencyLogoUrl: client.agency.logoUrl,
            agencyBrandColor: client.agency.brandColor,
            month,
            year,
            gaMetrics,
            metaMetrics,
            narrative,
        };

        // Generate PDF and upload
        const { buffer: pdfBuffer, url: pdfUrl } = await generateReportPDF(reportData);

        // Send email
        await sendReport({
            clientEmail: client.email,
            clientName: client.name,
            agencyName: client.agency.name,
            agencyLogoUrl: client.agency.logoUrl,
            agencyBrandColor: client.agency.brandColor,
            executiveSummary: narrative.executiveSummary,
            pdfBuffer,
            month,
            year,
        });

        // Update report record
        await prisma.report.update({
            where: { id: report.id },
            data: {
                status: "sent",
                pdfUrl,
                sentAt: new Date(),
            },
        });

        return { clientId: client.id, clientName: client.name, success: true };
    } catch (error) {
        // Mark report as failed
        const existingReport = await prisma.report.findFirst({
            where: { clientId: client.id, month, year },
        });
        if (existingReport) {
            await prisma.report.update({
                where: { id: existingReport.id },
                data: { status: "failed" },
            });
        }

        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        console.error(`Failed to generate report for ${client.name}:`, errorMessage);

        return {
            clientId: client.id,
            clientName: client.name,
            success: false,
            error: errorMessage,
        };
    }
}

// Default metrics when a platform is not connected
function getDefaultGAMetrics() {
    return {
        sessions: 0, users: 0, newUsers: 0,
        bounceRate: 0, avgSessionDuration: 0,
        topChannels: [], topPages: [],
        conversions: 0, conversionRate: 0,
        weekByWeekTrend: [],
    };
}

function getDefaultMetaMetrics() {
    return {
        spend: 0, impressions: 0, reach: 0, clicks: 0,
        ctr: 0, cpc: 0, cpm: 0, roas: 0,
        topCampaigns: [], weekByWeekSpend: [],
    };
}
