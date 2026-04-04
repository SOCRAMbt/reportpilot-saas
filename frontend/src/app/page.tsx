'use client'

import { DashboardLayout } from '@/components/DashboardLayout'
import { useSemaforoClientes } from '@/hooks/useClientes'
import { useAlertas } from '@/hooks/useAlertas'
import { AlertCircle, CheckCircle, AlertTriangle, RefreshCw, FileText } from 'lucide-react'
import api from '@/lib/api'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

export default function HomePage() {
  const { data: semaforo, isLoading: semaforoLoading } = useSemaforoClientes()
  const { data: alertas } = useAlertas()
  const qc = useQueryClient()
  const [syncing, setSyncing] = useState(false)

  const handleSincronizar = async () => {
    setSyncing(true)
    try {
      await api.post('/comprobantes/sincronizar-todo')
      qc.invalidateQueries({ queryKey: ['dashboard', 'semaforo'] })
    } catch (e) {
      console.error('Error sincronizando:', e)
    } finally {
      setSyncing(false)
    }
  }

  const totales = semaforo?.totales || { rojo: 0, amarillo: 0, verde: 0 }
  const lista = (semaforo?.semaforo || [])
    .sort((a: { color: string }, b: { color: string }) => {
      const orden: Record<string, number> = { rojo: 0, amarillo: 1, verde: 2 }
      return (orden[a.color] ?? 3) - (orden[b.color] ?? 3)
    })

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Dashboard</h1>
            <p className="page-subtitle">Estado de tus clientes de un vistazo</p>
          </div>
          <button
            onClick={handleSincronizar}
            disabled={syncing}
            className="btn-secondary"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Sincronizando...' : 'Sincronizar ARCA'}
          </button>
        </div>

        {/* Contadores */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard title="Necesitan atención" value={totales.rojo} icon={AlertTriangle} color="red" />
          <StatCard title="Pendientes" value={totales.amarillo} icon={AlertCircle} color="yellow" />
          <StatCard title="Al día" value={totales.verde} icon={CheckCircle} color="green" />
        </div>

        {/* Alertas críticas */}
        {alertas && alertas.length > 0 && (
          <div className="alert alert-yellow">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <div>
              <p className="font-semibold">{alertas[0].titulo}</p>
              <p className="text-sm">{alertas[0].mensaje}</p>
            </div>
          </div>
        )}

        {/* Semáforo de clientes */}
        {semaforoLoading ? (
          <div className="card skeleton h-64" />
        ) : lista.length > 0 ? (
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Clientes</h2>
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Estado</th>
                    <th>Cliente</th>
                    <th>CUIT</th>
                    <th>Categoría</th>
                    <th>Detalle</th>
                  </tr>
                </thead>
                <tbody>
                  {lista.map((c: any) => (
                    <tr key={c.id} className="hover:bg-slate-50">
                      <td><SemaforoDot color={c.color} /></td>
                      <td className="font-medium">{c.razon_social}</td>
                      <td className="font-mono text-xs">{c.cuit}</td>
                      <td>
                        {c.categoria_monotributo && (
                          <span className="badge badge-blue">{c.categoria_monotributo}</span>
                        )}
                      </td>
                      <td className="text-sm text-slate-600">{c.issues.join(', ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="card">
            <div className="empty-state">
              <FileText className="h-12 w-12 text-slate-300 mb-3" />
              <p className="text-slate-500">No hay clientes cargados todavía</p>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}

function StatCard({ title, value, icon: Icon, color }: {
  title: string; value: number; icon: React.ElementType; color: string
}) {
  const colors: Record<string, string> = {
    red: 'bg-red-50 text-red-600 border-red-200',
    yellow: 'bg-yellow-50 text-yellow-600 border-yellow-200',
    green: 'bg-emerald-50 text-emerald-600 border-emerald-200',
  }
  return (
    <div className={`card border ${colors[color] || colors.green}`}>
      <div className="flex items-center gap-3">
        <Icon className="h-6 w-6" />
        <div>
          <p className="text-sm font-medium">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </div>
    </div>
  )
}

function SemaforoDot({ color }: { color: string }) {
  const colors: Record<string, string> = {
    rojo: 'bg-red-500',
    amarillo: 'bg-yellow-500',
    verde: 'bg-emerald-500',
  }
  return <span className={`inline-block h-3 w-3 rounded-full ${colors[color] || 'bg-slate-300'}`} />
}
