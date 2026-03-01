import { google } from "googleapis";
import { prisma } from "@/lib/prisma";
import type { GAMetrics, ChannelData, PageData, WeeklyTrend } from "@/lib/types";

const analyticsData = google.analyticsdata("v1beta");

async function getValidAccessToken(clientId: string): Promise<string> {
    const integration = await prisma.integration.findFirst({
        where: { clientId, type: "google_analytics" },
    });

    if (!integration) {
        throw new Error(`No Google Analytics integration found for client ${clientId}`);
    }

    if (integration.expiresAt && integration.expiresAt > new Date(Date.now() + 5 * 60 * 1000)) {
        return integration.accessToken;
    }

    if (!integration.refreshToken) {
        throw new Error("No refresh token available. Client needs to re-authenticate.");
    }

    const oauth2Client = new google.auth.OAuth2(
        process.env.GOOGLE_CLIENT_ID,
        process.env.GOOGLE_CLIENT_SECRET
    );
    oauth2Client.setCredentials({ refresh_token: integration.refreshToken });

    try {
        const { credentials } = await oauth2Client.refreshAccessToken();
        await prisma.integration.update({
            where: { id: integration.id },
            data: {
                accessToken: credentials.access_token!,
                expiresAt: credentials.expiry_date ? new Date(credentials.expiry_date) : null,
            },
        });
        return credentials.access_token!;
    } catch (error) {
        throw new Error(`Failed to refresh Google token: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
}

export async function fetchGAMetrics(
    clientId: string,
    propertyId: string,
    startDate: string,
    endDate: string
): Promise<GAMetrics> {
    const accessToken = await getValidAccessToken(clientId);
    const oauth2Client = new google.auth.OAuth2();
    oauth2Client.setCredentials({ access_token: accessToken });

    const property = `properties/${propertyId}`;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const runReport = (params: Record<string, unknown>) =>
        analyticsData.properties.runReport(params as any);

    const [coreMetrics, channelData, pageData, weeklyData] = await Promise.all([
        runReport({
            property,
            auth: oauth2Client,
            requestBody: {
                dateRanges: [{ startDate, endDate }],
                metrics: [
                    { name: "sessions" },
                    { name: "totalUsers" },
                    { name: "newUsers" },
                    { name: "bounceRate" },
                    { name: "averageSessionDuration" },
                    { name: "conversions" },
                ],
            },
        }),
        runReport({
            property,
            auth: oauth2Client,
            requestBody: {
                dateRanges: [{ startDate, endDate }],
                dimensions: [{ name: "sessionDefaultChannelGroup" }],
                metrics: [{ name: "sessions" }],
                orderBys: [{ metric: { metricName: "sessions" }, desc: true }],
                limit: 6,
            },
        }),
        runReport({
            property,
            auth: oauth2Client,
            requestBody: {
                dateRanges: [{ startDate, endDate }],
                dimensions: [{ name: "pagePath" }, { name: "pageTitle" }],
                metrics: [{ name: "screenPageViews" }],
                orderBys: [{ metric: { metricName: "screenPageViews" }, desc: true }],
                limit: 5,
            },
        }),
        runReport({
            property,
            auth: oauth2Client,
            requestBody: {
                dateRanges: [{ startDate, endDate }],
                dimensions: [{ name: "isoWeek" }],
                metrics: [{ name: "sessions" }],
                orderBys: [{ dimension: { dimensionName: "isoWeek" }, desc: false }],
            },
        }),
    ]);

    const coreRow = coreMetrics.data.rows?.[0]?.metricValues || [];
    const totalSessions = parseInt(coreRow[0]?.value || "0");

    const channels: ChannelData[] = (channelData.data.rows || []).map((row) => ({
        channel: row.dimensionValues?.[0]?.value || "Unknown",
        sessions: parseInt(row.metricValues?.[0]?.value || "0"),
        percentage: totalSessions > 0
            ? (parseInt(row.metricValues?.[0]?.value || "0") / totalSessions) * 100
            : 0,
    }));

    const pages: PageData[] = (pageData.data.rows || []).map((row) => ({
        pagePath: row.dimensionValues?.[0]?.value || "/",
        pageTitle: row.dimensionValues?.[1]?.value || "Sin titulo",
        pageviews: parseInt(row.metricValues?.[0]?.value || "0"),
    }));

    const weeklyTrend: WeeklyTrend[] = (weeklyData.data.rows || []).map((row) => ({
        week: `Semana ${row.dimensionValues?.[0]?.value || "?"}`,
        sessions: parseInt(row.metricValues?.[0]?.value || "0"),
    }));

    const conversions = parseInt(coreRow[5]?.value || "0");
    const conversionRate = totalSessions > 0 ? (conversions / totalSessions) * 100 : 0;

    return {
        sessions: totalSessions,
        users: parseInt(coreRow[1]?.value || "0"),
        newUsers: parseInt(coreRow[2]?.value || "0"),
        bounceRate: parseFloat(coreRow[3]?.value || "0") * 100,
        avgSessionDuration: parseFloat(coreRow[4]?.value || "0"),
        topChannels: channels,
        topPages: pages,
        conversions,
        conversionRate,
        weekByWeekTrend: weeklyTrend,
    };
}
