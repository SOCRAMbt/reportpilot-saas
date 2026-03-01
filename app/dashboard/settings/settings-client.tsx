"use client";

import { useState } from "react";
import { Loader2, Save, Palette } from "lucide-react";

interface AgencyData {
    id: string;
    name: string;
    brandColor: string;
    logoUrl: string | null;
}

export function SettingsClient({ agency }: { agency: AgencyData }) {
    const [name, setName] = useState(agency.name);
    const [brandColor, setBrandColor] = useState(agency.brandColor);
    const [logoUrl, setLogoUrl] = useState(agency.logoUrl || "");
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    const handleSave = async () => {
        setSaving(true);
        setSaved(false);
        try {
            const res = await fetch("/api/agency", {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, brandColor, logoUrl: logoUrl || null }),
            });
            if (res.ok) {
                setSaved(true);
                setTimeout(() => setSaved(false), 3000);
            } else {
                alert("Error al guardar");
            }
        } catch {
            alert("Error de conexión");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-white">Configuración</h1>
                <p className="mt-1 text-slate-400">Personaliza tu agencia y marca</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 md:p-8 space-y-6">
                {/* Agency Name */}
                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        Nombre de la Agencia
                    </label>
                    <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                </div>

                {/* Brand Color */}
                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        <Palette className="w-4 h-4 inline mr-1" />
                        Color de Marca
                    </label>
                    <div className="flex items-center gap-3">
                        <input
                            type="color"
                            value={brandColor}
                            onChange={(e) => setBrandColor(e.target.value)}
                            className="w-12 h-12 rounded-lg cursor-pointer border border-slate-700 bg-slate-800 p-1"
                        />
                        <input
                            type="text"
                            value={brandColor}
                            onChange={(e) => setBrandColor(e.target.value)}
                            className="flex-1 px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="#3B82F6"
                        />
                    </div>
                    <p className="mt-2 text-xs text-slate-500">
                        Este color se usará en los reportes PDF y emails
                    </p>
                </div>

                {/* Logo URL */}
                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        URL del Logo
                    </label>
                    <input
                        type="url"
                        value={logoUrl}
                        onChange={(e) => setLogoUrl(e.target.value)}
                        placeholder="https://ejemplo.com/logo.png"
                        className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <p className="mt-2 text-xs text-slate-500">
                        Se mostrará en los reportes y emails. Recomendado: PNG con fondo transparente.
                    </p>
                    {logoUrl && (
                        <div className="mt-3 p-4 bg-slate-800 rounded-lg">
                            <p className="text-xs text-slate-500 mb-2">Vista previa:</p>
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                                src={logoUrl}
                                alt="Logo preview"
                                className="max-h-16 max-w-48 object-contain"
                                onError={(e) => {
                                    (e.target as HTMLImageElement).style.display = "none";
                                }}
                            />
                        </div>
                    )}
                </div>

                {/* Preview */}
                <div className="pt-4 border-t border-slate-800">
                    <p className="text-sm font-medium text-slate-300 mb-3">Vista Previa del Reporte</p>
                    <div
                        className="rounded-lg p-6 text-white text-center"
                        style={{ backgroundColor: brandColor }}
                    >
                        <h3 className="text-xl font-bold">{name || "Tu Agencia"}</h3>
                        <p className="text-sm opacity-80 mt-1">Reporte mensual de marketing</p>
                    </div>
                </div>

                {/* Save Button */}
                <div className="flex items-center gap-3 pt-2">
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
                    >
                        {saving ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Save className="w-4 h-4" />
                        )}
                        Guardar Cambios
                    </button>
                    {saved && (
                        <span className="text-green-400 text-sm">✓ Cambios guardados</span>
                    )}
                </div>
            </div>
        </div>
    );
}
