// ===== Google Analytics Types =====
export interface GAMetrics {
    sessions: number;
    users: number;
    newUsers: number;
    bounceRate: number;
    avgSessionDuration: number;
    topChannels: ChannelData[];
    topPages: PageData[];
    conversions: number;
    conversionRate: number;
    weekByWeekTrend: WeeklyTrend[];
}

export interface ChannelData {
    channel: string;
    sessions: number;
    percentage: number;
}

export interface PageData {
    pagePath: string;
    pageTitle: string;
    pageviews: number;
}

export interface WeeklyTrend {
    week: string;
    sessions: number;
}

// ===== Meta Ads Types =====
export interface MetaMetrics {
    spend: number;
    impressions: number;
    reach: number;
    clicks: number;
    ctr: number;
    cpc: number;
    cpm: number;
    roas: number;
    topCampaigns: CampaignData[];
    weekByWeekSpend: WeeklySpend[];
}

export interface CampaignData {
    name: string;
    spend: number;
    roas: number;
    impressions: number;
    clicks: number;
}

export interface WeeklySpend {
    week: string;
    spend: number;
}

// ===== AI Narrative Types =====
export type TrendDirection = "positivo" | "neutro" | "negativo";

export interface NarrativeOutput {
    executiveSummary: string;
    gaHighlights: string[];
    metaHighlights: string[];
    topWin: string;
    mainChallenge: string;
    recommendations: string[];
    trend: TrendDirection;
}

// ===== Report Data Types =====
export interface ReportData {
    clientName: string;
    clientEmail: string;
    agencyName: string;
    agencyLogoUrl: string | null;
    agencyBrandColor: string;
    month: number;
    year: number;
    gaMetrics: GAMetrics;
    metaMetrics: MetaMetrics;
    narrative: NarrativeOutput;
}

// ===== Plan Types =====
export type PlanType = "free" | "starter" | "growth" | "agency";

export interface PlanConfig {
    name: string;
    maxClients: number;
    price: number;
    priceId: string | null;
}

export const PLAN_CONFIGS: Record<PlanType, PlanConfig> = {
    free: { name: "Free", maxClients: 0, price: 0, priceId: null },
    starter: { name: "Starter", maxClients: 1, price: 79, priceId: process.env.STRIPE_STARTER_PRICE_ID || "" },
    growth: { name: "Growth", maxClients: 5, price: 129, priceId: process.env.STRIPE_GROWTH_PRICE_ID || "" },
    agency: { name: "Agency", maxClients: 999, price: 199, priceId: process.env.STRIPE_AGENCY_PRICE_ID || "" },
};

// ===== API Response Types =====
export interface GenerationResult {
    clientId: string;
    clientName: string;
    success: boolean;
    error?: string;
}

export interface GenerationSummary {
    success: number;
    failed: number;
    errors: GenerationResult[];
}
