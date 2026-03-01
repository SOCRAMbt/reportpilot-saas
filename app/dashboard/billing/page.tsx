import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { redirect } from "next/navigation";
import { BillingClient } from "./billing-client";

export default async function BillingPage() {
    const session = await auth();
    if (!session?.user?.id) redirect("/login");

    const user = await prisma.user.findUnique({
        where: { id: session.user.id },
    });

    if (!user) redirect("/login");

    const agency = await prisma.agency.findUnique({
        where: { userId: session.user.id },
    });

    const clientCount = agency
        ? await prisma.client.count({ where: { agencyId: agency.id } })
        : 0;

    return (
        <BillingClient
            currentPlan={user.plan}
            clientCount={clientCount}
        />
    );
}
