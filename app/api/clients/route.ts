import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

/**
 * POST /api/clients — Create a new client
 */
export async function POST(request: Request) {
    const session = await auth();
    if (!session?.user?.id) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    const { agencyId, name, email, gaPropertyId, metaAdAccountId } = body;

    // Verify agency belongs to user
    const agency = await prisma.agency.findFirst({
        where: { id: agencyId, userId: session.user.id },
    });

    if (!agency) {
        return NextResponse.json({ message: "Agencia no encontrada" }, { status: 404 });
    }

    // Check plan limits
    const user = await prisma.user.findUnique({ where: { id: session.user.id } });
    const clientCount = await prisma.client.count({ where: { agencyId } });
    const planLimits: Record<string, number> = {
        free: 0, starter: 1, growth: 5, agency: 999,
    };
    const maxClients = planLimits[user?.plan || "free"] || 0;

    if (clientCount >= maxClients) {
        return NextResponse.json(
            { message: "Has alcanzado el límite de clientes de tu plan" },
            { status: 403 }
        );
    }

    const client = await prisma.client.create({
        data: {
            agencyId,
            name,
            email,
            gaPropertyId: gaPropertyId || null,
            metaAdAccountId: metaAdAccountId || null,
        },
    });

    return NextResponse.json(client, { status: 201 });
}

/**
 * GET /api/clients — List agency clients
 */
export async function GET() {
    const session = await auth();
    if (!session?.user?.id) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const agency = await prisma.agency.findUnique({
        where: { userId: session.user.id },
    });

    if (!agency) {
        return NextResponse.json([]);
    }

    const clients = await prisma.client.findMany({
        where: { agencyId: agency.id },
        include: {
            reports: { orderBy: { createdAt: "desc" }, take: 1 },
        },
        orderBy: { createdAt: "desc" },
    });

    return NextResponse.json(clients);
}
