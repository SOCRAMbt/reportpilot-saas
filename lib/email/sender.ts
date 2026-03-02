import { Resend } from "resend";
import { getMonthName } from "@/lib/utils";

const resend = new Resend(process.env.RESEND_API_KEY || "fallback_key");

interface SendReportParams {
  clientEmail: string;
  clientName: string;
  agencyName: string;
  agencyLogoUrl: string | null;
  agencyBrandColor: string;
  executiveSummary: string;
  pdfBuffer: Buffer;
  month: number;
  year: number;
}

/**
 * Sends the monthly report email with PDF attachment
 */
export async function sendReport(params: SendReportParams): Promise<void> {
  const {
    clientEmail,
    clientName,
    agencyName,
    agencyBrandColor,
    executiveSummary,
    pdfBuffer,
    month,
    year,
  } = params;

  const monthName = getMonthName(month);
  const subject = `📊 Tu reporte de ${monthName} está listo, ${clientName}`;
  const firstName = clientName.split(" ")[0];

  const html = buildEmailTemplate({
    firstName,
    clientName,
    agencyName,
    agencyBrandColor,
    executiveSummary,
    monthName,
    year,
  });

  try {
    await resend.emails.send({
      from: `${agencyName} <reportes@reportpilot.com>`,
      to: clientEmail,
      subject,
      html,
      attachments: [
        {
          filename: `Reporte-${monthName}-${year}-${clientName.replace(/\s+/g, "-")}.pdf`,
          content: pdfBuffer,
        },
      ],
    });
  } catch (error) {
    throw new Error(
      `Failed to send email to ${clientEmail}: ${error instanceof Error ? error.message : "Unknown error"}`
    );
  }
}

interface EmailTemplateParams {
  firstName: string;
  clientName: string;
  agencyName: string;
  agencyBrandColor: string;
  executiveSummary: string;
  monthName: string;
  year: number;
}

function buildEmailTemplate(params: EmailTemplateParams): string {
  const {
    firstName,
    agencyName,
    agencyBrandColor,
    executiveSummary,
    monthName,
    year,
  } = params;

  return `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reporte de ${monthName} ${year}</title>
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f1f5f9;padding:32px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 6px rgba(0,0,0,0.05);">
          <!-- Header -->
          <tr>
            <td style="background-color:${agencyBrandColor};padding:32px 40px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;">${agencyName}</h1>
              <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">Reporte mensual de marketing</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <h2 style="margin:0 0 8px;color:#0f172a;font-size:20px;font-weight:700;">
                ¡Hola ${firstName}! 👋
              </h2>
              <p style="margin:0 0 24px;color:#64748b;font-size:15px;line-height:1.6;">
                Tu reporte de <strong>${monthName} ${year}</strong> ya está listo. Aquí tienes un resumen rápido:
              </p>

              <!-- Summary Card -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;border-radius:8px;border-left:4px solid ${agencyBrandColor};margin-bottom:32px;">
                <tr>
                  <td style="padding:20px;">
                    <p style="margin:0;color:#334155;font-size:14px;line-height:1.7;">
                      ${executiveSummary}
                    </p>
                  </td>
                </tr>
              </table>

              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center">
                    <p style="margin:0 0 16px;color:#64748b;font-size:14px;">
                      Abrí el PDF adjunto para ver el reporte completo con todos los detalles y recomendaciones.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Divider -->
              <hr style="border:none;border-top:1px solid #e2e8f0;margin:32px 0;">

              <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.5;">
                Este reporte fue generado automáticamente por <strong>ReportPilot</strong> 
                para ${agencyName}. Si tienes preguntas, contacta directamente a tu agencia.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f8fafc;padding:20px 40px;text-align:center;border-top:1px solid #e2e8f0;">
              <p style="margin:0;color:#94a3b8;font-size:11px;">
                Generado automáticamente por ReportPilot · reportpilot.com
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
}
