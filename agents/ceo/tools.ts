import { prisma } from "@/lib/prisma";
import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY!);

// ============================================================
// CEO TOOLS — Function Calling Interface for Alex Rivera
// Each tool is an atomic, auditable action the CEO can execute.
// ============================================================

export interface SystemSnapshot {
    totalUsers: number;
    totalAgencies: number;
    totalClients: number;
    activeClients: number;
    inactiveClients: number;
    reportsSentThisMonth: number;
    reportsFailed: number;
    reportsProcessing: number;
    agenciesWithoutClients: number;
    freeUsers: number;
    paidUsers: number;
    recentErrors: string[];
}

export async function getSystemSnapshot(): Promise<SystemSnapshot> {
    const now = new Date();
    const firstOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

    const [
        totalUsers,
        totalAgencies,
        totalClients,
        activeClients,
        inactiveClients,
        reportsSentThisMonth,
        reportsFailed,
        reportsProcessing,
        freeUsers,
        paidUsers,
    ] = await Promise.all([
        prisma.user.count(),
        prisma.agency.count(),
        prisma.client.count(),
        prisma.client.count({ where: { active: true } }),
        prisma.client.count({ where: { active: false } }),
        prisma.report.count({ where: { status: "sent", createdAt: { gte: firstOfMonth } } }),
        prisma.report.count({ where: { status: "failed" } }),
        prisma.report.count({ where: { status: "processing" } }),
        prisma.user.count({ where: { plan: "free" } }),
        prisma.user.count({ where: { plan: { not: "free" } } }),
    ]);

    // Agencies that registered but never added a client
    const agenciesWithClients = await prisma.agency.count({ where: { clients: { some: {} } } });
    const agenciesWithoutClients = totalAgencies - agenciesWithClients;

    // Get recent failed reports as "errors"
    const failedReports = await prisma.report.findMany({
        where: { status: "failed" },
        take: 10,
        orderBy: { createdAt: "desc" },
        include: { client: { select: { name: true, email: true } } },
    });

    const recentErrors = failedReports.map(
        (r) => `Report ${r.id} for ${r.client.name} (${r.client.email}) failed on ${r.createdAt.toISOString()}`
    );

    return {
        totalUsers,
        totalAgencies,
        totalClients,
        activeClients,
        inactiveClients,
        reportsSentThisMonth,
        reportsFailed,
        reportsProcessing,
        agenciesWithoutClients,
        freeUsers,
        paidUsers,
        recentErrors,
    };
}

export async function updateReportStatus(
    reportId: string,
    status: "pending" | "processing" | "sent" | "failed",
    notes?: string
): Promise<{ success: boolean }> {
    await prisma.report.update({
        where: { id: reportId },
        data: { status, ...(status === "sent" ? { sentAt: new Date() } : {}) },
    });
    console.log(`[CEO] Report ${reportId} → ${status}${notes ? ` | ${notes}` : ""}`);
    return { success: true };
}

export async function sendCustomerAlert(
    agencyId: string,
    subject: string,
    bodyHtml: string
): Promise<{ success: boolean; email: string }> {
    const agency = await prisma.agency.findUnique({
        where: { id: agencyId },
        include: { user: { select: { email: true, name: true } } },
    });
    if (!agency || !agency.user.email) throw new Error(`Agency ${agencyId} not found or no email`);

    await resend.emails.send({
        from: `Alex Rivera — ReportPilot <ceo@reportpilot.com>`,
        to: agency.user.email,
        subject,
        html: bodyHtml,
    });
    return { success: true, email: agency.user.email };
}

export async function generateSuccessEmail(clientId: string): Promise<{ subject: string; body: string }> {
    const client = await prisma.client.findUnique({
        where: { id: clientId },
        include: {
            agency: true,
            reports: { where: { status: "sent" }, orderBy: { createdAt: "desc" }, take: 1 },
        },
    });
    if (!client) throw new Error(`Client ${clientId} not found`);

    const reportCount = await prisma.report.count({ where: { clientId, status: "sent" } });

    const subject = `🎉 ${client.agency.name}: ${reportCount} reportes enviados exitosamente a ${client.name}`;
    const body = `<div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
    <h2 style="color:#3B82F6;">¡Felicitaciones, ${client.agency.name}!</h2>
    <p>Tu cliente <strong>${client.name}</strong> ya ha recibido <strong>${reportCount}</strong> reportes automáticos.</p>
    <p>Cada reporte que enviás refuerza tu posición como agencia profesional y confiable. Seguí así. 💪</p>
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0;">
    <p style="color:#94a3b8;font-size:12px;">— Alex Rivera, CEO Técnico de ReportPilot</p>
  </div>`;

    return { subject, body };
}

export async function pauseClient(
    clientId: string,
    reason: string
): Promise<{ success: boolean }> {
    await prisma.client.update({
        where: { id: clientId },
        data: { active: false },
    });
    console.log(`[CEO] Client ${clientId} PAUSED. Reason: ${reason}`);
    return { success: true };
}

export async function generateMarketingPost(
    platform: "linkedin" | "x",
    trendData: string
): Promise<{ draft: string }> {
    // Gemini will generate the actual content via the orchestrator
    // This tool just structures the output
    return {
        draft: `[${platform.toUpperCase()} DRAFT] Based on trend: ${trendData}. (Content generated by CEO orchestrator)`,
    };
}

export async function createBenchmarkPageData(): Promise<{
    industries: Array<{ name: string; avgCPC: number; avgROAS: number; avgCTR: number; country: string }>;
}> {
    // Aggregate anonymized data from all clients
    const clients = await prisma.client.findMany({
        where: { active: true },
        include: { reports: { where: { status: "sent" }, orderBy: { createdAt: "desc" }, take: 1 } },
    });

    // In production this would parse the report data snapshots
    // For now return structured placeholder that the CEO enriches
    return {
        industries: [
            { name: "E-commerce", avgCPC: 0.45, avgROAS: 4.2, avgCTR: 2.1, country: "MX" },
            { name: "Servicios Profesionales", avgCPC: 1.2, avgROAS: 3.1, avgCTR: 1.8, country: "AR" },
            { name: "Educación Online", avgCPC: 0.35, avgROAS: 5.5, avgCTR: 3.2, country: "CO" },
            { name: "Salud y Bienestar", avgCPC: 0.8, avgROAS: 3.8, avgCTR: 2.5, country: "MX" },
        ],
    };
}

export async function createLinearTicket(
    title: string,
    description: string,
    priority: "urgent" | "high" | "medium" | "low"
): Promise<{ ticketId: string; logged: boolean }> {
    // In production, this would call Linear API or GitHub Issues API
    // For now, log to audit_logs and console
    const ticketId = `TICKET-${Date.now()}`;
    console.log(`[CEO] 🎫 Created ticket ${ticketId}: [${priority.toUpperCase()}] ${title}`);
    console.log(`[CEO]    Description: ${description}`);
    return { ticketId, logged: true };
}

export async function logCEODecision(
    layer: string,
    decision: string,
    thought: string,
    actionsTaken: unknown[],
    impact?: string,
    ticketJson?: unknown
): Promise<void> {
    await prisma.auditLog.create({
        data: {
            layer,
            decision,
            thought,
            actionsTaken: JSON.stringify(actionsTaken),
            impact: impact || null,
            ticketJson: ticketJson ? JSON.stringify(ticketJson) : null,
        },
    });
}
