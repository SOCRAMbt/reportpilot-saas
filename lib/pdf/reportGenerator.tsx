import React from "react";
import {
    Document,
    Page,
    Text,
    View,
    StyleSheet,
    Font,
    renderToBuffer,
} from "@react-pdf/renderer";
import { put } from "@vercel/blob";
import type { ReportData } from "@/lib/types";
import { formatCurrency, formatNumber, formatPercent, getMonthName } from "@/lib/utils";

Font.register({
    family: "Inter",
    fonts: [
        { src: "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfMZg.ttf", fontWeight: 400 },
        { src: "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuGKYMZg.ttf", fontWeight: 600 },
        { src: "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuFuYMZg.ttf", fontWeight: 700 },
    ],
});

const createStyles = (brandColor: string) =>
    StyleSheet.create({
        page: { fontFamily: "Inter", fontSize: 10, color: "#1e293b", paddingTop: 40, paddingBottom: 60, paddingHorizontal: 40 },
        coverPage: { fontFamily: "Inter", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", backgroundColor: brandColor, color: "white" },
        coverTitle: { fontSize: 36, fontWeight: 700, marginBottom: 8 },
        coverSubtitle: { fontSize: 18, fontWeight: 400, opacity: 0.9 },
        coverMonth: { fontSize: 24, fontWeight: 600, marginTop: 40 },
        coverClient: { fontSize: 20, fontWeight: 400, marginTop: 8, opacity: 0.9 },
        sectionTitle: { fontSize: 20, fontWeight: 700, color: brandColor, marginBottom: 16, paddingBottom: 8, borderBottomWidth: 2, borderBottomColor: brandColor },
        metricsRow: { flexDirection: "row", marginBottom: 12, gap: 12 },
        metricCard: { flex: 1, backgroundColor: "#f8fafc", borderRadius: 8, padding: 12, borderLeftWidth: 3, borderLeftColor: brandColor },
        metricLabel: { fontSize: 8, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 },
        metricValue: { fontSize: 18, fontWeight: 700, color: "#0f172a" },
        tableHeader: { flexDirection: "row", backgroundColor: brandColor, padding: 8, borderRadius: 4, marginBottom: 4 },
        tableHeaderText: { color: "white", fontSize: 8, fontWeight: 600, textTransform: "uppercase" },
        tableRow: { flexDirection: "row", padding: 8, borderBottomWidth: 1, borderBottomColor: "#e2e8f0" },
        tableCell: { fontSize: 9 },
        insightCard: { backgroundColor: "#f8fafc", borderRadius: 8, padding: 16, marginBottom: 12, borderLeftWidth: 4 },
        insightTitle: { fontSize: 12, fontWeight: 700, marginBottom: 6 },
        insightText: { fontSize: 10, lineHeight: 1.5, color: "#334155" },
        bulletPoint: { flexDirection: "row", marginBottom: 6 },
        bullet: { width: 16, color: brandColor, fontWeight: 700 },
        bulletText: { flex: 1, fontSize: 10, lineHeight: 1.4, color: "#334155" },
        trendBadge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, alignSelf: "flex-start", marginBottom: 16 },
        trendText: { fontSize: 11, fontWeight: 600 },
        barContainer: { marginBottom: 8 },
        barLabel: { fontSize: 8, color: "#64748b", marginBottom: 2 },
        barTrack: { height: 14, backgroundColor: "#e2e8f0", borderRadius: 4, overflow: "hidden", flexDirection: "row" },
        barFill: { height: 14, borderRadius: 4, backgroundColor: brandColor },
        footer: { position: "absolute", bottom: 20, left: 40, right: 40, flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderTopWidth: 1, borderTopColor: "#e2e8f0", paddingTop: 8 },
        footerText: { fontSize: 7, color: "#94a3b8" },
    });

const getTrendColor = (trend: string) => {
    if (trend === "positivo") return { bg: "#dcfce7", text: "#166534" };
    if (trend === "negativo") return { bg: "#fef2f2", text: "#991b1b" };
    return { bg: "#fef3c7", text: "#92400e" };
};

const getTrendEmoji = (trend: string) => {
    if (trend === "positivo") return "???";
    if (trend === "negativo") return "???";
    return "???";
};

function ReportPDF({ data }: { data: ReportData }) {
    const styles = createStyles(data.agencyBrandColor);
    const { narrative, gaMetrics, metaMetrics } = data;
    const monthName = getMonthName(data.month);
    const trendStyle = getTrendColor(narrative.trend);
    const maxChannelSessions = Math.max(...gaMetrics.topChannels.map((c) => c.sessions), 1);

    return (
        <Document>
            <Page size="A4" style={[styles.page, styles.coverPage]}>
                <Text style={styles.coverTitle}>Reporte de Marketing</Text>
                <Text style={styles.coverSubtitle}>{data.agencyName}</Text>
                <Text style={styles.coverMonth}>{monthName} {data.year}</Text>
                <Text style={styles.coverClient}>{data.clientName}</Text>
                <View style={styles.footer}>
                    <Text style={[styles.footerText, { color: "rgba(255,255,255,0.6)" }]}>Generado por ReportPilot</Text>
                </View>
            </Page>

            <Page size="A4" style={styles.page}>
                <Text style={styles.sectionTitle}>Resumen Ejecutivo</Text>
                <View style={[styles.trendBadge, { backgroundColor: trendStyle.bg }]}>
                    <Text style={[styles.trendText, { color: trendStyle.text }]}>{getTrendEmoji(narrative.trend)} Tendencia: {narrative.trend}</Text>
                </View>
                <View style={[styles.insightCard, { borderLeftColor: data.agencyBrandColor }]}>
                    <Text style={styles.insightText}>{narrative.executiveSummary}</Text>
                </View>
                <View style={{ marginTop: 20 }}>
                    <Text style={[styles.insightTitle, { color: data.agencyBrandColor }]}>Rendimiento del Sitio Web</Text>
                    {narrative.gaHighlights.map((h, i) => (
                        <View key={`ga-${i}`} style={styles.bulletPoint}>
                            <Text style={styles.bullet}>&#8226;</Text>
                            <Text style={styles.bulletText}>{h}</Text>
                        </View>
                    ))}
                </View>
                <View style={{ marginTop: 16 }}>
                    <Text style={[styles.insightTitle, { color: data.agencyBrandColor }]}>Publicidad Pagada</Text>
                    {narrative.metaHighlights.map((h, i) => (
                        <View key={`meta-${i}`} style={styles.bulletPoint}>
                            <Text style={styles.bullet}>&#8226;</Text>
                            <Text style={styles.bulletText}>{h}</Text>
                        </View>
                    ))}
                </View>
                <View style={styles.footer}>
                    <Text style={styles.footerText}>{data.agencyName}</Text>
                    <Text style={styles.footerText}>Generado por ReportPilot</Text>
                </View>
            </Page>

            <Page size="A4" style={styles.page}>
                <Text style={styles.sectionTitle}>Rendimiento del Sitio Web</Text>
                <View style={styles.metricsRow}>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>Sesiones</Text><Text style={styles.metricValue}>{formatNumber(gaMetrics.sessions)}</Text></View>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>Usuarios</Text><Text style={styles.metricValue}>{formatNumber(gaMetrics.users)}</Text></View>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>Nuevos</Text><Text style={styles.metricValue}>{formatNumber(gaMetrics.newUsers)}</Text></View>
                </View>
                <View style={styles.metricsRow}>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>Rebote</Text><Text style={styles.metricValue}>{formatPercent(gaMetrics.bounceRate)}</Text></View>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>Duracion Prom.</Text><Text style={styles.metricValue}>{gaMetrics.avgSessionDuration.toFixed(0)}s</Text></View>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>Conversiones</Text><Text style={styles.metricValue}>{formatNumber(gaMetrics.conversions)}</Text></View>
                </View>
                <Text style={[styles.insightTitle, { marginTop: 20, color: data.agencyBrandColor }]}>Canales de Trafico</Text>
                {gaMetrics.topChannels.map((ch, i) => (
                    <View key={`ch-${i}`} style={styles.barContainer}>
                        <Text style={styles.barLabel}>{ch.channel} - {formatNumber(ch.sessions)} ({formatPercent(ch.percentage)})</Text>
                        <View style={styles.barTrack}>
                            <View style={[styles.barFill, { width: `${(ch.sessions / maxChannelSessions) * 100}%` }]} />
                        </View>
                    </View>
                ))}
                <Text style={[styles.insightTitle, { marginTop: 20, color: data.agencyBrandColor }]}>Paginas Mas Visitadas</Text>
                <View style={styles.tableHeader}>
                    <Text style={[styles.tableHeaderText, { flex: 2 }]}>Pagina</Text>
                    <Text style={[styles.tableHeaderText, { flex: 1, textAlign: "right" }]}>Vistas</Text>
                </View>
                {gaMetrics.topPages.map((p, i) => (
                    <View key={`pg-${i}`} style={styles.tableRow}>
                        <Text style={[styles.tableCell, { flex: 2 }]}>{p.pageTitle}</Text>
                        <Text style={[styles.tableCell, { flex: 1, textAlign: "right" }]}>{formatNumber(p.pageviews)}</Text>
                    </View>
                ))}
                <View style={styles.footer}>
                    <Text style={styles.footerText}>{data.agencyName}</Text>
                    <Text style={styles.footerText}>Generado por ReportPilot</Text>
                </View>
            </Page>

            <Page size="A4" style={styles.page}>
                <Text style={styles.sectionTitle}>Publicidad Pagada (Meta Ads)</Text>
                <View style={styles.metricsRow}>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>Gasto</Text><Text style={styles.metricValue}>{formatCurrency(metaMetrics.spend)}</Text></View>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>Impresiones</Text><Text style={styles.metricValue}>{formatNumber(metaMetrics.impressions)}</Text></View>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>Alcance</Text><Text style={styles.metricValue}>{formatNumber(metaMetrics.reach)}</Text></View>
                </View>
                <View style={styles.metricsRow}>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>Clics</Text><Text style={styles.metricValue}>{formatNumber(metaMetrics.clicks)}</Text></View>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>CTR</Text><Text style={styles.metricValue}>{formatPercent(metaMetrics.ctr)}</Text></View>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>ROAS</Text><Text style={styles.metricValue}>{metaMetrics.roas.toFixed(2)}x</Text></View>
                </View>
                <View style={styles.metricsRow}>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>CPC</Text><Text style={styles.metricValue}>{formatCurrency(metaMetrics.cpc)}</Text></View>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}>CPM</Text><Text style={styles.metricValue}>{formatCurrency(metaMetrics.cpm)}</Text></View>
                    <View style={styles.metricCard}><Text style={styles.metricLabel}> </Text><Text style={styles.metricValue}> </Text></View>
                </View>
                <Text style={[styles.insightTitle, { marginTop: 20, color: data.agencyBrandColor }]}>Top Campanas</Text>
                <View style={styles.tableHeader}>
                    <Text style={[styles.tableHeaderText, { flex: 2 }]}>Campana</Text>
                    <Text style={[styles.tableHeaderText, { flex: 1, textAlign: "right" }]}>Gasto</Text>
                    <Text style={[styles.tableHeaderText, { flex: 1, textAlign: "right" }]}>ROAS</Text>
                    <Text style={[styles.tableHeaderText, { flex: 1, textAlign: "right" }]}>Clics</Text>
                </View>
                {metaMetrics.topCampaigns.map((c, i) => (
                    <View key={`camp-${i}`} style={styles.tableRow}>
                        <Text style={[styles.tableCell, { flex: 2 }]}>{c.name}</Text>
                        <Text style={[styles.tableCell, { flex: 1, textAlign: "right" }]}>{formatCurrency(c.spend)}</Text>
                        <Text style={[styles.tableCell, { flex: 1, textAlign: "right" }]}>{c.roas.toFixed(2)}x</Text>
                        <Text style={[styles.tableCell, { flex: 1, textAlign: "right" }]}>{formatNumber(c.clicks)}</Text>
                    </View>
                ))}
                <View style={styles.footer}>
                    <Text style={styles.footerText}>{data.agencyName}</Text>
                    <Text style={styles.footerText}>Generado por ReportPilot</Text>
                </View>
            </Page>

            <Page size="A4" style={styles.page}>
                <Text style={styles.sectionTitle}>Analisis e Insights</Text>
                <View style={[styles.insightCard, { borderLeftColor: "#22c55e" }]}>
                    <Text style={[styles.insightTitle, { color: "#166534" }]}>Mayor Logro</Text>
                    <Text style={styles.insightText}>{narrative.topWin}</Text>
                </View>
                <View style={[styles.insightCard, { borderLeftColor: "#ef4444" }]}>
                    <Text style={[styles.insightTitle, { color: "#991b1b" }]}>Principal Desafio</Text>
                    <Text style={styles.insightText}>{narrative.mainChallenge}</Text>
                </View>
                <View style={[styles.insightCard, { borderLeftColor: data.agencyBrandColor }]}>
                    <Text style={[styles.insightTitle, { color: data.agencyBrandColor }]}>Recomendaciones para el Proximo Mes</Text>
                    {narrative.recommendations.map((rec, i) => (
                        <View key={`rec-${i}`} style={styles.bulletPoint}>
                            <Text style={styles.bullet}>{i + 1}.</Text>
                            <Text style={styles.bulletText}>{rec}</Text>
                        </View>
                    ))}
                </View>
                <View style={styles.footer}>
                    <Text style={styles.footerText}>{data.agencyName}</Text>
                    <Text style={styles.footerText}>Generado por ReportPilot</Text>
                </View>
            </Page>
        </Document>
    );
}

export async function generateReportPDF(data: ReportData): Promise<{ buffer: Buffer; url: string }> {
    const monthName = getMonthName(data.month);
    const pdfBuffer = await renderToBuffer(<ReportPDF data={data} />);
    const buffer = Buffer.from(pdfBuffer);
    const filename = `reports/${data.clientName.replace(/\s+/g, "-").toLowerCase()}-${monthName.toLowerCase()}-${data.year}.pdf`;
    const blob = await put(filename, buffer, { access: "public", contentType: "application/pdf" });
    return { buffer, url: blob.url };
}
