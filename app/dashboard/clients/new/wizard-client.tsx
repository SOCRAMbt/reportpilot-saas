"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, ArrowLeft, ArrowRight, Loader2 } from "lucide-react";

interface WizardProps {
    agencyId: string;
}

export function NewClientWizard({ agencyId }: WizardProps) {
    const router = useRouter();
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);

    // Step 1
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");

    // Step 2
    const [gaPropertyId, setGaPropertyId] = useState("");

    // Step 3
    const [metaAdAccountId, setMetaAdAccountId] = useState("");

    const steps = [
        { num: 1, label: "Información" },
        { num: 2, label: "Google Analytics" },
        { num: 3, label: "Meta Ads" },
        { num: 4, label: "Confirmar" },
    ];

    const handleSubmit = async () => {
        setLoading(true);
        try {
            const res = await fetch("/api/clients", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    agencyId,
                    name,
                    email,
                    gaPropertyId: gaPropertyId || null,
                    metaAdAccountId: metaAdAccountId || null,
                }),
            });

            if (res.ok) {
                const data = await res.json();
                router.push(`/dashboard/clients/${data.id}`);
            } else {
                const error = await res.json();
                alert(`Error: ${error.message || "Error al crear cliente"}`);
            }
        } catch {
            alert("Error de conexión");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-8">
            {/* Steps indicator */}
            <div className="flex items-center justify-between">
                {steps.map((s, i) => (
                    <div key={s.num} className="flex items-center">
                        <div className="flex items-center gap-2">
                            <div
                                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${step > s.num
                                        ? "bg-green-500 text-white"
                                        : step === s.num
                                            ? "bg-blue-600 text-white"
                                            : "bg-slate-800 text-slate-500"
                                    }`}
                            >
                                {step > s.num ? <Check className="w-4 h-4" /> : s.num}
                            </div>
                            <span className="text-sm text-slate-400 hidden sm:inline">{s.label}</span>
                        </div>
                        {i < steps.length - 1 && (
                            <div className={`w-8 sm:w-16 h-0.5 mx-2 ${step > s.num ? "bg-green-500" : "bg-slate-800"}`} />
                        )}
                    </div>
                ))}
            </div>

            {/* Step content */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 md:p-8">
                {step === 1 && (
                    <div className="space-y-5">
                        <div>
                            <h2 className="text-lg font-semibold text-white mb-1">Información del Cliente</h2>
                            <p className="text-sm text-slate-400">Ingresa los datos básicos del cliente</p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Nombre</label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="Ej: Restaurante La Buena Mesa"
                                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">
                                Email (para enviar reportes)
                            </label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="cliente@ejemplo.com"
                                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>
                    </div>
                )}

                {step === 2 && (
                    <div className="space-y-5">
                        <div>
                            <h2 className="text-lg font-semibold text-white mb-1">Google Analytics</h2>
                            <p className="text-sm text-slate-400">
                                Conecta la propiedad de Google Analytics del cliente
                            </p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">
                                ID de Propiedad (GA4)
                            </label>
                            <input
                                type="text"
                                value={gaPropertyId}
                                onChange={(e) => setGaPropertyId(e.target.value)}
                                placeholder="Ej: 123456789"
                                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                            <p className="mt-2 text-xs text-slate-500">
                                Encuéntralo en Google Analytics → Administración → Configuración de propiedad → ID de Propiedad
                            </p>
                        </div>
                        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                            <p className="text-sm text-blue-400">
                                💡 Asegúrate de que la cuenta de Google con la que iniciaste sesión tiene acceso de lectura a esta propiedad.
                            </p>
                        </div>
                    </div>
                )}

                {step === 3 && (
                    <div className="space-y-5">
                        <div>
                            <h2 className="text-lg font-semibold text-white mb-1">Meta Ads</h2>
                            <p className="text-sm text-slate-400">
                                Conecta la cuenta de Meta Ads del cliente
                            </p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">
                                ID de Cuenta Publicitaria
                            </label>
                            <input
                                type="text"
                                value={metaAdAccountId}
                                onChange={(e) => setMetaAdAccountId(e.target.value)}
                                placeholder="Ej: 1234567890"
                                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                            <p className="mt-2 text-xs text-slate-500">
                                Encuéntralo en Meta Business Suite → Configuración → Información de la cuenta publicitaria
                            </p>
                        </div>
                        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                            <p className="text-sm text-blue-400">
                                💡 Puedes omitir este paso si el cliente no utiliza Meta Ads.
                            </p>
                        </div>
                    </div>
                )}

                {step === 4 && (
                    <div className="space-y-5">
                        <div>
                            <h2 className="text-lg font-semibold text-white mb-1">Confirmar</h2>
                            <p className="text-sm text-slate-400">Revisa la información antes de crear el cliente</p>
                        </div>
                        <div className="space-y-3">
                            <div className="flex justify-between py-3 border-b border-slate-800">
                                <span className="text-slate-400">Nombre</span>
                                <span className="text-white font-medium">{name}</span>
                            </div>
                            <div className="flex justify-between py-3 border-b border-slate-800">
                                <span className="text-slate-400">Email</span>
                                <span className="text-white font-medium">{email}</span>
                            </div>
                            <div className="flex justify-between py-3 border-b border-slate-800">
                                <span className="text-slate-400">Google Analytics</span>
                                <span className="text-white font-medium">{gaPropertyId || "No conectado"}</span>
                            </div>
                            <div className="flex justify-between py-3">
                                <span className="text-slate-400">Meta Ads</span>
                                <span className="text-white font-medium">{metaAdAccountId || "No conectado"}</span>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Navigation buttons */}
            <div className="flex justify-between">
                <button
                    onClick={() => setStep((s) => Math.max(1, s - 1))}
                    disabled={step === 1}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Anterior
                </button>

                {step < 4 ? (
                    <button
                        onClick={() => setStep((s) => s + 1)}
                        disabled={step === 1 && (!name || !email)}
                        className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                    >
                        Siguiente
                        <ArrowRight className="w-4 h-4" />
                    </button>
                ) : (
                    <button
                        onClick={handleSubmit}
                        disabled={loading || !name || !email}
                        className="flex items-center gap-2 px-6 py-2.5 bg-green-600 hover:bg-green-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
                    >
                        {loading ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Check className="w-4 h-4" />
                        )}
                        Crear Cliente
                    </button>
                )}
            </div>
        </div>
    );
}
