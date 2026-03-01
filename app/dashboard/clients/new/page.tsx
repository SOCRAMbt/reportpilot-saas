import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { redirect } from "next/navigation";
import { NewClientWizard } from "./wizard-client";

export default async function NewClientPage() {
    const session = await auth();
    if (!session?.user?.id) redirect("/login");

    const agency = await prisma.agency.findUnique({
        where: { userId: session.user.id },
    });

    if (!agency) redirect("/dashboard");

    // Check plan limits
    const user = await prisma.user.findUnique({ where: { id: session.user.id } });
    const clientCount = await prisma.client.count({ where: { agencyId: agency.id } });

    const planLimits: Record<string, number> = {
        free: 0,
        starter: 1,
        growth: 5,
        agency: 999,
    };

    const maxClients = planLimits[user?.plan || "free"] || 0;
    const canAdd = clientCount < maxClients;

    return (
        <div className="max-w-2xl mx-auto">
            <h1 className="text-2xl font-bold text-white mb-6">Nuevo Cliente</h1>
            {!canAdd ? (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-6 text-center">
                    <p className="text-amber-400 font-medium mb-2">
                        Has alcanzado el límite de tu plan ({clientCount}/{maxClients} clientes)
                    </p>
                    <p className="text-slate-400 text-sm mb-4">
                        Actualiza tu plan para agregar más clientes
                    </p>
                    <a
                        href="/dashboard/billing"
                        className="inline-block px-6 py-2.5 bg-amber-500 hover:bg-amber-400 text-black font-medium rounded-lg transition-colors"
                    >
                        Actualizar Plan
                    </a>
                </div>
            ) : (
                <NewClientWizard agencyId={agency.id} />
            )}
        </div>
    );
}
