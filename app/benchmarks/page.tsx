"use client";

import { useState, useEffect } from "react";

interface BenchmarkEntry {
    name: string;
    avgCPC: number;
    avgROAS: number;
    avgCTR: number;
    country: string;
}

export default function BenchmarksPage() {
    const [benchmarks, setBenchmarks] = useState<BenchmarkEntry[]>([]);
    const [email, setEmail] = useState("");
    const [submitted, setSubmitted] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("/api/benchmarks")
            .then((r) => r.json())
            .then((data) => {
                if (data.industries) setBenchmarks(data.industries);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email) return;
        const res = await fetch("/api/benchmarks", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email }),
        });
        if (res.ok) setSubmitted(true);
    };

    return (
        <div className="min-h-screen bg-[#0a0e1a] text-white">
            {/* Hero */}
            <div className="max-w-5xl mx-auto px-6 py-20">
                <div className="text-center mb-16">
                    <span className="inline-block px-3 py-1 text-xs font-medium bg-blue-500/20 text-blue-400 rounded-full mb-4">
                        Datos actualizados · Marzo 2026
                    </span>
                    <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-white via-blue-200 to-blue-400 bg-clip-text text-transparent">
                        Benchmarks de Marketing Digital — LatAm
                    </h1>
                    <p className="text-lg text-gray-400 max-w-2xl mx-auto">
                        Datos reales y anonimizados de agencias que usan ReportPilot.
                        Compará el rendimiento de tus campañas contra la industria.
                    </p>
                </div>

                {/* Benchmark Table */}
                <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden mb-16">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-white/10">
                                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Industria</th>
                                    <th className="px-6 py-4 text-center text-sm font-semibold text-gray-300">País</th>
                                    <th className="px-6 py-4 text-center text-sm font-semibold text-gray-300">CPC Promedio</th>
                                    <th className="px-6 py-4 text-center text-sm font-semibold text-gray-300">ROAS Promedio</th>
                                    <th className="px-6 py-4 text-center text-sm font-semibold text-gray-300">CTR Promedio</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading ? (
                                    <tr>
                                        <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                                            Cargando benchmarks...
                                        </td>
                                    </tr>
                                ) : (
                                    benchmarks.map((b, i) => (
                                        <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                            <td className="px-6 py-4 font-medium">{b.name}</td>
                                            <td className="px-6 py-4 text-center">
                                                <span className="inline-block px-2 py-0.5 text-xs bg-blue-500/20 text-blue-300 rounded">
                                                    {b.country}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-center font-mono text-green-400">
                                                ${b.avgCPC.toFixed(2)}
                                            </td>
                                            <td className="px-6 py-4 text-center font-mono text-yellow-400">
                                                {b.avgROAS.toFixed(1)}x
                                            </td>
                                            <td className="px-6 py-4 text-center font-mono text-purple-400">
                                                {b.avgCTR.toFixed(1)}%
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Lead Magnet Form */}
                <div className="max-w-lg mx-auto bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-2xl p-8 text-center">
                    {submitted ? (
                        <div>
                            <div className="text-4xl mb-4">🎉</div>
                            <h3 className="text-xl font-bold mb-2">¡Listo!</h3>
                            <p className="text-gray-300">
                                Te enviaremos el reporte completo de benchmarks por industria a tu correo.
                            </p>
                        </div>
                    ) : (
                        <>
                            <h3 className="text-xl font-bold mb-2">
                                ¿Querés el reporte detallado completo?
                            </h3>
                            <p className="text-gray-400 mb-6 text-sm">
                                Incluye desglose por sub-industria, tendencias mensuales y recomendaciones de la IA.
                            </p>
                            <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
                                <input
                                    type="email"
                                    placeholder="tu@agencia.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="flex-1 px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    required
                                />
                                <button
                                    type="submit"
                                    className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-colors whitespace-nowrap"
                                >
                                    Enviar reporte gratis
                                </button>
                            </form>
                        </>
                    )}
                </div>

                {/* CTA */}
                <div className="text-center mt-16">
                    <p className="text-gray-500 text-sm mb-4">
                        Estos datos son generados por la IA de ReportPilot a partir de cuentas reales.
                    </p>
                    <a
                        href="/login"
                        className="inline-flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl text-white font-medium transition-colors"
                    >
                        Probá ReportPilot gratis 14 días →
                    </a>
                </div>
            </div>

            {/* Footer */}
            <footer className="border-t border-white/10 py-8 text-center text-gray-600 text-sm">
                © {new Date().getFullYear()} ReportPilot · Benchmarks generados con IA
            </footer>
        </div>
    );
}
