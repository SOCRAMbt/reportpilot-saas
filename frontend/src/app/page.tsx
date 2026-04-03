'use client'

import Link from 'next/link'
import { DashboardLayout } from '@/components/DashboardLayout'
import { useDashboardStats } from '@/hooks/useDashboard'
import { useAlertas } from '@/hooks/useAlertas'
import { useComprobantes } from '@/hooks/useComprobantes'
import { AlertCircle, CheckCircle, Clock, Archive, RefreshCw, DollarSign } from 'lucide-react'

export default function HomePage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats()
  const { data: alertas } = useAlertas()
  const { data: comprobantesData } = useComprobantes({ limite: 5 })

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Dashboard</h1>
            <p className="page-subtitle">Resumen de tu estudio contable</p>
          </div>
          <Link href="/comprobantes/nuevo" className="btn-primary">
            + Nuevo Comprobante
          </Link>
        </div>

        {/* Stats */}
        {statsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="card skeleton h-28" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <StatCard
              title="Comprobantes hoy"
              value={stats?.comprobantes_hoy || 0}
              change="+12%"
              trend="up"
            />
            <StatCard
              title="Pendientes revisión"
              value={stats?.pendientes_revision || 0}
              change={stats && stats.pendientes_revision > 0 ? 'Atención' : 'Normal'}
              trend={stats && stats.pendientes_revision > 0 ? 'warning' : 'normal'}
            />
            <StatCard
              title="VEPs del mes"
              value={stats?.veps_pendientes || 0}
              change="+5"
              trend="up"
            />
            <StatCard
              title="Alertas activas"
              value={stats?.alertas_activas || 0}
              change={stats && stats.alertas_activas > 5 ? 'Atención' : 'Normal'}
              trend={stats && stats.alertas_activas > 5 ? 'warning' : 'normal'}
            />
          </div>
        )}

        {/* Acciones rápidas */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Acciones rápidas</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <QuickActionCard
              icon={RefreshCw}
              title="Sincronizar ARCA"
              description="Forzar sincronización con ARCA ahora"
              href="/comprobantes"
              color="blue"
            />
            <QuickActionCard
              icon={DollarSign}
              title="Generar VEPs"
              description="Pre-liquidar VEPs del mes"
              href="/veps"
              color="green"
            />
            <QuickActionCard
              icon={Archive}
              title="Bank-Kit"
              description="Generar paquete para el banco"
              href="/bank-kit"
              color="purple"
            />
          </div>
        </div>

        {/* Alertas críticas */}
        {alertas && alertas.length > 0 && (
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-amber-500" />
                Alertas Recientes
              </h2>
              <Link href="/alertas" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
                Ver todas →
              </Link>
            </div>
            <div className="space-y-3">
              {alertas.slice(0, 3).map((alerta) => (
                <div
                  key={alerta.id}
                  className={`alert ${
                    alerta.severidad === 'critica' ? 'alert-red' :
                    alerta.severidad === 'alta' ? 'alert-yellow' : 'alert-blue'
                  }`}
                >
                  <div className="flex-1">
                    <p className="font-semibold">{alerta.titulo}</p>
                    <p className="text-sm mt-1">{alerta.mensaje}</p>
                  </div>
                  <span className="text-xs text-slate-500">
                    {new Date(alerta.creado_en).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Últimos comprobantes */}
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Últimos Comprobantes</h2>
            <Link href="/comprobantes" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
              Ver todos →
            </Link>
          </div>
          {comprobantesData && comprobantesData.comprobantes.length > 0 ? (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Tipo</th>
                    <th>Número</th>
                    <th>Total</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {comprobantesData.comprobantes.map((cbte) => (
                    <tr key={cbte.id}>
                      <td>{new Date(cbte.fecha_emision).toLocaleDateString()}</td>
                      <td>
                        <span className="badge badge-gray">
                          {cbte.tipo_comprobante === '1' ? 'FA' : 
                           cbte.tipo_comprobante === '2' ? 'FB' : 
                           cbte.tipo_comprobante === '3' ? 'FC' : cbte.tipo_comprobante}
                        </span>
                      </td>
                      <td className="font-mono text-xs">
                        {String(cbte.punto_venta).padStart(4, '0')}-{String(cbte.numero).padStart(8, '0')}
                      </td>
                      <td className="font-semibold">${Number(cbte.total).toLocaleString('es-AR')}</td>
                      <td>
                        <EstadoBadge estado={cbte.estado_interno} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <CheckCircle className="h-12 w-12 text-slate-300 mb-3" />
              <p className="text-slate-500">No hay comprobantes recientes</p>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}

function StatCard({
  title,
  value,
  change,
  trend,
}: {
  title: string
  value: string | number
  change: string
  trend: 'up' | 'down' | 'warning' | 'normal'
}) {
  const trendColors = {
    up: 'text-emerald-600',
    down: 'text-red-600',
    warning: 'text-amber-600',
    normal: 'text-slate-600',
  }

  return (
    <div className="stat-card">
      <p className="stat-label">{title}</p>
      <p className="stat-value">{value}</p>
      <p className={`stat-change-${trend === 'up' || trend === 'normal' ? 'up' : 'down'}`}>
        {change}
      </p>
    </div>
  )
}

function QuickActionCard({
  icon: Icon,
  title,
  description,
  href,
  color,
}: {
  icon: any
  title: string
  description: string
  href: string
  color: 'blue' | 'green' | 'purple'
}) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600 hover:bg-blue-100',
    green: 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100',
    purple: 'bg-purple-50 text-purple-600 hover:bg-purple-100',
  }

  return (
    <Link href={href} className={`card card-hover ${colorClasses[color]}`}>
      <Icon className="h-8 w-8 mb-3" />
      <h3 className="font-semibold text-slate-900">{title}</h3>
      <p className="text-sm text-slate-600 mt-1">{description}</p>
    </Link>
  )
}

function EstadoBadge({ estado }: { estado: string }) {
  const estados: Record<string, { clase: string; label: string }> = {
    INCORPORADO: { clase: 'badge-green', label: 'OK' },
    REVISION_HUMANA: { clase: 'badge-yellow', label: 'Revisar' },
    PENDIENTE_VERIFICACION: { clase: 'badge-blue', label: 'Pendiente' },
    ANULADO: { clase: 'badge-red', label: 'Anulado' },
    AUSENTE: { clase: 'badge-red', label: 'Ausente' },
  }

  const config = estados[estado] || { clase: 'badge-gray', label: estado }

  return <span className={`badge ${config.clase}`}>{config.label}</span>
}
