"use client";

import { useState } from "react";
import Link from "next/link";
import { Users, FileText, Calendar, Zap, Loader2, ExternalLink } from "lucide-react";
import { getMonthName } from "@/lib/utils";

interface ClientData {
    id: string;
    name: string;
    email: string;
    active: boolean;
    lastReport: {
        status: string;
        sentAt: string | null;
        month: number;
        year: number;
    } | null;
}

interface DashboardProps {
    stats: {
        totalClients: number;
        activeClients: number;
        reportsThisMonth: number;
        nextReportDate: string;
    };
    clients: ClientData[];
}

export function DashboardClient({ stats, clients }: DashboardProps) {
    const [generating, setGenerating] = useState<string | null>(null);

    const handleGenerate = async (clientId: string) => {
        setGenerating(clientId);
        try {
            const res = await fetch("/api/reports/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ clientId }),
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
            setGenerating(null);
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-2xl md:text-3xl font-bold text-white">Panel de Control</h1>
                <p className="mt-1 text-slate-400">Gestiona tus clientes y reportes</p>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    icon={<Users className="w-5 h-5" />}
                    label="Total Clientes"
                    value={stats.totalClients.toString()}
                    color="blue"
                />
                <StatCard
                    icon={<Zap className="w-5 h-5" />}
                    label="Clientes Activos"
                    value={stats.activeClients.toString()}
                    color="green"
                />
                <StatCard
                    icon={<FileText className="w-5 h-5" />}
                    label="Reportes este Mes"
                    value={stats.reportsThisMonth.toString()}
                    color="purple"
                />
                <StatCard
                    icon={<Calendar className="w-5 h-5" />}
                    label="Próximo Reporte"
                    value={stats.nextReportDate}
                    color="amber"
                />
            </div>

            {/* Clients Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
                    <h2 className="text-lg font-semibold text-white">Clientes</h2>
                    <Link
                        href="/dashboard/clients/new"
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                        + Nuevo Cliente
                    </Link>
                </div>

                {clients.length === 0 ? (
                    <div className="px-6 py-16 text-center">
                        <Users className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                        <p className="text-slate-400 text-lg">No tienes clientes aún</p>
                        <p className="text-slate-500 text-sm mt-1">
                            Agrega tu primer cliente para comenzar a generar reportes
                        </p>
                        <Link
                            href="/dashboard/clients/new"
                            className="inline-block mt-4 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
                        >
                            Agregar Cliente
                        </Link>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                                    <th className="px-6 py-3">Cliente</th>
                                    <th className="px-6 py-3">Estado</th>
                                    <th className="px-6 py-3">Último Reporte</th>
                                    <th className="px-6 py-3 text-right">Acciones</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                                {clients.map((client) => (
                                    <tr
                                        key={client.id}
                                        className="hover:bg-slate-800/50 transition-colors"
                                    >
                                        <td className="px-6 py-4">
                                            <Link
                                                href={`/dashboard/clients/${client.id}`}
                                                className="hover:text-blue-400 transition-colors"
                                            >
                                                <div className="font-medium text-white">{client.name}</div>
                                                <div className="text-sm text-slate-500">{client.email}</div>
                                            </Link>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span
                                                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${client.active
                                                        ? "bg-green-500/10 text-green-400"
                                                        : "bg-slate-700 text-slate-400"
                                                    }`}
                                            >
                                                <span
                                                    className={`w-1.5 h-1.5 rounded-full ${client.active ? "bg-green-400" : "bg-slate-500"
                                                        }`}
                                                />
                                                {client.active ? "Activo" : "Inactivo"}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-slate-400">
                                            {client.lastReport ? (
                                                <span>
                                                    {getMonthName(client.lastReport.month)} {client.lastReport.year}
                                                    {client.lastReport.status === "sent" && (
                                                        <span className="ml-2 text-green-400">✓ Enviado</span>
                                                    )}
                                                    {client.lastReport.status === "failed" && (
                                                        <span className="ml-2 text-red-400">✗ Error</span>
                                                    )}
                                                </span>
                                            ) : (
                                                <span className="text-slate-600">Sin reportes</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                <button
                                                    onClick={() => handleGenerate(client.id)}
                                                    disabled={generating === client.id}
                                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 text-xs font-medium rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
                                                >
                                                    {generating === client.id ? (
                                                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                    ) : (
                                                        <Zap className="w-3.5 h-3.5" />
                                                    )}
                                                    Generar reporte
                                                </button>
                                                <Link
                                                    href={`/dashboard/clients/${client.id}`}
                                                    className="inline-flex items-center gap-1 px-3 py-1.5 text-slate-400 hover:text-white text-xs font-medium rounded-lg hover:bg-slate-800 transition-colors"
                                                >
                                                    <ExternalLink className="w-3.5 h-3.5" />
                                                    Ver
                                                </Link>
                                            </div>
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

function StatCard({
    icon,
    label,
    value,
    color,
}: {
    icon: React.ReactNode;
    label: string;
    value: string;
    color: "blue" | "green" | "purple" | "amber";
}) {
    const colorClasses = {
        blue: "bg-blue-500/10 text-blue-400 border-blue-500/20",
        green: "bg-green-500/10 text-green-400 border-green-500/20",
        purple: "bg-purple-500/10 text-purple-400 border-purple-500/20",
        amber: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    };

    const iconBg = {
        blue: "bg-blue-500/20",
        green: "bg-green-500/20",
        purple: "bg-purple-500/20",
        amber: "bg-amber-500/20",
    };

    return (
        <div
            className={`p-5 rounded-xl border ${colorClasses[color]} backdrop-blur-sm`}
        >
            <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${iconBg[color]}`}>{icon}</div>
                <div>
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                        {label}
                    </p>
                    <p className="text-xl font-bold text-white mt-0.5">{value}</p>
                </div>
            </div>
        </div>
    );
}
