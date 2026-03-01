import { NextResponse } from "next/server";
import { stripe } from "@/lib/stripe/client";
import { prisma } from "@/lib/prisma";
import Stripe from "stripe";

/**
 * POST /api/webhooks/stripe
 * Handles Stripe webhook events for subscription lifecycle
 */
export async function POST(request: Request) {
    const body = await request.text();
    const sig = request.headers.get("stripe-signature")!;

    let event: Stripe.Event;

    try {
        event = stripe.webhooks.constructEvent(
            body,
            sig,
            process.env.STRIPE_WEBHOOK_SECRET!
        );
    } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error";
        console.error("Webhook signature verification failed:", message);
        return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
    }

    try {
        switch (event.type) {
            case "checkout.session.completed": {
                const session = event.data.object as Stripe.Checkout.Session;
                const userId = session.metadata?.userId;

                if (userId && session.subscription) {
                    // Get the subscription to find the plan
                    const subscription = await stripe.subscriptions.retrieve(
                        session.subscription as string
                    );
                    const priceId = subscription.items.data[0]?.price?.id;
                    const plan = getPlanFromPriceId(priceId);

                    await prisma.user.update({
                        where: { id: userId },
                        data: {
                            plan,
                            stripeCustomerId: session.customer as string,
                        },
                    });
                }
                break;
            }

            case "customer.subscription.updated": {
                const subscription = event.data.object as Stripe.Subscription;
                const customerId = subscription.customer as string;
                const priceId = subscription.items.data[0]?.price?.id;
                const plan = getPlanFromPriceId(priceId);

                const user = await prisma.user.findFirst({
                    where: { stripeCustomerId: customerId },
                });

                if (user) {
                    await prisma.user.update({
                        where: { id: user.id },
                        data: { plan },
                    });
                }
                break;
            }

            case "customer.subscription.deleted": {
                const subscription = event.data.object as Stripe.Subscription;
                const customerId = subscription.customer as string;

                const user = await prisma.user.findFirst({
                    where: { stripeCustomerId: customerId },
                });

                if (user) {
                    await prisma.user.update({
                        where: { id: user.id },
                        data: { plan: "free" },
                    });
                }
                break;
            }
        }
    } catch (error) {
        console.error("Error processing webhook:", error);
        return NextResponse.json(
            { error: "Webhook processing failed" },
            { status: 500 }
        );
    }

    return NextResponse.json({ received: true });
}

function getPlanFromPriceId(priceId: string | undefined): string {
    if (!priceId) return "free";

    if (priceId === process.env.STRIPE_STARTER_PRICE_ID) return "starter";
    if (priceId === process.env.STRIPE_GROWTH_PRICE_ID) return "growth";
    if (priceId === process.env.STRIPE_AGENCY_PRICE_ID) return "agency";

    return "free";
}
