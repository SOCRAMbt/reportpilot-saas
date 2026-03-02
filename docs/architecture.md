# ReportPilot Architecture Diagram
This document describes the flow and architecture of the ReportPilot V2 platform using the new Agentic Stack.

\`\`\`mermaid
graph TD
    %% Actors
    Admin([Agency Admin])
    Cron([Cron Job / Scheduler])
    Client([End Client / Receiver])

    %% Frontend & Auth
    subgraph UI [Next.js 15 Frontend]
        Dashboard[Dashboard / Onboarding]
    end

    Clerk[Clerk Auth & Organizations]

    %% Vercel Backend
    subgraph Edge [Next.js API & Server Actions]
        API_Inngest[/app/api/inngest/]
        StripeWebhook[/app/api/stripe/webhook/]
    end

    %% Inngest Orchestration
    subgraph Orchestrator [Inngest Functions]
        MonthlyTrigger[Report Trigger Event]
        ReportWorker[Client Report Worker\n- Download Data\n- Query Gemini\n- Render PDF\n- Send Email]
    end

    %% Database & ORM
    Drizzle[(Drizzle ORM)]
    Neon[(Neon Serverless Postgres)]

    %% External APIs
    GA4[Google Analytics Data API]
    Meta[Meta Ads Graph API]
    Gemini[Google Gemini 3 Pro\nStructured Output API]
    Stripe[(Stripe Billing)]
    Resend[Resend Mailer API]

    %% Connections
    Admin -->|Login & Manage| UI
    UI <-->|Authenticate| Clerk

    UI <-->|Fetch/Write| Edge
    Edge <-->|Mutate| Drizzle
    Drizzle <--> Neon

    Cron -->|Day 1 Trigger| Edge
    Edge -->|Dispatch| MonthlyTrigger
    MonthlyTrigger -->|Fan-Out per Client| ReportWorker

    ReportWorker -->|Fetch| GA4
    ReportWorker -->|Fetch| Meta
    ReportWorker -->|Analyze Data| Gemini

    ReportWorker -->|Generate| PDF[@react-pdf/renderer Engine]
    PDF -->|Attach to| EmailSender[Email Dispatcher]
    
    EmailSender --> Resend
    Resend -->|Delivers Report| Client

    Stripe -->|Updates Usage| StripeWebhook
    StripeWebhook -->|Mutate| Drizzle
\`\`\`
