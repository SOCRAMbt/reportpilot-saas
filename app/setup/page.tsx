"use client";

import { useState, useEffect } from "react";
import { CheckCircle, XCircle, Loader2, AlertTriangle } from "lucide-react";

interface EnvCheck {
    name: string;
    description: string;
    status: "checking" | "ok" | "missing" | "error";
}

const ENV_VARS: Array<{ name: string; description: string }> = [
    { name: "DATABASE_URL", description: "URL de la base de datos" },
    { name: "NEXTAUTH_SECRET", description: "Secreto para NextAuth.js" },
    { name: "NEXTAUTH_URL", description: "URL base de la aplicación" },
    { name: "GOOGLE_CLIENT_ID", description: "ID de cliente Google OAuth" },
    { name: "GOOGLE_CLIENT_SECRET", description: "Secreto de cliente Google OAuth" },
    { name: "META_APP_ID", description: "ID de la app de Meta/Facebook" },
    { name: "META_APP_SECRET", description: "Secreto de la app de Meta/Facebook" },
    { name: "GEMINI_API_KEY", description: "API Key de Gemini (Google AI)" },
    { name: "STRIPE_SECRET_KEY", description: "Clave secreta de Stripe" },
    { name: "STRIPE_WEBHOOK_SECRET", description: "Secreto del webhook de Stripe" },
    { name: "STRIPE_STARTER_PRICE_ID", description: "ID del precio Starter en Stripe" },
    { name: "STRIPE_GROWTH_PRICE_ID", description: "ID del precio Growth en Stripe" },
    { name: "STRIPE_AGENCY_PRICE_ID", description: "ID del precio Agency en Stripe" },
    { name: "RESEND_API_KEY", description: "API Key de Resend (email)" },
    { name: "CRON_SECRET", description: "Secreto para el endpoint cron" },
];

export default function SetupPage() {
    const [checks, setChecks] = useState<EnvCheck[]>(
        ENV_VARS.map((v) => ({ ...v, status: "checking" }))
    );
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function checkEnvVars() {
            try {
                const res = await fetch("/api/setup/check");
                const data = await res.json();

                setChecks(
                    ENV_VARS.map((v) => ({
                        ...v,
                        status: data.results?.[v.name] ? "ok" : "missing",
                    }))
                );
            } catch {
                setChecks(ENV_VARS.map((v) => ({ ...v, status: "error" })));
            } finally {
                setLoading(false);
            }
        }

        checkEnvVars();
    }, []);

    const configured = checks.filter((c) => c.status === "ok").length;
    const total = checks.length;

    return (
        <div className="min-h-screen bg-slate-950 text-white p-8">
            <div className="max-w-2xl mx-auto">
                <div className="flex items-center gap-3 mb-8">
                    <AlertTriangle className="w-6 h-6 text-amber-400" />
                    <h1 className="text-2xl font-bold">Configuración del Entorno</h1>
                </div>

                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-8">
                    <p className="text-amber-400 text-sm">
                        Esta página solo es accesible en modo desarrollo. Verifica que todas
                        las variables de entorno estén configuradas correctamente.
                    </p>
                </div>

                <div className="mb-6">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-slate-400">Progreso</span>
                        <span className="text-sm font-medium text-white">{configured}/{total}</span>
                    </div>
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-green-500 rounded-full transition-all"
                            style={{ width: `${(configured / total) * 100}%` }}
                        />
                    </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                    {checks.map((check, i) => (
                        <div
                            key={check.name}
                            className={`flex items-center justify-between px-5 py-3.5 ${i < checks.length - 1 ? "border-b border-slate-800" : ""
                                }`}
                        >
                            <div>
                                <code className="text-sm font-mono text-white">{check.name}</code>
                                <p className="text-xs text-slate-500 mt-0.5">{check.description}</p>
                            </div>
                            <div>
                                {loading ? (
                                    <Loader2 className="w-5 h-5 text-slate-500 animate-spin" />
                                ) : check.status === "ok" ? (
                                    <CheckCircle className="w-5 h-5 text-green-400" />
                                ) : (
                                    <XCircle className="w-5 h-5 text-red-400" />
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                {!loading && configured === total && (
                    <div className="mt-6 bg-green-500/10 border border-green-500/20 rounded-xl p-4 text-center">
                        <CheckCircle className="w-8 h-8 text-green-400 mx-auto mb-2" />
                        <p className="text-green-400 font-medium">
                            ¡Todas las variables están configuradas! ✅
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
