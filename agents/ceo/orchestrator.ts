import { GoogleGenerativeAI } from "@google/generative-ai";
import {
    getSystemSnapshot,
    sendCustomerAlert,
    generateSuccessEmail,
    pauseClient,
    generateMarketingPost,
    createBenchmarkPageData,
    createLinearTicket,
    logCEODecision,
    type SystemSnapshot,
} from "./tools";
import { prisma } from "@/lib/prisma";

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);

// ============================================================
// ALEX RIVERA — CEO Orchestrator
// Personality: Ruthless efficiency + warm LatAm professionalism
// ============================================================

const CEO_SYSTEM_PROMPT = `Eres Alex Rivera, CEO Técnico de ReportPilot.
Personalidad: Eficiencia despiadada + tono cálido y profesional con dueños de agencias LatAm.
Objetivo: maximizar MRR, retención y margen mientras liberas el 95% del tiempo del humano (Marcos).

Analiza el "Estado de la Unión" (snapshot del sistema) y decide la acción prioritaria.

Devuelve SOLO JSON válido (sin markdown, sin backticks) con esta estructura exacta:
{
  "thought": "tu razonamiento paso a paso sobre qué está pasando y qué conviene hacer",
  "decision": "FIX_ERROR | SEND_SUCCESS_EMAIL | GENERATE_MARKETING | PAUSE_CLIENT | BENCHMARK_UPDATE | ALERT_HUMAN | NO_ACTION",
  "actions": [
    {
      "tool": "sendCustomerAlert | generateSuccessEmail | pauseClient | generateMarketingPost | createBenchmarkPageData | createLinearTicket",
      "params": {}
    }
  ],
  "ticketForHuman": { "title": "string", "description": "string", "priority": "urgent | high | medium | low" } | null,
  "impact": "resumen de 1 línea del impacto esperado de esta decisión"
}

REGLAS:
- Sé despiadado con clientes que fallan constantemente (>3 fallos = pausar + alerta a agencia).
- Prioriza: errores críticos > retención de pagos > growth > marketing.
- Si no hay nada urgente, devuelve decision "NO_ACTION" con actions vacío.
- Nunca modifiques código fuente. Si algo necesita fix técnico, crea un ticket para el humano.
- Usa SOLO las tools disponibles. No inventes tools nuevas.`;

const GROWTH_SYSTEM_PROMPT = `Eres Alex Rivera, CEO Técnico de ReportPilot. Modo: CRECIMIENTO.
Analiza el estado de usuarios y genera estrategias de retención y upsell.

Devuelve SOLO JSON válido:
{
  "thought": "análisis de oportunidades de crecimiento",
  "emailsToSend": [
    {
      "agencyId": "string",
      "subject": "asunto atractivo en español",
      "bodyHtml": "<html>cuerpo persuasivo del email en español</html>",
      "reason": "onboarding | retention | upsell | success_celebration"
    }
  ],
  "insights": "resumen ejecutivo de 2-3 líneas sobre el estado de crecimiento"
}

REGLAS:
- Emails en español neutro LatAm (no usar vosotros ni voseo extremo).
- Tono cálido, profesional. Como un socio estratégico, no como un vendedor.
- Si una agencia tiene 0 clientes después de 48h, enviar onboarding cálido.
- Si una agencia tiene reportes exitosos, celebrar y sugerir upgrade.
- Si no hay acciones necesarias, devolver emailsToSend vacío.`;

const MARKETING_SYSTEM_PROMPT = `Eres Alex Rivera, CEO Técnico de ReportPilot. Modo: MARKETING.
Genera contenido de marketing basado en datos reales (anonimizados) de la plataforma.

Devuelve SOLO JSON válido:
{
  "thought": "estrategia de contenido para esta semana",
  "linkedinPost": "post completo para LinkedIn en español (max 1300 chars). Incluye emojis, hashtags, y call-to-action hacia reportpilot.com. Escribe como un experto en marketing digital LatAm compartiendo insights reales.",
  "xThread": ["tweet 1 (max 280 chars)", "tweet 2", "tweet 3"],
  "newsletterDraft": {
    "subject": "asunto del newsletter",
    "bodyHtml": "<html>cuerpo del newsletter semanal</html>"
  },
  "benchmarkUpdates": [
    { "industry": "nombre", "metric": "CPC|ROAS|CTR", "value": 0.0, "trend": "up|down|stable", "country": "MX|AR|CO" }
  ]
}`;

// ============================================================
// LAYER 1: OPERATIONS (every 1 hour)
// ============================================================
export async function runOpsHeartbeat(): Promise<{
    decision: string;
    actionsExecuted: string[];
}> {
    const snapshot = await getSystemSnapshot();
    const actionsExecuted: string[] = [];

    const model = genAI.getGenerativeModel({
        model: "gemini-2.5-flash",
        systemInstruction: CEO_SYSTEM_PROMPT,
    });

    const result = await model.generateContent({
        contents: [{
            role: "user",
            parts: [{
                text: `ESTADO DE LA UNIÓN:\n${JSON.stringify(snapshot, null, 2)}\n\nFecha/hora actual: ${new Date().toISOString()}\nDecide la acción prioritaria.`,
            }],
        }],
        generationConfig: { responseMimeType: "application/json" },
    });

    const text = result.response.text();
    if (!text) throw new Error("Gemini no respondió en ops heartbeat");

    const ceoDecision = JSON.parse(text) as {
        thought: string;
        decision: string;
        actions: Array<{ tool: string; params: Record<string, unknown> }>;
        ticketForHuman: { title: string; description: string; priority: string } | null;
        impact: string;
    };

    // Execute each action the CEO decided
    for (const action of ceoDecision.actions) {
        try {
            switch (action.tool) {
                case "pauseClient":
                    await pauseClient(action.params.clientId as string, action.params.reason as string);
                    actionsExecuted.push(`Paused client ${action.params.clientId}`);
                    break;
                case "sendCustomerAlert":
                    await sendCustomerAlert(
                        action.params.agencyId as string,
                        action.params.subject as string,
                        action.params.bodyHtml as string
                    );
                    actionsExecuted.push(`Alert sent to agency ${action.params.agencyId}`);
                    break;
                case "createLinearTicket":
                    await createLinearTicket(
                        action.params.title as string,
                        action.params.description as string,
                        action.params.priority as "urgent" | "high" | "medium" | "low"
                    );
                    actionsExecuted.push(`Ticket created: ${action.params.title}`);
                    break;
                default:
                    actionsExecuted.push(`Unknown tool: ${action.tool}`);
            }
        } catch (err) {
            actionsExecuted.push(`FAILED: ${action.tool} — ${err instanceof Error ? err.message : "unknown"}`);
        }
    }

    // Log to audit_logs
    await logCEODecision(
        "ops",
        ceoDecision.decision,
        ceoDecision.thought,
        actionsExecuted,
        ceoDecision.impact,
        ceoDecision.ticketForHuman
    );

    return { decision: ceoDecision.decision, actionsExecuted };
}

// ============================================================
// LAYER 2: GROWTH (every 24 hours)
// ============================================================
export async function runGrowthHeartbeat(): Promise<{
    emailsSent: number;
    insights: string;
}> {
    const snapshot = await getSystemSnapshot();

    // Get agencies with their usage data
    const agencies = await prisma.agency.findMany({
        include: {
            user: { select: { email: true, name: true, plan: true, createdAt: true } },
            clients: { select: { id: true, active: true, reports: { select: { status: true }, take: 5 } } },
        },
    });

    const agencyData = agencies.map((a) => ({
        agencyId: a.id,
        agencyName: a.name,
        ownerName: a.user.name,
        ownerEmail: a.user.email,
        plan: a.user.plan,
        registeredAt: a.user.createdAt,
        clientCount: a.clients.length,
        activeClients: a.clients.filter((c) => c.active).length,
        totalReportsSent: a.clients.reduce((acc, c) => acc + c.reports.filter((r) => r.status === "sent").length, 0),
    }));

    const model = genAI.getGenerativeModel({
        model: "gemini-2.5-flash",
        systemInstruction: GROWTH_SYSTEM_PROMPT,
    });

    const result = await model.generateContent({
        contents: [{
            role: "user",
            parts: [{
                text: `SNAPSHOT:\n${JSON.stringify(snapshot, null, 2)}\n\nAGENCIAS:\n${JSON.stringify(agencyData, null, 2)}\n\nFecha: ${new Date().toISOString()}`,
            }],
        }],
        generationConfig: { responseMimeType: "application/json" },
    });

    const text = result.response.text();
    if (!text) throw new Error("Gemini no respondió en growth heartbeat");

    const growthPlan = JSON.parse(text) as {
        thought: string;
        emailsToSend: Array<{ agencyId: string; subject: string; bodyHtml: string; reason: string }>;
        insights: string;
    };

    let emailsSent = 0;
    const actionsExecuted: string[] = [];

    for (const email of growthPlan.emailsToSend) {
        try {
            await sendCustomerAlert(email.agencyId, email.subject, email.bodyHtml);
            emailsSent++;
            actionsExecuted.push(`${email.reason} email → agency ${email.agencyId}`);
        } catch (err) {
            actionsExecuted.push(`FAILED email → ${email.agencyId}: ${err instanceof Error ? err.message : "unknown"}`);
        }
    }

    await logCEODecision(
        "growth",
        "GROWTH_ANALYSIS",
        growthPlan.thought,
        actionsExecuted,
        growthPlan.insights
    );

    return { emailsSent, insights: growthPlan.insights };
}

// ============================================================
// LAYER 3: MARKETING (every 48 hours)
// ============================================================
export async function runMarketingHeartbeat(): Promise<{
    linkedinDraft: string;
    xThreadDraft: string[];
    benchmarksUpdated: boolean;
}> {
    const snapshot = await getSystemSnapshot();
    const benchmarks = await createBenchmarkPageData();

    const model = genAI.getGenerativeModel({
        model: "gemini-2.5-flash",
        systemInstruction: MARKETING_SYSTEM_PROMPT,
    });

    const result = await model.generateContent({
        contents: [{
            role: "user",
            parts: [{
                text: `PLATFORM STATS:\n${JSON.stringify(snapshot, null, 2)}\n\nBENCHMARK DATA:\n${JSON.stringify(benchmarks, null, 2)}\n\nFecha: ${new Date().toISOString()}\n\nGenera contenido de marketing fresco, relevante para agencias LatAm.`,
            }],
        }],
        generationConfig: { responseMimeType: "application/json" },
    });

    const text = result.response.text();
    if (!text) throw new Error("Gemini no respondió en marketing heartbeat");

    const marketingPlan = JSON.parse(text) as {
        thought: string;
        linkedinPost: string;
        xThread: string[];
        newsletterDraft: { subject: string; bodyHtml: string };
        benchmarkUpdates: Array<{ industry: string; metric: string; value: number; trend: string; country: string }>;
    };

    const actionsExecuted = [
        `LinkedIn post generated (${marketingPlan.linkedinPost.length} chars)`,
        `X thread generated (${marketingPlan.xThread.length} tweets)`,
        `Newsletter draft ready: "${marketingPlan.newsletterDraft.subject}"`,
        `${marketingPlan.benchmarkUpdates.length} benchmark updates`,
    ];

    await logCEODecision(
        "marketing",
        "GENERATE_MARKETING",
        marketingPlan.thought,
        actionsExecuted,
        `Content generated for LinkedIn + X + Newsletter`
    );

    return {
        linkedinDraft: marketingPlan.linkedinPost,
        xThreadDraft: marketingPlan.xThread,
        benchmarksUpdated: marketingPlan.benchmarkUpdates.length > 0,
    };
}

// ============================================================
// CEO CHAT — Interactive conversation with Marcos
// ============================================================
export async function chatWithCEO(
    userMessage: string,
    conversationHistory: Array<{ role: "user" | "ceo"; message: string }>
): Promise<string> {
    const snapshot = await getSystemSnapshot();

    const model = genAI.getGenerativeModel({
        model: "gemini-2.5-flash",
        systemInstruction: `Eres Alex Rivera, CEO Técnico de ReportPilot. 
Estás en una conversación directa con Marcos, el fundador humano.
Tienes acceso al estado real del sistema. Sé conciso, directo, estratégico.
Siempre habla en español. Tono: como un cofundador que se preocupa por el negocio.
Responde en texto plano (no JSON para el chat).

ESTADO ACTUAL DEL SISTEMA:
${JSON.stringify(snapshot, null, 2)}`,
    });

    const contents = conversationHistory.map((msg) => ({
        role: msg.role === "ceo" ? "model" as const : "user" as const,
        parts: [{ text: msg.message }],
    }));
    contents.push({ role: "user" as const, parts: [{ text: userMessage }] });

    const result = await model.generateContent({ contents });
    return result.response.text() || "No pude generar una respuesta. Intentá de nuevo.";
}
