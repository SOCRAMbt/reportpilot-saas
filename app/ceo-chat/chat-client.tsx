"use client";

import { useState, useRef, useEffect } from "react";

interface ChatMessage {
    role: "user" | "ceo";
    message: string;
    timestamp: string;
}

export default function CEOChatClient() {
    const [messages, setMessages] = useState<ChatMessage[]>([
        {
            role: "ceo",
            message:
                "Hola Marcos 👋 Soy Alex Rivera, tu CEO Técnico. Tengo acceso al estado real del sistema en este momento. Preguntame lo que necesites: métricas, estrategia, estado de reportes, ideas de crecimiento... estoy acá para vos.",
            timestamp: new Date().toISOString(),
        },
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const sendMessage = async () => {
        if (!input.trim() || loading) return;

        const userMsg: ChatMessage = {
            role: "user",
            message: input.trim(),
            timestamp: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setLoading(true);

        try {
            const res = await fetch("/api/ceo-chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: userMsg.message,
                    history: messages.map((m) => ({ role: m.role, message: m.message })),
                }),
            });

            const data = await res.json();

            const ceoMsg: ChatMessage = {
                role: "ceo",
                message: data.response || "Error en la respuesta. Intentá de nuevo.",
                timestamp: new Date().toISOString(),
            };

            setMessages((prev) => [...prev, ceoMsg]);
        } catch {
            setMessages((prev) => [
                ...prev,
                {
                    role: "ceo",
                    message: "Error de conexión. Verificá que el servidor esté activo.",
                    timestamp: new Date().toISOString(),
                },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-80px)]">
            {/* Header */}
            <div className="border-b border-white/10 px-6 py-4 bg-gradient-to-r from-blue-600/10 to-purple-600/10">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
                        AR
                    </div>
                    <div>
                        <h2 className="font-bold text-white">Alex Rivera — CEO Técnico</h2>
                        <p className="text-xs text-gray-400">
                            Conectado al sistema en tiempo real · Gemini 1.5 Flash
                        </p>
                    </div>
                    <div className="ml-auto flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs text-green-400">Online</span>
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                {messages.map((msg, i) => (
                    <div
                        key={i}
                        className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                        <div
                            className={`max-w-[80%] rounded-2xl px-4 py-3 ${msg.role === "user"
                                ? "bg-blue-600 text-white"
                                : "bg-white/10 border border-white/10 text-gray-200"
                                }`}
                        >
                            {msg.role === "ceo" && (
                                <div className="text-xs text-blue-400 font-semibold mb-1">Alex Rivera</div>
                            )}
                            <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.message}</p>
                            <div
                                className={`text-[10px] mt-1 ${msg.role === "user" ? "text-blue-200" : "text-gray-500"
                                    }`}
                            >
                                {new Date(msg.timestamp).toLocaleTimeString("es-MX", {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                })}
                            </div>
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-white/10 border border-white/10 rounded-2xl px-4 py-3">
                            <div className="flex items-center gap-2">
                                <div className="flex gap-1">
                                    <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                                    <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                                    <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                                </div>
                                <span className="text-xs text-gray-500">Alex está analizando...</span>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="border-t border-white/10 px-6 py-4 bg-[#0a0e1a]/80 backdrop-blur">
                <div className="flex gap-3 items-end">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Preguntale algo a Alex Rivera..."
                        rows={1}
                        className="flex-1 px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none text-sm"
                    />
                    <button
                        onClick={sendMessage}
                        disabled={loading || !input.trim()}
                        className="px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors text-sm"
                    >
                        Enviar
                    </button>
                </div>
                <p className="text-[10px] text-gray-600 mt-2 text-center">
                    Alex tiene acceso de solo lectura al estado del sistema. No puede modificar código ni hacer deploys.
                </p>
            </div>
        </div>
    );
}
