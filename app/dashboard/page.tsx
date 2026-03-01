import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { redirect } from "next/navigation";
import { getMonthName } from "@/lib/utils";
import { DashboardClient } from "./dashboard-client";

export default async function DashboardPage() {
    const session = await auth();
    if (!session?.user?.id) redirect("/login");

    // Get or create agency
    let agency = await prisma.agency.findUnique({
        where: { userId: session.user.id },
        include: {
            clients: {
                include: {
                    reports: {
                        orderBy: { createdAt: "desc" },
                        take: 1,
                    },
                },
                orderBy: { createdAt: "desc" },
            },
        },
    });

    if (!agency) {
        agency = await prisma.agency.create({
            data: {
                userId: session.user.id,
                name: session.user.name || "Mi Agencia",
            },
            include: {
                clients: {
                    include: {
                        reports: {
                            orderBy: { createdAt: "desc" },
                            take: 1,
                        },
                    },
                    orderBy: { createdAt: "desc" },
                },
            },
        });
    }

    const now = new Date();
    const currentMonth = now.getMonth() + 1;
    const currentYear = now.getFullYear();

    // Stats
    const totalClients = agency.clients.length;
    const activeClients = agency.clients.filter((c) => c.active).length;
    const reportsThisMonth = await prisma.report.count({
        where: {
            client: { agencyId: agency.id },
            month: currentMonth,
            year: currentYear,
            status: "sent",
        },
    });

    // Next report date: 1st of next month
    const nextReportDate = new Date(currentYear, now.getMonth() + 1, 1);
    const nextReportFormatted = `1 de ${getMonthName(nextReportDate.getMonth() + 1)}`;

    const clientsData = agency.clients.map((client) => ({
        id: client.id,
        name: client.name,
        email: client.email,
        active: client.active,
        lastReport: client.reports[0]
            ? {
                status: client.reports[0].status,
                sentAt: client.reports[0].sentAt?.toISOString() || null,
                month: client.reports[0].month,
                year: client.reports[0].year,
            }
            : null,
    }));

    return (
        <DashboardClient
            stats={{
                totalClients,
                activeClients,
                reportsThisMonth,
                nextReportDate: nextReportFormatted,
            }}
            clients={clientsData}
        />
    );
}
