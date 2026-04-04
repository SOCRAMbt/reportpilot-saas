'use client'

import { useState } from 'react'
import Link from 'next/link'
import { DashboardLayout } from '@/components/DashboardLayout'
import { DollarSign, Calendar, Filter, AlertTriangle } from 'lucide-react'
import api from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

interface VEP {
  id: number
  tipo_vep: string
  periodo: string
  categoria: string
  importe_total: number
  estado: string
  fecha_vencimiento: string
  cliente?: {
    razon_social: string
  }
}

export default function VEPsPage() {
  const [filtroPeriodo, setFiltroPeriodo] = useState('')
  const [filtroEstado, setFiltroEstado] = useState('')
  const [preliquidando, setPreliquidando] = useState(false)
  const queryClient = useQueryClient()

  const handlePreLiquidar = async () => {
    setPreliquidando(true)
    try {
      await api.post('/veps/pre-liquidar')
      queryClient.invalidateQueries({ queryKey: ['veps'] })
    } catch (e) {
      console.error('Error pre-liquidando:', e)
    } finally {
      setPreliquidando(false)
    }
  }

  const { data: vepsData, isLoading } = useQuery({
    queryKey: ['veps', filtroPeriodo, filtroEstado],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filtroPeriodo) params.set('periodo', filtroPeriodo)
      if (filtroEstado) params.set('estado', filtroEstado)
      const { data } = await api.get(`/veps?${params}`)
      return data
    },
  })

  const aprobarVEP = useMutation({
    mutationFn: async (id: number) => {
      await api.post(`/veps/${id}/aprobar`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['veps'] })
    },
  })

  const marcarPagado = useMutation({
    mutationFn: async (id: number) => {
      await api.put(`/veps/${id}/registrar-pago`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['veps'] })
    },
  })

  const veps = vepsData?.veps || []

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">VEPs</h1>
            <p className="page-subtitle">Gestión de obligaciones fiscales</p>
          </div>
          <button
            onClick={handlePreLiquidar}
            disabled={preliquidando}
            className="btn-primary"
          >
            {preliquidando ? 'Pre-liquidando...' : '+ Pre-liquidar VEPs'}
          </button>
        </div>

        {/* Banner de vencimientos */}
        <div className="alert alert-yellow">
          <AlertTriangle className="h-5 w-5 flex-shrink-0" />
          <div>
            <p className="font-semibold">Vencimientos próximos</p>
            <p className="text-sm">3 VEPs vencen en los próximos 7 días</p>
          </div>
        </div>

        {/* Filtros */}
        <div className="card">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="input-label">Período</label>
              <input
                type="month"
                value={filtroPeriodo}
                onChange={(e) => setFiltroPeriodo(e.target.value)}
                className="input-field"
              />
            </div>
            <div className="flex-1 min-w-[200px]">
              <label className="input-label">Estado</label>
              <select
                value={filtroEstado}
                onChange={(e) => setFiltroEstado(e.target.value)}
                className="input-field"
              >
                <option value="">Todos</option>
                <option value="PRE_LIQUIDADO">Pre-liquidado</option>
                <option value="APROBADO">Aprobado</option>
                <option value="PAGADO">Pagado</option>
                <option value="VENCIDO">Vencido</option>
              </select>
            </div>
            <button className="btn-secondary">
              <Filter className="h-4 w-4 mr-2" />
              Filtrar
            </button>
          </div>
        </div>

        {/* Tabla de VEPs */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Obligaciones fiscales</h2>
          
          {isLoading ? (
            <div className="skeleton h-64" />
          ) : veps.length > 0 ? (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Período</th>
                    <th>Tipo</th>
                    <th>Importe</th>
                    <th>Vencimiento</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {veps.map((vep: VEP) => (
                    <tr key={vep.id}>
                      <td className="font-medium">
                        {vep.cliente?.razon_social || 'Sin cliente'}
                      </td>
                      <td>{vep.periodo}</td>
                      <td>
                        <span className="badge badge-blue">{vep.tipo_vep}</span>
                      </td>
                      <td className="font-semibold">
                        ${Number(vep.importe_total).toLocaleString('es-AR', { minimumFractionDigits: 2 })}
                      </td>
                      <td>
                        <span className={
                          new Date(vep.fecha_vencimiento) < new Date() 
                            ? 'text-red-600 font-medium' 
                            : 'text-slate-600'
                        }>
                          {new Date(vep.fecha_vencimiento).toLocaleDateString()}
                        </span>
                      </td>
                      <td>
                        <EstadoBadge estado={vep.estado} />
                      </td>
                      <td>
                        <div className="flex gap-2">
                          {vep.estado === 'PRE_LIQUIDADO' && (
                            <button
                              onClick={() => aprobarVEP.mutate(vep.id)}
                              className="btn-success btn-sm"
                            >
                              Aprobar
                            </button>
                          )}
                          {vep.estado === 'APROBADO' && (
                            <button
                              onClick={() => marcarPagado.mutate(vep.id)}
                              className="btn-secondary btn-sm"
                            >
                              Marcar pagado
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <DollarSign className="h-12 w-12 text-slate-300 mb-3" />
              <p className="text-slate-500">No hay VEPs para mostrar</p>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}

function EstadoBadge({ estado }: { estado: string }) {
  const estados: Record<string, { clase: string; label: string; icono: string }> = {
    PRE_LIQUIDADO: { clase: 'badge-yellow', label: 'Pendiente', icono: '⏳' },
    APROBADO: { clase: 'badge-blue', label: 'Aprobado', icono: '✓' },
    PAGADO: { clase: 'badge-green', label: 'Pagado', icono: '✓' },
    VENCIDO: { clase: 'badge-red', label: 'Vencido', icono: '⚠' },
  }

  const config = estados[estado] || { clase: 'badge-gray', label: estado, icono: '' }

  return (
    <span className={`badge ${config.clase}`}>
      {config.icono} {config.label}
    </span>
  )
}
