import { inngest } from "./client";
import { prisma } from "@/lib/prisma";
import { fetchGAMetrics } from "@/lib/ga/client";
import { fetchMetaMetrics } from "@/lib/meta/client";
import { generateNarrative } from "@/lib/ai/narrativeGenerator";
import { generateReportPDF } from "@/lib/pdf/reportGenerator";
import { sendReport } from "@/lib/email/sender";
import { getLastMonthRange } from "@/lib/utils";
import type { ReportData } from "@/lib/types";

export const scheduledReportTrigger = inngest.createFunction(
    { id: "scheduled-report-trigger" },
    { cron: "0 8 1 * *" }, // Run at 8:00 AM on the 1st of every month
    async ({ step }) => {
        const { startDate, endDate, month, year } = getLastMonthRange();

        const clients = await step.run("fetch-active-clients", async () => {
            return prisma.client.findMany({
                where: { active: true },
            });
        });

        if (clients.length === 0) {
            return { message: "No active clients found" };
        }

        const events = clients.map((client) => ({
            name: "report.generate",
            data: {
                clientId: client.id,
                startDate,
                endDate,
                month,
                year,
            },
        }));

        await step.sendEvent("dispatch-client-reports", events);

        return { dispatched: events.length };
    }
);

export const generateClientReport = inngest.createFunction(
    {
        id: "generate-client-report",
        concurrency: {
            limit: 5, // Process max 5 reports at a time to avoid rate limits
        },
        retries: 3 // Retry up to 3 times on failure
    },
    { event: "report.generate" },
    async ({ event, step }) => {
        const { clientId, startDate, endDate, month, year } = event.data;

        const client = await step.run("fetch-client-details", async () => {
            return prisma.client.findUnique({
                where: { id: clientId },
                include: {
                    agency: {
                        include: { user: true },
                    },
                    integrations: true,
                },
            });
        });

        if (!client) {
            throw new Error(`Client not found: ${clientId}`);
        }

        // Check if report already exists and is sent
        const existingReport = await step.run("check-existing-report", async () => {
            return prisma.report.findFirst({
                where: { clientId, month, year },
            });
        });

        if (existingReport?.status === "sent") {
            return { message: "Report already sent for this month" };
        }

        // Create or update status to generating
        const reportId = await step.run("create-report-record", async () => {
            const r = existingReport || await prisma.report.create({
                data: { clientId, month, year, status: "generating" },
            });
            if (existingReport) {
                await prisma.report.update({
                    where: { id: existingReport.id },
                    data: { status: "generating" },
                });
            }
            return r.id;
        });

        try {
            // Fetch analytics data
            const gaMetrics = await step.run("fetch-ga-metrics", async () => {
                return client.gaPropertyId
                    ? fetchGAMetrics(client.id, client.gaPropertyId, startDate, endDate)
                    : getDefaultGAMetrics();
            });

            const metaMetrics = await step.run("fetch-meta-metrics", async () => {
                return client.metaAdAccountId
                    ? fetchMetaMetrics(client.id, client.metaAdAccountId, startDate, endDate)
                    : getDefaultMetaMetrics();
            });

            // Generate AI Narrative
            const narrative = await step.run("generate-ai-narrative", async () => {
                return generateNarrative(gaMetrics, metaMetrics, client.name);
            });

            // Make sure we pass the correct data format
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

            // Combine PDF generation and email sending to avoid moving large Buffers between steps
            const pdfUrl = await step.run("generate-pdf-and-send-email", async () => {
                // Generate PDF
                const { buffer: pdfBuffer, url } = await generateReportPDF(reportData);

                // Send Email
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

                return url;
            });

            // Update record as sent
            await step.run("mark-report-sent", async () => {
                await prisma.report.update({
                    where: { id: reportId },
                    data: {
                        status: "sent",
                        pdfUrl,
                        sentAt: new Date(),
                    },
                });
            });

            return { success: true, client: client.name };
        } catch (error) {
            // Unhandled errors will be retried automatically by Inngest.
            // On the final failure, Inngest will mark it as failed. 
            // We want to mark it as failed in DB too.
            await step.run("mark-report-failed", async () => {
                await prisma.report.update({
                    where: { id: reportId },
                    data: { status: "failed" },
                });
            });

            throw error;
        }
    }
);

function getDefaultGAMetrics(): any {
    return {
        sessions: 0, users: 0, newUsers: 0,
        bounceRate: 0, avgSessionDuration: 0,
        topChannels: [], topPages: [],
        conversions: 0, conversionRate: 0,
        weekByWeekTrend: [],
    };
}

function getDefaultMetaMetrics(): any {
    return {
        spend: 0, impressions: 0, reach: 0, clicks: 0,
        ctr: 0, cpc: 0, cpm: 0, roas: 0,
        topCampaigns: [], weekByWeekSpend: [],
    };
}
