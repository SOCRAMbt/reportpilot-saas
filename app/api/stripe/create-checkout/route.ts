import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { createCheckoutSession, getOrCreateCustomer } from "@/lib/stripe/client";

/**
 * POST /api/stripe/create-checkout
 * Creates a Stripe Checkout session for plan subscription
 */
export async function POST(request: Request) {
    const session = await auth();
    if (!session?.user?.id) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    const { priceId } = body;

    if (!priceId) {
        return NextResponse.json({ error: "priceId is required" }, { status: 400 });
    }

    const user = await prisma.user.findUnique({
        where: { id: session.user.id },
    });

    if (!user) {
        return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    try {
        // Get or create Stripe customer
        const customerId = await getOrCreateCustomer(
            user.email || "",
            user.name || "",
            user.stripeCustomerId
        );

        // Save customer ID if new
        if (!user.stripeCustomerId) {
            await prisma.user.update({
                where: { id: user.id },
                data: { stripeCustomerId: customerId },
            });
        }

        // Create checkout session
        const checkoutUrl = await createCheckoutSession(
            customerId,
            priceId,
            user.id
        );

        return NextResponse.json({ url: checkoutUrl });
    } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error";
        console.error("Checkout session creation failed:", message);
        return NextResponse.json(
            { error: "Failed to create checkout session" },
            { status: 500 }
        );
    }
}
