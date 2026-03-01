import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

/**
 * PUT /api/agency — Update agency settings
 */
export async function PUT(request: Request) {
    const session = await auth();
    if (!session?.user?.id) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    const { name, brandColor, logoUrl } = body;

    const agency = await prisma.agency.findUnique({
        where: { userId: session.user.id },
    });

    if (!agency) {
        return NextResponse.json({ error: "Agency not found" }, { status: 404 });
    }

    const updated = await prisma.agency.update({
        where: { id: agency.id },
        data: {
            name: name || agency.name,
            brandColor: brandColor || agency.brandColor,
            logoUrl: logoUrl !== undefined ? logoUrl : agency.logoUrl,
        },
    });

    return NextResponse.json(updated);
}
