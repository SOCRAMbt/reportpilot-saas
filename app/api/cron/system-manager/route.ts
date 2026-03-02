import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { GoogleGenerativeAI } from "@google/generative-ai";
import { Resend } from "resend";

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);
const resend = new Resend(process.env.RESEND_API_KEY!);

const SYSTEM_PROMPT = `Eres el "Director Técnico e IA de Operaciones" del sistema ReportPilot.
Tu tarea es leer el reporte de estado de la base de datos y la plataforma, y detectar si hay problemas (por ejemplo, muchas cuentas sin conectar, agencias sin clientes, tokens de integración caídos o estancamiento en el registro de usuarios). 
Debes proponer soluciones automatizables o dar un diagnóstico técnico accionable al administrador.

Devuelve UNICAMENTE un JSON (sin markdown) con esta estructura:
{
  "status": "Healthy | Warning | Critical",
  "issuesFound": ["problema 1...", "problema 2..."],
  "aiDiagnosis": "Un análisis profundo de 1 o 2 párrafos sobre la salud del sistema.",
  "recommendedFixes": ["Qué debería arreglar o implementar el dev a nivel técnico."]
}
`;

export async function POST(req: Request) {
    const authHeader = req.headers.get("Authorization");
    if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
        // 1. Recopilar métricas del sistema
        const totalUsers = await prisma.user.count();
        const totalAgencies = await prisma.agency.count();
        const totalClients = await prisma.client.count();
        const sentReports = await prisma.report.count({ where: { status: "sent" } });
        const failedReports = await prisma.report.count({ where: { status: "failed" } });

        // Buscar clientes inactivos o con problemas de integración
        const inactiveClients = await prisma.client.count({ where: { active: false } });

        const systemData = {
            timestamp: new Date().toISOString(),
            metrics: {
                totalUsers,
                totalAgencies,
                totalClients,
                sentReports,
                failedReports,
                inactiveClients,
            }
        };

        // 2. Hacer que Gemini actúe como System Manager para razonar sobre estos datos
        const model = genAI.getGenerativeModel({
            model: "gemini-1.5-flash",
            systemInstruction: SYSTEM_PROMPT,
        });

        const result = await model.generateContent({
            contents: [{ role: "user", parts: [{ text: "Aquí tienes los datos de la base de datos de producción hoy:\n\n" + JSON.stringify(systemData, null, 2) }] }],
            generationConfig: {
                responseMimeType: "application/json",
            }
        });

        const textContent = result.response.text();
        if (!textContent) throw new Error("Gemini no respondió.");

        const analysis = JSON.parse(textContent);

        // 3. (Opcional) Autocorrección básica. Si Gemini detecta problemas críticos de tokens, 
        // en el futuro el sistema puede ejecutar rutinas de auto-healing. Por ahora, notifica al admin.

        if (analysis.status === "Warning" || analysis.status === "Critical") {
            await resend.emails.send({
                from: `System Manager <manager@reportpilot.com>`,
                to: "casselsmarcos1@gmail.com", // Admin email
                subject: `⚠️ ReportPilot Alerta del Sistema: ${analysis.status}`,
                html: `<h2>Gemini ha detectado problemas en el sistema</h2>
               <p><strong>Diagnóstico:</strong> ${analysis.aiDiagnosis}</p>
               <ul>${analysis.issuesFound.map((i: string) => `<li>${i}</li>`).join('')}</ul>
               <h3>Recomendaciones para ti:</h3>
               <ul>${analysis.recommendedFixes.map((r: string) => `<li>${r}</li>`).join('')}</ul>`,
            });
        }

        return NextResponse.json({
            success: true,
            message: "Operación de mantenimiento y regulación completada por el AI Manager.",
            analysis
        });

    } catch (error: any) {
        console.error("System Manager Error:", error);
        return NextResponse.json(
            { success: false, error: error.message },
            { status: 500 }
        );
    }
}
