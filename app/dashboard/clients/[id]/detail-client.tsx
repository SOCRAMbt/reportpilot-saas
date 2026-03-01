"use client";

import { useState } from "react";
import Link from "next/link";
import {
    ArrowLeft,
    Download,
    Zap,
    Loader2,
    CheckCircle,
    XCircle,
    Clock,
    Plug,
} from "lucide-react";
import { getMonthName } from "@/lib/utils";

interface ReportData {
    id: string;
    month: number;
    year: number;
    status: string;
    pdfUrl: string | null;
    sentAt: string | null;
    createdAt: string;
}

interface IntegrationData {
    id: string;
    type: string;
    expiresAt: string | null;
}

interface ClientData {
    id: string;
    name: string;
    email: string;
    active: boolean;
    gaPropertyId: string | null;
    metaAdAccountId: string | null;
    createdAt: string;
    reports: ReportData[];
    integrations: IntegrationData[];
}

export function ClientDetailClient({ client }: { client: ClientData }) {
    const [generating, setGenerating] = useState(false);

    const handleGenerate = async () => {
        setGenerating(true);
        try {
            const res = await fetch("/api/reports/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ clientId: client.id }),
            });
            const data = await res.json();
            if (data.success) {
                alert("✅ Reporte generado y enviado exitosamente");
                window.location.reload();
            } else {
                alert(`❌ Error: ${data.error || "Error desconocido"}`);
            }
        } catch {
            alert("❌ Error de conexión");
        } finally {
            setGenerating(false);
        }
    };

    const statusIcon = (status: string) => {
        switch (status) {
            case "sent": return <CheckCircle className="w-4 h-4 text-green-400" />;
            case "failed": return <XCircle className="w-4 h-4 text-red-400" />;
            default: return <Clock className="w-4 h-4 text-amber-400" />;
        }
    };

    const statusLabel = (status: string) => {
        switch (status) {
            case "sent": return "Enviado";
            case "failed": return "Error";
            case "generating": return "Generando";
            default: return "Pendiente";
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex items-center gap-4">
                    <Link
                        href="/dashboard"
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div>
                        <h1 className="text-2xl font-bold text-white">{client.name}</h1>
                        <p className="text-slate-400 text-sm">{client.email}</p>
                    </div>
                </div>

                <button
                    onClick={handleGenerate}
                    disabled={generating}
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
                >
                    {generating ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                        <Zap className="w-4 h-4" />
                    )}
                    Generar Reporte Ahora
                </button>
            </div>

            {/* Integration Status */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <Plug className="w-5 h-5 text-blue-400" />
                        <h3 className="font-medium text-white">Google Analytics</h3>
                    </div>
                    {client.gaPropertyId ? (
                        <div>
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-400">
                                <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                                Conectado
                            </span>
                            <p className="mt-2 text-xs text-slate-500">
                                Propiedad: {client.gaPropertyId}
                            </p>
                        </div>
                    ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-700 text-slate-400">
                            No conectado
                        </span>
                    )}
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <Plug className="w-5 h-5 text-purple-400" />
                        <h3 className="font-medium text-white">Meta Ads</h3>
                    </div>
                    {client.metaAdAccountId ? (
                        <div>
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-400">
                                <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                                Conectado
                            </span>
                            <p className="mt-2 text-xs text-slate-500">
                                Cuenta: {client.metaAdAccountId}
                            </p>
                        </div>
                    ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-700 text-slate-400">
                            No conectado
                        </span>
                    )}
                </div>
            </div>

            {/* Reports Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-800">
                    <h2 className="text-lg font-semibold text-white">Historial de Reportes</h2>
                </div>

                {client.reports.length === 0 ? (
                    <div className="px-6 py-12 text-center">
                        <p className="text-slate-400">No hay reportes generados aún</p>
                        <p className="text-slate-500 text-sm mt-1">
                            Haz clic en &quot;Generar Reporte Ahora&quot; para crear el primer reporte
                        </p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                                    <th className="px-6 py-3">Periodo</th>
                                    <th className="px-6 py-3">Estado</th>
                                    <th className="px-6 py-3">Enviado</th>
                                    <th className="px-6 py-3 text-right">Acciones</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                                {client.reports.map((report) => (
                                    <tr key={report.id} className="hover:bg-slate-800/50 transition-colors">
                                        <td className="px-6 py-4 text-white font-medium">
                                            {getMonthName(report.month)} {report.year}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2 text-sm">
                                                {statusIcon(report.status)}
                                                <span className="text-slate-300">{statusLabel(report.status)}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-slate-400">
                                            {report.sentAt
                                                ? new Date(report.sentAt).toLocaleDateString("es-MX")
                                                : "—"}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            {report.pdfUrl && (
                                                <a
                                                    href={report.pdfUrl}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 text-xs font-medium rounded-lg transition-colors"
                                                >
                                                    <Download className="w-3.5 h-3.5" />
                                                    Descargar PDF
                                                </a>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
