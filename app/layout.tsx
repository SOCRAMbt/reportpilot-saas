import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { SessionProvider } from "next-auth/react";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "ReportPilot — Reportes de marketing automáticos",
  description:
    "Conecta Google Analytics y Meta Ads una vez. El día 1 de cada mes, tus clientes reciben su reporte automáticamente.",
  keywords: ["marketing", "reportes", "automatización", "agencias", "Google Analytics", "Meta Ads"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className={`${inter.variable} font-sans antialiased`}>
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
