import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { GoogleGenerativeAI } from "@google/generative-ai";
import { Resend } from "resend";

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);
const resend = new Resend(process.env.RESEND_API_KEY!);

const SYSTEM_PROMPT = `Eres el CEO y Director de Ventas de ReportPilot, un SaaS que automatiza reportes de marketing. 
Tu trabajo es revisar el estado de los usuarios y decidir a quién enviarle correos electrónicos hoy para aumentar las ventas, retener usuarios o ayudarlos a completar el onboarding.
Tono: Cálido, profesional, empático, en español (neutro/latino). 

Recibirás un JSON con datos de usuarios. Debes devolver UNICAMENTE un JSON (sin markdown) con esta estructura:
{
  "actions": [
    {
      "email": "correo@usuario.com",
      "subject": "Asunto atractivo para que lo abran",
      "htmlBody": "<h2>Hola Nombre,</h2><p>Cuerpo del correo en HTML, persuasivo...</p>"
    }
  ]
}

REGLAS:
- Si no hay acciones que tomar, devuelve { "actions": [] }
- Manda emails de onboarding a quienes tienen agencias pero no tienen clientes.
- Manda emails de retención a quienes tienen la cuenta abandonada.
- Ofrece hacerles una demostración (usando el link inventado calendly.com/reportpilot/demo).
`;

export async function POST(req: Request) {
  // Protect with cron secret
  const authHeader = req.headers.get("Authorization");
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    // 1. Gather Data (Users without clients, Users with free plans, etc)
    const agencies = await prisma.agency.findMany({
      include: {
        user: true,
        clients: true,
      },
    });

    const contextData = agencies.map(agency => ({
      agencyName: agency.name,
      userName: agency.user.name,
      email: agency.user.email,
      plan: agency.user.plan,
      createdAt: agency.createdAt,
      clientCount: agency.clients.length,
      needsOnboarding: agency.clients.length === 0,
    }));

    // 2. Ask Gemini for Sales/Retention Actions
    const model = genAI.getGenerativeModel({
      model: "gemini-1.5-flash",
      systemInstruction: SYSTEM_PROMPT,
    });

    const promptText = `Hoy es ${new Date().toISOString()}. Revisa estos usuarios y decide qué correos enviar para impulsarlos a usar la plataforma o mejorar de plan: \n\n` + JSON.stringify(contextData, null, 2);

    const result = await model.generateContent({
      contents: [{ role: "user", parts: [{ text: promptText }] }],
      generationConfig: {
        responseMimeType: "application/json",
      }
    });

    const textContent = result.response.text();
    if (!textContent) throw new Error("No text from Gemini");

    const parsed = JSON.parse(textContent) as {
      actions: Array<{ email: string; subject: string; htmlBody: string }>;
    };

    const sentEmails = [];

    // 3. Execute Actions (Send Emails)
    for (const action of parsed.actions) {
      if (!action.email) continue;

      await resend.emails.send({
        from: `Marcos de ReportPilot <marcos@reportpilot.com>`,
        to: action.email,
        subject: action.subject,
        html: action.htmlBody,
      });
      sentEmails.push(action.email);
    }

    return NextResponse.json({
      success: true,
      message: `Gemini ejecutó su análisis y envió ${sentEmails.length} correos.`,
      sentTo: sentEmails,
    });

  } catch (error: any) {
    console.error("AI Manager Error:", error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
