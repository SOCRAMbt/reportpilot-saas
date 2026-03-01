import Stripe from "stripe";

let _stripe: Stripe | null = null;

export function getStripe(): Stripe {
    if (!_stripe) {
        if (!process.env.STRIPE_SECRET_KEY) {
            throw new Error("STRIPE_SECRET_KEY is not set");
        }
        _stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
    }
    return _stripe;
}

// Keep `stripe` export for backward compatibility
export const stripe = new Proxy({} as Stripe, {
    get(_target, prop) {
        return (getStripe() as unknown as Record<string | symbol, unknown>)[prop];
    },
});

export const PLANS = {
    starter: {
        name: "Starter",
        price: 79,
        maxClients: 1,
        priceId: process.env.STRIPE_STARTER_PRICE_ID || "",
        features: [
            "1 cliente",
            "Reportes automáticos mensuales",
            "Google Analytics + Meta Ads",
            "Insights con IA",
            "Soporte por email",
        ],
    },
    growth: {
        name: "Growth",
        price: 129,
        maxClients: 5,
        priceId: process.env.STRIPE_GROWTH_PRICE_ID || "",
        features: [
            "Hasta 5 clientes",
            "Todo lo de Starter",
            "Marca personalizada",
            "Soporte prioritario",
        ],
    },
    agency: {
        name: "Agency",
        price: 199,
        maxClients: 999,
        priceId: process.env.STRIPE_AGENCY_PRICE_ID || "",
        features: [
            "Clientes ilimitados",
            "Todo lo de Growth",
            "Logo personalizado en reportes",
            "API access",
            "Soporte dedicado",
        ],
    },
} as const;

/**
 * Creates a Stripe Checkout session for plan upgrade
 */
export async function createCheckoutSession(
    customerId: string,
    priceId: string,
    userId: string
): Promise<string> {
    const session = await stripe.checkout.sessions.create({
        customer: customerId,
        mode: "subscription",
        payment_method_types: ["card"],
        line_items: [{ price: priceId, quantity: 1 }],
        success_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard/billing?success=true`,
        cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard/billing?canceled=true`,
        metadata: { userId },
    });

    return session.url!;
}

/**
 * Creates or retrieves a Stripe customer for a user
 */
export async function getOrCreateCustomer(
    email: string,
    name: string,
    existingCustomerId?: string | null
): Promise<string> {
    if (existingCustomerId) {
        return existingCustomerId;
    }

    const customer = await stripe.customers.create({
        email,
        name,
    });

    return customer.id;
}

/**
 * Gets active subscriptions for a customer
 */
export async function getSubscription(customerId: string) {
    const subscriptions = await stripe.subscriptions.list({
        customer: customerId,
        status: "active",
        limit: 1,
    });

    return subscriptions.data[0] || null;
}

/**
 * Creates a billing portal session for subscription management
 */
export async function createPortalSession(customerId: string): Promise<string> {
    const session = await stripe.billingPortal.sessions.create({
        customer: customerId,
        return_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard/billing`,
    });

    return session.url;
}
