import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export function getMonthName(month: number): string {
    const months = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ];
    return months[month - 1] || "Desconocido";
}

export function getLastMonthRange(): { startDate: string; endDate: string; month: number; year: number } {
    const now = new Date();
    const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);

    return {
        startDate: lastMonth.toISOString().split("T")[0],
        endDate: lastMonthEnd.toISOString().split("T")[0],
        month: lastMonth.getMonth() + 1,
        year: lastMonth.getFullYear(),
    };
}

export function formatCurrency(amount: number): string {
    return new Intl.NumberFormat("es-MX", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 2,
    }).format(amount);
}

export function formatNumber(num: number): string {
    return new Intl.NumberFormat("es-MX").format(num);
}

export function formatPercent(num: number): string {
    return `${num.toFixed(2)}%`;
}
