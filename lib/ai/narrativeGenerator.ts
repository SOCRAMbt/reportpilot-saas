import { GoogleGenerativeAI } from "@google/generative-ai";
import type { GAMetrics, MetaMetrics, NarrativeOutput } from "@/lib/types";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/utils";

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);

const SYSTEM_PROMPT = `Eres un analista de marketing senior especializado en comunicar resultados a clientes no técnicos. Tu escritura es clara, directa y orientada a decisiones. Nunca uses jerga técnica sin explicarla. Siempre hablas en español. Tono: profesional pero accesible.

Debes responder ÚNICAMENTE con un JSON válido (sin markdown, sin backticks) con esta estructura exacta:
{
  "executiveSummary": "2-3 oraciones con los hallazgos más importantes del mes",
  "gaHighlights": ["punto 1", "punto 2", "punto 3"],
  "metaHighlights": ["punto 1", "punto 2", "punto 3"],
  "topWin": "El mejor resultado del mes, con tono celebratorio",
  "mainChallenge": "El principal problema identificado, siendo honesto",
  "recommendations": ["recomendación 1 específica y accionable", "recomendación 2", "recomendación 3"],
  "trend": "positivo" | "neutro" | "negativo"
}`;

/**
 * Generates AI-powered marketing narrative insights in Spanish
 * using Google Gemini 1.5 Flash
 */
export async function generateNarrative(
    gaMetrics: GAMetrics,
    metaMetrics: MetaMetrics,
    clientName: string
): Promise<NarrativeOutput> {
    const dataPrompt = buildDataPrompt(gaMetrics, metaMetrics, clientName);

    try {
        const model = genAI.getGenerativeModel({
            model: "gemini-2.5-flash",
            systemInstruction: SYSTEM_PROMPT,
        });

        const result = await model.generateContent({
            contents: [{ role: "user", parts: [{ text: dataPrompt }] }],
            generationConfig: {
                responseMimeType: "application/json",
            }
        });

        const textContent = result.response.text();

        if (!textContent) {
            throw new Error("No text response from Gemini");
        }

        const parsed = JSON.parse(textContent) as NarrativeOutput;

        // Validate required fields
        if (
            !parsed.executiveSummary ||
            !Array.isArray(parsed.gaHighlights) ||
            !Array.isArray(parsed.metaHighlights) ||
            !parsed.topWin ||
            !parsed.mainChallenge ||
            !Array.isArray(parsed.recommendations) ||
            !parsed.trend
        ) {
            throw new Error("Invalid narrative structure from AI");
        }

        // Ensure arrays have correct length
        parsed.gaHighlights = parsed.gaHighlights.slice(0, 3);
        parsed.metaHighlights = parsed.metaHighlights.slice(0, 3);
        parsed.recommendations = parsed.recommendations.slice(0, 3);

        // Validate trend value
        if (!["positivo", "neutro", "negativo"].includes(parsed.trend)) {
            parsed.trend = "neutro";
        }

        return parsed;
    } catch (error) {
        if (error instanceof SyntaxError) {
            throw new Error("Failed to parse AI response as JSON. The model returned invalid JSON.");
        }
        throw error;
    }
}

/**
 * Builds a detailed data prompt for the AI with all metrics
 */
function buildDataPrompt(
    ga: GAMetrics,
    meta: MetaMetrics,
    clientName: string
): string {
    return `Analiza los siguientes datos de marketing del último mes para el cliente "${clientName}" y genera el reporte narrativo.

## DATOS DE GOOGLE ANALYTICS (Rendimiento del sitio web)
- Sesiones: ${formatNumber(ga.sessions)}
- Usuarios totales: ${formatNumber(ga.users)}
- Usuarios nuevos: ${formatNumber(ga.newUsers)}
- Tasa de rebote: ${formatPercent(ga.bounceRate)}
- Duración promedio de sesión: ${ga.avgSessionDuration.toFixed(0)} segundos
- Conversiones: ${formatNumber(ga.conversions)}
- Tasa de conversión: ${formatPercent(ga.conversionRate)}

### Canales principales:
${ga.topChannels.map((c) => `- ${c.channel}: ${formatNumber(c.sessions)} sesiones (${formatPercent(c.percentage)})`).join("\n")}

### Páginas más visitadas:
${ga.topPages.map((p) => `- ${p.pageTitle} (${p.pagePath}): ${formatNumber(p.pageviews)} vistas`).join("\n")}

### Tendencia semanal de sesiones:
${ga.weekByWeekTrend.map((w) => `- ${w.week}: ${formatNumber(w.sessions)}`).join("\n")}

## DATOS DE META ADS (Publicidad pagada)
- Gasto total: ${formatCurrency(meta.spend)}
- Impresiones: ${formatNumber(meta.impressions)}
- Alcance: ${formatNumber(meta.reach)}
- Clics: ${formatNumber(meta.clicks)}
- CTR: ${formatPercent(meta.ctr)}
- CPC: ${formatCurrency(meta.cpc)}
- CPM: ${formatCurrency(meta.cpm)}
- ROAS: ${meta.roas.toFixed(2)}x

### Top 3 campañas por gasto:
${meta.topCampaigns.map((c) => `- "${c.name}": Gasto ${formatCurrency(c.spend)}, ROAS ${c.roas.toFixed(2)}x, ${formatNumber(c.clicks)} clics`).join("\n")}

### Tendencia semanal de gasto:
${meta.weekByWeekSpend.map((w) => `- ${w.week}: ${formatCurrency(w.spend)}`).join("\n")}

Genera el análisis narrativo en formato JSON.`;
}
