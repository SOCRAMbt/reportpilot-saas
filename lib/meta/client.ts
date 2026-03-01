import { prisma } from "@/lib/prisma";
import type { MetaMetrics, CampaignData, WeeklySpend } from "@/lib/types";

const META_GRAPH_API = "https://graph.facebook.com/v19.0";

interface MetaApiResponse {
    data: Array<Record<string, string>>;
    paging?: {
        cursors?: { after?: string };
        next?: string;
    };
}

/**
 * Fetches a valid access token for Meta Ads API
 */
async function getValidAccessToken(clientId: string): Promise<string> {
    const integration = await prisma.integration.findFirst({
        where: { clientId, type: "meta_ads" },
    });

    if (!integration) {
        throw new Error(`No Meta Ads integration found for client ${clientId}`);
    }

    // Meta long-lived tokens last ~60 days, check expiry
    if (integration.expiresAt && integration.expiresAt < new Date()) {
        // Attempt to exchange for a new long-lived token
        if (!integration.refreshToken) {
            throw new Error("Meta token expired and no refresh mechanism available. Client needs to re-authenticate.");
        }

        try {
            const response = await fetch(
                `${META_GRAPH_API}/oauth/access_token?` +
                `grant_type=fb_exchange_token&` +
                `client_id=${process.env.META_APP_ID}&` +
                `client_secret=${process.env.META_APP_SECRET}&` +
                `fb_exchange_token=${integration.accessToken}`
            );

            if (!response.ok) {
                throw new Error("Failed to refresh Meta token");
            }

            const data = await response.json();

            await prisma.integration.update({
                where: { id: integration.id },
                data: {
                    accessToken: data.access_token,
                    expiresAt: new Date(Date.now() + (data.expires_in || 5184000) * 1000),
                },
            });

            return data.access_token;
        } catch (error) {
            throw new Error(`Failed to refresh Meta token: ${error instanceof Error ? error.message : "Unknown error"}`);
        }
    }

    return integration.accessToken;
}

/**
 * Makes a paginated request to the Meta Graph API
 */
async function fetchMetaApi(url: string, accessToken: string): Promise<MetaApiResponse["data"]> {
    const allData: MetaApiResponse["data"] = [];
    let nextUrl: string | null = url;

    while (nextUrl) {
        const response = await fetch(nextUrl, {
            headers: { Authorization: `Bearer ${accessToken}` },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(`Meta API error: ${JSON.stringify(error)}`);
        }

        const result: MetaApiResponse = await response.json();
        allData.push(...(result.data || []));

        // Handle pagination
        nextUrl = result.paging?.next || null;

        // Safety limit: max 10 pages
        if (allData.length > 1000) break;
    }

    return allData;
}

/**
 * Fetches Meta Ads metrics for a given ad account and date range
 */
export async function fetchMetaMetrics(
    clientId: string,
    adAccountId: string,
    startDate: string,
    endDate: string
): Promise<MetaMetrics> {
    const accessToken = await getValidAccessToken(clientId);

    // Fetch account-level insights and campaign-level insights in parallel
    const [accountInsights, campaignInsights, weeklyInsights] = await Promise.all([
        // Account-level aggregate metrics
        fetchMetaApi(
            `${META_GRAPH_API}/act_${adAccountId}/insights?` +
            `time_range={"since":"${startDate}","until":"${endDate}"}&` +
            `fields=spend,impressions,reach,clicks,ctr,cpc,cpm,actions,action_values&` +
            `level=account`,
            accessToken
        ),

        // Campaign-level breakdown (for top campaigns)
        fetchMetaApi(
            `${META_GRAPH_API}/act_${adAccountId}/insights?` +
            `time_range={"since":"${startDate}","until":"${endDate}"}&` +
            `fields=campaign_name,spend,impressions,clicks,actions,action_values&` +
            `level=campaign&sort=spend_descending&limit=10`,
            accessToken
        ),

        // Weekly breakdown for trend
        fetchMetaApi(
            `${META_GRAPH_API}/act_${adAccountId}/insights?` +
            `time_range={"since":"${startDate}","until":"${endDate}"}&` +
            `fields=spend&` +
            `time_increment=7`,
            accessToken
        ),
    ]);

    // Parse account-level metrics
    const account = accountInsights[0] || {};
    const spend = parseFloat(account.spend || "0");
    const impressions = parseInt(account.impressions || "0");
    const clicks = parseInt(account.clicks || "0");

    // Calculate ROAS from action_values (purchase value / spend)
    const purchaseValue = Array.isArray(account.action_values)
        ? account.action_values
            .filter((a: Record<string, string>) => a.action_type === "purchase" || a.action_type === "omni_purchase")
            .reduce((sum: number, a: Record<string, string>) => sum + parseFloat(a.value || "0"), 0)
        : 0;

    const roas = spend > 0 ? purchaseValue / spend : 0;

    // Parse top campaigns
    const topCampaigns: CampaignData[] = campaignInsights
        .slice(0, 3)
        .map((campaign) => {
            const campaignSpend = parseFloat(campaign.spend || "0");
            const campaignPurchaseValue = Array.isArray(campaign.action_values)
                ? campaign.action_values
                    .filter((a: Record<string, string>) => a.action_type === "purchase" || a.action_type === "omni_purchase")
                    .reduce((sum: number, a: Record<string, string>) => sum + parseFloat(a.value || "0"), 0)
                : 0;

            return {
                name: campaign.campaign_name || "Sin nombre",
                spend: campaignSpend,
                roas: campaignSpend > 0 ? campaignPurchaseValue / campaignSpend : 0,
                impressions: parseInt(campaign.impressions || "0"),
                clicks: parseInt(campaign.clicks || "0"),
            };
        });

    // Parse weekly spend trend
    const weekByWeekSpend: WeeklySpend[] = weeklyInsights.map(
        (week, index) => ({
            week: `Semana ${index + 1}`,
            spend: parseFloat(week.spend || "0"),
        })
    );

    return {
        spend,
        impressions,
        reach: parseInt(account.reach || "0"),
        clicks,
        ctr: parseFloat(account.ctr || "0"),
        cpc: parseFloat(account.cpc || "0"),
        cpm: parseFloat(account.cpm || "0"),
        roas,
        topCampaigns,
        weekByWeekSpend,
    };
}
