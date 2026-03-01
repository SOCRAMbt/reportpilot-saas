"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import { cn } from "@/lib/utils";
import {
    LayoutDashboard,
    Users,
    Settings,
    CreditCard,
    LogOut,
    BarChart3,
    Menu,
    X,
} from "lucide-react";
import { useState } from "react";

const navItems = [
    { href: "/dashboard", label: "Panel", icon: LayoutDashboard },
    { href: "/dashboard/clients/new", label: "Nuevo Cliente", icon: Users },
    { href: "/dashboard/settings", label: "Configuración", icon: Settings },
    { href: "/dashboard/billing", label: "Facturación", icon: CreditCard },
];

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const [sidebarOpen, setSidebarOpen] = useState(false);

    return (
        <div className="min-h-screen bg-slate-950">
            {/* Mobile overlay */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-40 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside
                className={cn(
                    "fixed top-0 left-0 z-50 h-full w-64 bg-slate-900 border-r border-slate-800 transition-transform duration-300 lg:translate-x-0",
                    sidebarOpen ? "translate-x-0" : "-translate-x-full"
                )}
            >
                <div className="flex flex-col h-full">
                    {/* Logo */}
                    <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-800">
                        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                            <BarChart3 className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-lg font-bold text-white">
                            Report<span className="text-blue-400">Pilot</span>
                        </span>
                        <button
                            className="ml-auto lg:hidden text-slate-400 hover:text-white"
                            onClick={() => setSidebarOpen(false)}
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 px-3 py-4 space-y-1">
                        {navItems.map((item) => {
                            const isActive =
                                item.href === "/dashboard"
                                    ? pathname === "/dashboard"
                                    : pathname.startsWith(item.href);

                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    onClick={() => setSidebarOpen(false)}
                                    className={cn(
                                        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                                        isActive
                                            ? "bg-blue-600/20 text-blue-400"
                                            : "text-slate-400 hover:text-white hover:bg-slate-800"
                                    )}
                                >
                                    <item.icon className="w-5 h-5" />
                                    {item.label}
                                </Link>
                            );
                        })}
                    </nav>

                    {/* Sign out */}
                    <div className="px-3 py-4 border-t border-slate-800">
                        <button
                            onClick={() => signOut({ callbackUrl: "/" })}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors w-full cursor-pointer"
                        >
                            <LogOut className="w-5 h-5" />
                            Cerrar sesión
                        </button>
                    </div>
                </div>
            </aside>

            {/* Main content */}
            <div className="lg:pl-64">
                {/* Top bar (mobile) */}
                <header className="sticky top-0 z-30 flex items-center gap-4 px-4 py-3 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800 lg:hidden">
                    <button
                        onClick={() => setSidebarOpen(true)}
                        className="text-slate-400 hover:text-white"
                    >
                        <Menu className="w-6 h-6" />
                    </button>
                    <span className="text-lg font-bold text-white">
                        Report<span className="text-blue-400">Pilot</span>
                    </span>
                </header>

                <main className="p-4 md:p-6 lg:p-8">{children}</main>
            </div>
        </div>
    );
}
