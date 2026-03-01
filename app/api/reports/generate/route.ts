import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { fetchGAMetrics } from "@/lib/ga/client";
import { fetchMetaMetrics } from "@/lib/meta/client";
import { generateNarrative } from "@/lib/ai/narrativeGenerator";
import { generateReportPDF } from "@/lib/pdf/reportGenerator";
import { sendReport } from "@/lib/email/sender";
import { getLastMonthRange } from "@/lib/utils";
import type { ReportData } from "@/lib/types";

/**
 * POST /api/reports/generate
 * Manual on-demand report generation for a specific client
 * Requires authentication
 */
export async function POST(request: Request) {
    const session = await auth();
    if (!session?.user?.id) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    const { clientId } = body;

    if (!clientId) {
        return NextResponse.json({ error: "clientId is required" }, { status: 400 });
    }

    // Verify the client belongs to this user's agency
    const client = await prisma.client.findFirst({
        where: {
            id: clientId,
            agency: { userId: session.user.id },
        },
        include: {
            agency: true,
        },
    });

    if (!client) {
        return NextResponse.json({ error: "Client not found" }, { status: 404 });
    }

    const { startDate, endDate, month, year } = getLastMonthRange();

    try {
        // Create report record
        const report = await prisma.report.create({
            data: { clientId: client.id, month, year, status: "generating" },
        });

        // Fetch metrics
        const [gaMetrics, metaMetrics] = await Promise.all([
            client.gaPropertyId
                ? fetchGAMetrics(client.id, client.gaPropertyId, startDate, endDate)
                : Promise.resolve({
                    sessions: 0, users: 0, newUsers: 0, bounceRate: 0,
                    avgSessionDuration: 0, topChannels: [], topPages: [],
                    conversions: 0, conversionRate: 0, weekByWeekTrend: [],
                }),
            client.metaAdAccountId
                ? fetchMetaMetrics(client.id, client.metaAdAccountId, startDate, endDate)
                : Promise.resolve({
                    spend: 0, impressions: 0, reach: 0, clicks: 0,
                    ctr: 0, cpc: 0, cpm: 0, roas: 0,
                    topCampaigns: [], weekByWeekSpend: [],
                }),
        ]);

        // Generate narrative
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

        // Generate PDF
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

        // Update report
        await prisma.report.update({
            where: { id: report.id },
            data: { status: "sent", pdfUrl, sentAt: new Date() },
        });

        return NextResponse.json({
            success: true,
            reportId: report.id,
            pdfUrl,
            month,
            year,
        });
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        console.error(`Manual report generation failed for ${client.name}:`, errorMessage);

        return NextResponse.json(
            { error: "Report generation failed", details: errorMessage },
            { status: 500 }
        );
    }
}
