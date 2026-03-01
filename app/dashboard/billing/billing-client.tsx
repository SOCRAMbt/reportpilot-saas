"use client";

import { useState } from "react";
import { Check, Loader2, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

const plans = [
    {
        id: "starter",
        name: "Starter",
        price: 79,
        maxClients: 1,
        priceId: process.env.NEXT_PUBLIC_STRIPE_STARTER_PRICE_ID || "starter",
        features: [
            "1 cliente",
            "Reportes automáticos mensuales",
            "Google Analytics + Meta Ads",
            "Insights con IA",
            "Soporte por email",
        ],
    },
    {
        id: "growth",
        name: "Growth",
        price: 129,
        maxClients: 5,
        priceId: process.env.NEXT_PUBLIC_STRIPE_GROWTH_PRICE_ID || "growth",
        popular: true,
        features: [
            "Hasta 5 clientes",
            "Todo lo de Starter",
            "Marca personalizada",
            "Soporte prioritario",
        ],
    },
    {
        id: "agency",
        name: "Agency",
        price: 199,
        maxClients: 999,
        priceId: process.env.NEXT_PUBLIC_STRIPE_AGENCY_PRICE_ID || "agency",
        features: [
            "Clientes ilimitados",
            "Todo lo de Growth",
            "Logo personalizado en reportes",
            "API access",
            "Soporte dedicado",
        ],
    },
];

interface BillingProps {
    currentPlan: string;
    clientCount: number;
}

export function BillingClient({ currentPlan, clientCount }: BillingProps) {
    const [loading, setLoading] = useState<string | null>(null);

    const currentPlanConfig = plans.find((p) => p.id === currentPlan);
    const maxClients = currentPlanConfig?.maxClients || 0;

    const handleSubscribe = async (priceId: string) => {
        setLoading(priceId);
        try {
            const res = await fetch("/api/stripe/create-checkout", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ priceId }),
            });
            const data = await res.json();
            if (data.url) {
                window.location.href = data.url;
            } else {
                alert("Error al crear la sesión de pago");
            }
        } catch {
            alert("Error de conexión");
        } finally {
            setLoading(null);
        }
    };

    return (
        <div className="max-w-5xl mx-auto space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-white">Facturación</h1>
                <p className="mt-1 text-slate-400">Gestiona tu plan y facturación</p>
            </div>

            {/* Current Plan */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div>
                        <p className="text-sm text-slate-500">Plan actual</p>
                        <p className="text-xl font-bold text-white mt-0.5">
                            {currentPlanConfig?.name || "Sin plan"}
                        </p>
                    </div>
                    <div>
                        <p className="text-sm text-slate-500">Uso de clientes</p>
                        <div className="flex items-center gap-3 mt-1">
                            <div className="w-32 h-2 bg-slate-800 rounded-full overflow-hidden">
                                <div
                                    className={cn(
                                        "h-full rounded-full transition-all",
                                        clientCount >= maxClients ? "bg-red-500" : "bg-blue-500"
                                    )}
                                    style={{ width: `${maxClients > 0 ? Math.min((clientCount / maxClients) * 100, 100) : 0}%` }}
                                />
                            </div>
                            <span className="text-sm text-slate-300 font-medium">
                                {clientCount} / {maxClients === 999 ? "∞" : maxClients}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Plans Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {plans.map((plan) => (
                    <div
                        key={plan.id}
                        className={cn(
                            "relative bg-slate-900 border rounded-xl p-6 transition-all",
                            plan.popular
                                ? "border-blue-500 shadow-lg shadow-blue-500/10"
                                : "border-slate-800",
                            currentPlan === plan.id && "ring-2 ring-green-500"
                        )}
                    >
                        {plan.popular && (
                            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                                <span className="px-3 py-1 bg-blue-600 text-white text-xs font-medium rounded-full">
                                    Más popular
                                </span>
                            </div>
                        )}

                        <div className="text-center mb-6">
                            <h3 className="text-lg font-semibold text-white">{plan.name}</h3>
                            <div className="mt-2">
                                <span className="text-3xl font-bold text-white">${plan.price}</span>
                                <span className="text-slate-500">/mes</span>
                            </div>
                        </div>

                        <ul className="space-y-3 mb-6">
                            {plan.features.map((feature, i) => (
                                <li key={i} className="flex items-center gap-2 text-sm text-slate-300">
                                    <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
                                    {feature}
                                </li>
                            ))}
                        </ul>

                        {currentPlan === plan.id ? (
                            <div className="w-full py-2.5 text-center text-sm font-medium text-green-400 bg-green-500/10 rounded-lg">
                                Plan actual
                            </div>
                        ) : (
                            <button
                                onClick={() => handleSubscribe(plan.priceId)}
                                disabled={loading === plan.priceId}
                                className={cn(
                                    "w-full flex items-center justify-center gap-2 py-2.5 text-sm font-medium rounded-lg transition-colors cursor-pointer",
                                    plan.popular
                                        ? "bg-blue-600 hover:bg-blue-500 text-white"
                                        : "bg-slate-800 hover:bg-slate-700 text-white"
                                )}
                            >
                                {loading === plan.priceId ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Zap className="w-4 h-4" />
                                )}
                                {currentPlan === "free" ? "Suscribirse" : "Cambiar plan"}
                            </button>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
