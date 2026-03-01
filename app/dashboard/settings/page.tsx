import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { redirect } from "next/navigation";
import { SettingsClient } from "./settings-client";

export default async function SettingsPage() {
    const session = await auth();
    if (!session?.user?.id) redirect("/login");

    const agency = await prisma.agency.findUnique({
        where: { userId: session.user.id },
    });

    if (!agency) redirect("/dashboard");

    return (
        <SettingsClient
            agency={{
                id: agency.id,
                name: agency.name,
                brandColor: agency.brandColor,
                logoUrl: agency.logoUrl,
            }}
        />
    );
}
