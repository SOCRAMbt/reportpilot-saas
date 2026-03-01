import Link from "next/link";
import {
  BarChart3,
  Plug,
  Brain,
  Mail,
  Check,
  ArrowRight,
  Zap,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold">
              Report<span className="text-blue-400">Pilot</span>
            </span>
          </div>
          <div className="flex items-center gap-4">
            <a href="#pricing" className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:inline">
              Precios
            </a>
            <Link
              href="/login"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Iniciar sesión
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-20 md:pt-40 md:pb-32 overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute -top-40 -right-40 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
          <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.02)_1px,transparent_1px)] bg-[size:64px_64px]" />
        </div>

        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-medium mb-8">
            <Zap className="w-4 h-4" />
            Automatización con IA
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight leading-tight">
            Tus reportes de marketing,{" "}
            <span className="bg-gradient-to-r from-blue-400 via-blue-500 to-indigo-500 bg-clip-text text-transparent">
              solos.
            </span>
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Conecta Google Analytics y Meta Ads una vez. El día 1 de cada mes,
            tus clientes reciben su reporte automáticamente.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/login"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-all hover:scale-105 hover:shadow-lg hover:shadow-blue-600/25"
            >
              Empezar gratis 14 días
              <ArrowRight className="w-5 h-5" />
            </Link>
            <a
              href="#how-it-works"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-medium rounded-xl transition-colors"
            >
              Cómo funciona
            </a>
          </div>

          {/* Hero visual — Report mockup */}
          <div className="mt-16 relative">
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 md:p-8 shadow-2xl max-w-lg mx-auto">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
              </div>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-sm">RP</div>
                  <div>
                    <div className="text-sm font-semibold text-white">Reporte de Febrero 2025</div>
                    <div className="text-xs text-slate-400">Restaurante La Buena Mesa</div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-slate-800/80 rounded-lg p-3">
                    <div className="text-xs text-slate-500">Sesiones</div>
                    <div className="text-lg font-bold text-white">12,450</div>
                    <div className="text-xs text-green-400">↑ 23%</div>
                  </div>
                  <div className="bg-slate-800/80 rounded-lg p-3">
                    <div className="text-xs text-slate-500">ROAS</div>
                    <div className="text-lg font-bold text-white">4.2x</div>
                    <div className="text-xs text-green-400">↑ 15%</div>
                  </div>
                  <div className="bg-slate-800/80 rounded-lg p-3">
                    <div className="text-xs text-slate-500">Conversiones</div>
                    <div className="text-lg font-bold text-white">342</div>
                    <div className="text-xs text-green-400">↑ 8%</div>
                  </div>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-3 border-l-2 border-blue-500">
                  <div className="text-xs text-slate-400 italic">
                    &ldquo;El tráfico orgánico creció un 23% gracias a la optimización SEO implementada el mes pasado...&rdquo;
                  </div>
                </div>
              </div>
            </div>
            <div className="absolute -inset-4 bg-gradient-to-t from-slate-950 via-transparent to-transparent pointer-events-none" />
          </div>
        </div>
      </section>

      {/* How it Works */}
      <section id="how-it-works" className="py-20 md:py-32">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold">
              Cómo funciona
            </h2>
            <p className="mt-4 text-lg text-slate-400">
              Tres pasos simples para automatizar tus reportes
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <StepCard
              number={1}
              icon={<Plug className="w-6 h-6" />}
              title="Conecta tus cuentas"
              description="Vincula Google Analytics y Meta Ads de tus clientes en menos de 2 minutos."
              color="blue"
            />
            <StepCard
              number={2}
              icon={<Brain className="w-6 h-6" />}
              title="Nosotros analizamos todo"
              description="Nuestra IA analiza los datos y genera insights profesionales en español."
              color="purple"
            />
            <StepCard
              number={3}
              icon={<Mail className="w-6 h-6" />}
              title="Tu cliente recibe su reporte"
              description="El día 1 de cada mes, un reporte PDF profesional llega automáticamente al email de tu cliente."
              color="green"
            />
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-20 md:py-32 bg-slate-900/50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold">
              Planes simples, sin sorpresas
            </h2>
            <p className="mt-4 text-lg text-slate-400">
              Empieza gratis 14 días. Sin tarjeta de crédito.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <PricingCard
              name="Starter"
              price={79}
              features={[
                "1 cliente",
                "Reportes automáticos mensuales",
                "Google Analytics + Meta Ads",
                "Insights con IA",
                "Soporte por email",
              ]}
            />
            <PricingCard
              name="Growth"
              price={129}
              popular
              features={[
                "Hasta 5 clientes",
                "Todo lo de Starter",
                "Marca personalizada",
                "Soporte prioritario",
              ]}
            />
            <PricingCard
              name="Agency"
              price={199}
              features={[
                "Clientes ilimitados",
                "Todo lo de Growth",
                "Logo personalizado",
                "API access",
                "Soporte dedicado",
              ]}
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-md bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                <BarChart3 className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="font-bold">
                Report<span className="text-blue-400">Pilot</span>
              </span>
            </div>
            <p className="text-sm text-slate-500">
              © 2025 ReportPilot. Todos los derechos reservados.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function StepCard({
  number,
  icon,
  title,
  description,
  color,
}: {
  number: number;
  icon: React.ReactNode;
  title: string;
  description: string;
  color: "blue" | "purple" | "green";
}) {
  const colors = {
    blue: "from-blue-500 to-blue-600 shadow-blue-500/20",
    purple: "from-purple-500 to-purple-600 shadow-purple-500/20",
    green: "from-green-500 to-green-600 shadow-green-500/20",
  };

  return (
    <div className="relative bg-slate-900 border border-slate-800 rounded-2xl p-8 hover:border-slate-700 transition-all group">
      <div className="absolute -top-4 -left-2 w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-400">
        {number}
      </div>
      <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${colors[color]} flex items-center justify-center text-white shadow-lg mb-5 group-hover:scale-110 transition-transform`}>
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      <p className="text-slate-400 leading-relaxed">{description}</p>
    </div>
  );
}

function PricingCard({
  name,
  price,
  features,
  popular = false,
}: {
  name: string;
  price: number;
  features: string[];
  popular?: boolean;
}) {
  return (
    <div
      className={`relative bg-slate-900 border rounded-2xl p-8 ${popular
          ? "border-blue-500 shadow-lg shadow-blue-500/10 scale-105"
          : "border-slate-800"
        }`}
    >
      {popular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="px-4 py-1 bg-blue-600 text-white text-xs font-medium rounded-full">
            Más popular
          </span>
        </div>
      )}

      <div className="text-center mb-8">
        <h3 className="text-lg font-semibold text-white">{name}</h3>
        <div className="mt-3">
          <span className="text-4xl font-bold text-white">${price}</span>
          <span className="text-slate-500 ml-1">/mes</span>
        </div>
      </div>

      <ul className="space-y-3 mb-8">
        {features.map((feature, i) => (
          <li key={i} className="flex items-center gap-2 text-sm text-slate-300">
            <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
            {feature}
          </li>
        ))}
      </ul>

      <Link
        href="/login"
        className={`block w-full text-center py-3 font-medium rounded-xl transition-all hover:scale-105 ${popular
            ? "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/25"
            : "bg-white/5 hover:bg-white/10 border border-white/10 text-white"
          }`}
      >
        Empezar gratis
      </Link>
    </div>
  );
}
