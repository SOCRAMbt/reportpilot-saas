# ReportPilot 🚀

**Reportes de marketing automáticos para agencias.**  
Conecta Google Analytics y Meta Ads → IA genera insights → PDF profesional → Email automático → Cero intervención humana.

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Database**: Prisma ORM (SQLite dev / PostgreSQL prod)
- **Auth**: NextAuth.js v5 (Google OAuth)
- **AI**: Google Gemini 1.5 Flash
- **PDF**: @react-pdf/renderer
- **Email**: Resend
- **Billing**: Stripe
- **Hosting**: Vercel

---

## Quick Start

### 1. Clone & install

```bash
git clone <repository-url>
cd reportpilot
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in all variables in `.env` (see credential guide below).

### 3. Set up database

```bash
npx prisma db push
npx prisma generate
```

### 4. Run locally

```bash
npm run dev
```

Visit `http://localhost:3000/setup` to verify all environment variables are configured.

---

## API Credential Guide

### Google OAuth + Analytics
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Analytics Data API**
3. Go to **APIs & Services → Credentials → Create OAuth 2.0 Client ID**
4. Set redirect URI: `http://localhost:3000/api/auth/callback/google`
5. Copy **Client ID** → `GOOGLE_CLIENT_ID`
6. Copy **Client Secret** → `GOOGLE_CLIENT_SECRET`
7. Under OAuth consent screen, add scope: `analytics.readonly`

### Meta (Facebook) Ads
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create an app → Select **Business** type
3. Add **Marketing API** product
4. Copy **App ID** → `META_APP_ID`
5. Copy **App Secret** → `META_APP_SECRET`

### Google Gemini (AI)
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create an API key → `GEMINI_API_KEY`

### Stripe (Billing)
1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Copy **Secret Key** → `STRIPE_SECRET_KEY`
3. Create 3 products with recurring prices:
   - Starter ($79/mo) → copy Price ID → `STRIPE_STARTER_PRICE_ID`
   - Growth ($129/mo) → copy Price ID → `STRIPE_GROWTH_PRICE_ID`
   - Agency ($199/mo) → copy Price ID → `STRIPE_AGENCY_PRICE_ID`
4. Set up webhook endpoint: `https://your-domain.com/api/webhooks/stripe`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Copy Webhook Secret → `STRIPE_WEBHOOK_SECRET`

### Resend (Email)
1. Go to [Resend](https://resend.com/)
2. Create an API key → `RESEND_API_KEY`
3. Verify your sending domain

### Other Variables
- `NEXTAUTH_SECRET`: Run `openssl rand -base64 32`
- `NEXTAUTH_URL`: `http://localhost:3000` (dev) or your production URL
- `CRON_SECRET`: Run `openssl rand -hex 32`
- `NEXT_PUBLIC_APP_URL`: Same as `NEXTAUTH_URL`

---

## Deploy to Vercel

1. Push to GitHub
2. Import project in [Vercel](https://vercel.com/)
3. Add all environment variables from `.env.example`
4. Set `DATABASE_URL` to your PostgreSQL connection string (e.g., Neon, Supabase)
5. Deploy!

The cron job runs automatically on the 1st of each month at 8:00 AM UTC.

---

## Project Structure

```
├── app/
│   ├── page.tsx                    # Landing page
│   ├── login/page.tsx              # Login page
│   ├── setup/page.tsx              # Dev env checker
│   ├── dashboard/
│   │   ├── page.tsx                # Main dashboard
│   │   ├── layout.tsx              # Dashboard layout
│   │   ├── clients/new/            # New client wizard
│   │   ├── clients/[id]/           # Client detail
│   │   ├── settings/               # Agency settings
│   │   └── billing/                # Plan management
│   └── api/
│       ├── auth/                   # NextAuth handlers
│       ├── clients/                # Client CRUD
│       ├── agency/                 # Agency settings
│       ├── reports/generate/       # Manual report gen
│       ├── cron/generate-reports/  # Monthly cron
│       ├── stripe/create-checkout/ # Stripe checkout
│       └── webhooks/stripe/        # Stripe webhooks
├── lib/
│   ├── auth.ts                     # NextAuth config
│   ├── prisma.ts                   # Prisma client
│   ├── utils.ts                    # Utilities
│   ├── types.ts                    # TypeScript types
│   ├── ga/client.ts                # Google Analytics
│   ├── meta/client.ts              # Meta Ads
│   ├── ai/narrativeGenerator.ts    # AI insights
│   ├── pdf/reportGenerator.ts      # PDF generation
│   ├── email/sender.ts             # Email delivery
│   └── stripe/client.ts            # Stripe billing
├── prisma/schema.prisma            # Database schema
├── middleware.ts                    # Route protection
└── vercel.json                     # Cron + functions
```
