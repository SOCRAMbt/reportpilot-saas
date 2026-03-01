import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { redirect, notFound } from "next/navigation";
import { ClientDetailClient } from "./detail-client";

interface PageProps {
    params: Promise<{ id: string }>;
}

export default async function ClientDetailPage({ params }: PageProps) {
    const { id } = await params;
    const session = await auth();
    if (!session?.user?.id) redirect("/login");

    const client = await prisma.client.findFirst({
        where: {
            id,
            agency: { userId: session.user.id },
        },
        include: {
            agency: true,
            reports: {
                orderBy: { createdAt: "desc" },
            },
            integrations: true,
        },
    });

    if (!client) notFound();

    const clientData = {
        id: client.id,
        name: client.name,
        email: client.email,
        active: client.active,
        gaPropertyId: client.gaPropertyId,
        metaAdAccountId: client.metaAdAccountId,
        createdAt: client.createdAt.toISOString(),
        reports: client.reports.map((r) => ({
            id: r.id,
            month: r.month,
            year: r.year,
            status: r.status,
            pdfUrl: r.pdfUrl,
            sentAt: r.sentAt?.toISOString() || null,
            createdAt: r.createdAt.toISOString(),
        })),
        integrations: client.integrations.map((i) => ({
            id: i.id,
            type: i.type,
            expiresAt: i.expiresAt?.toISOString() || null,
        })),
    };

    return <ClientDetailClient client={clientData} />;
}
