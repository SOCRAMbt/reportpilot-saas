'use client'

import { useState } from 'react'
import Link from 'next/link'
import { DashboardLayout } from '@/components/DashboardLayout'
import { Bell, AlertTriangle, AlertCircle, Info, CheckCircle, Filter } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

interface Alerta {
  id: number
  tipo: string
  severidad: string
  titulo: string
  mensaje: string
  leida: boolean
  creado_en: string
}

export default function AlertasPage() {
  const [filtro, setFiltro] = useState<'todas' | 'no-leidas' | 'criticas'>('todas')
  const queryClient = useQueryClient()

  const { data: alertas, isLoading } = useQuery({
    queryKey: ['alertas'],
    queryFn: async () => {
      const { data } = await api.get('/alertas')
      return data as Alerta[]
    },
  })

  const marcarLeida = useMutation({
    mutationFn: async (id: number) => {
      await api.put(`/alertas/${id}/marcar-leida`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertas'] })
    },
  })

  const alertasFiltradas = alertas?.filter((alerta) => {
    if (filtro === 'no-leidas') return !alerta.leida
    if (filtro === 'criticas') return alerta.severidad === 'critica'
    return true
  })

  // Ordenar por severidad
  const severidadOrden = { critica: 0, alta: 1, media: 2, baja: 3 }
  const alertasOrdenadas = alertasFiltradas?.sort(
    (a, b) => severidadOrden[a.severidad as keyof typeof severidadOrden] - 
              severidadOrden[b.severidad as keyof typeof severidadOrden]
  )

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Alertas</h1>
            <p className="page-subtitle">Notificaciones del sistema</p>
          </div>
        </div>

        {/* Filtros */}
        <div className="card">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setFiltro('todas')}
              className={`btn-sm ${filtro === 'todas' ? 'btn-primary' : 'btn-secondary'}`}
            >
              Todas
            </button>
            <button
              onClick={() => setFiltro('no-leidas')}
              className={`btn-sm ${filtro === 'no-leidas' ? 'btn-primary' : 'btn-secondary'}`}
            >
              No leídas
            </button>
            <button
              onClick={() => setFiltro('criticas')}
              className={`btn-sm ${filtro === 'criticas' ? 'btn-primary' : 'btn-secondary'}`}
            >
              Críticas
            </button>
          </div>
        </div>

        {/* Lista de alertas */}
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="card skeleton h-24" />
            ))}
          </div>
        ) : alertasOrdenadas && alertasOrdenadas.length > 0 ? (
          <div className="space-y-3">
            {alertasOrdenadas.map((alerta) => (
              <div
                key={alerta.id}
                className={`card ${alerta.leida ? 'opacity-60' : ''} ${
                  alerta.severidad === 'critica' ? 'border-red-200 bg-red-50' :
                  alerta.severidad === 'alta' ? 'border-amber-200 bg-amber-50' : ''
                }`}
              >
                <div className="flex items-start gap-4">
                  {/* Ícono según severidad */}
                  <div className={`flex-shrink-0 ${
                    alerta.severidad === 'critica' ? 'text-red-600' :
                    alerta.severidad === 'alta' ? 'text-amber-600' :
                    'text-blue-600'
                  }`}>
                    {alerta.severidad === 'critica' && <AlertTriangle className="h-6 w-6" />}
                    {alerta.severidad === 'alta' && <AlertCircle className="h-6 w-6" />}
                    {alerta.severidad === 'media' && <Info className="h-6 w-6" />}
                    {alerta.severidad === 'baja' && <Bell className="h-6 w-6" />}
                  </div>

                  {/* Contenido */}
                  <div className="flex-1">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-semibold text-slate-900">{alerta.titulo}</h3>
                        <p className="text-sm text-slate-600 mt-1">{alerta.mensaje}</p>
                      </div>
                      {!alerta.leida && (
                        <button
                          onClick={() => marcarLeida.mutate(alerta.id)}
                          className="btn-ghost btn-sm flex items-center gap-1"
                        >
                          <CheckCircle className="h-4 w-4" />
                          Marcar leída
                        </button>
                      )}
                    </div>
                    <div className="flex items-center gap-4 mt-3">
                      <span className={`badge ${
                        alerta.severidad === 'critica' ? 'badge-red' :
                        alerta.severidad === 'alta' ? 'badge-yellow' :
                        alerta.severidad === 'media' ? 'badge-blue' : 'badge-gray'
                      }`}>
                        {alerta.severidad}
                      </span>
                      <span className="text-xs text-slate-500">
                        {new Date(alerta.creado_en).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card">
            <div className="empty-state">
              <CheckCircle className="h-12 w-12 text-slate-300 mb-3" />
              <p className="text-slate-500">
                {filtro === 'no-leidas' ? 'No hay alertas no leídas' :
                 filtro === 'criticas' ? 'No hay alertas críticas' :
                 'No hay alertas'}
              </p>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
