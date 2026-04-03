'use client'

import { useState } from 'react'
import Link from 'next/link'
import { DashboardLayout } from '@/components/DashboardLayout'
import { FileText, Upload, Filter, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

interface Comprobante {
  id: number
  tipo_comprobante: string
  punto_venta: number
  numero: number
  fecha_emision: string
  total: number
  estado_interno: string
  estado_arca: string
  cliente?: {
    razon_social: string
  }
}

export default function ComprobantesPage() {
  const [pestaña, setPestaña] = useState<'arca' | 'delta'>('arca')
  const [pagina, setPagina] = useState(1)
  const [filtros, setFiltros] = useState({
    estado: '',
    fecha_desde: '',
    fecha_hasta: '',
  })
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['comprobantes', pestaña, filtros, pagina],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.set('pagina', String(pagina))
      params.set('limite', '20')
      
      if (filtros.estado) params.set('estado', filtros.estado)
      if (filtros.fecha_desde) params.set('fecha_desde', filtros.fecha_desde)
      if (filtros.fecha_hasta) params.set('fecha_hasta', filtros.fecha_hasta)
      
      // Filtrar por pestaña
      if (pestaña === 'arca') {
        params.set('estado_arca', 'PRESENTE_VALIDO,INCORPORADO')
      } else {
        params.set('estado_interno', 'REVISION_HUMANA,AUSENTE')
      }
      
      const { data } = await api.get(`/comprobantes?${params}`)
      return data
    },
  })

  const incorporarComprobante = useMutation({
    mutationFn: async (id: number) => {
      await api.put(`/comprobantes/${id}/incorporar`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comprobantes'] })
    },
  })

  const descartarComprobante = useMutation({
    mutationFn: async (id: number) => {
      await api.put(`/comprobantes/${id}/descartar`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comprobantes'] })
    },
  })

  const comprobantes = data?.comprobantes || []

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Comprobantes</h1>
            <p className="page-subtitle">Gestión de facturas y documentos fiscales</p>
          </div>
          <div className="flex gap-2">
            <button className="btn-secondary">
              <Upload className="h-4 w-4 mr-2" />
              Importar
            </button>
            <Link href="/comprobantes/nuevo" className="btn-primary">
              <FileText className="h-4 w-4 mr-2" />
              Nuevo Comprobante
            </Link>
          </div>
        </div>

        {/* Banner Delta */}
        {pestaña === 'delta' && (
          <div className="alert alert-yellow">
            <AlertTriangle className="h-5 w-5 flex-shrink-0" />
            <div>
              <p className="font-semibold">Comprobantes que requieren tu revisión</p>
              <p className="text-sm">
                Estos comprobantes fueron detectados en ARCA pero requieren validación antes de incorporarse
              </p>
            </div>
          </div>
        )}

        {/* Pestañas */}
        <div className="flex gap-2 border-b border-slate-200">
          <button
            onClick={() => setPestaña('arca')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              pestaña === 'arca'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <CheckCircle className="h-4 w-4 inline mr-2" />
            En ARCA
          </button>
          <button
            onClick={() => setPestaña('delta')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              pestaña === 'delta'
                ? 'border-amber-600 text-amber-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <AlertTriangle className="h-4 w-4 inline mr-2" />
            Delta (requieren acción)
          </button>
        </div>

        {/* Filtros */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="h-5 w-5 text-slate-400" />
            <h2 className="font-semibold">Filtros</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <select
              className="input-field"
              value={filtros.estado}
              onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}
            >
              <option value="">Todos los estados</option>
              <option value="PENDIENTE_VERIFICACION">Pendiente</option>
              <option value="REVISION_HUMANA">Revisión</option>
              <option value="INCORPORADO">Incorporado</option>
            </select>
            <input
              type="date"
              className="input-field"
              value={filtros.fecha_desde}
              onChange={(e) => setFiltros({ ...filtros, fecha_desde: e.target.value })}
            />
            <input
              type="date"
              className="input-field"
              value={filtros.fecha_hasta}
              onChange={(e) => setFiltros({ ...filtros, fecha_hasta: e.target.value })}
            />
            <button className="btn-primary">Aplicar</button>
          </div>
        </div>

        {/* Lista de comprobantes */}
        <div className="card">
          {isLoading ? (
            <div className="text-center py-8">
              <p className="text-slate-500">Cargando comprobantes...</p>
            </div>
          ) : comprobantes.length > 0 ? (
            <>
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Fecha</th>
                      <th>Cliente</th>
                      <th>Tipo</th>
                      <th>Número</th>
                      <th>Total</th>
                      <th>Estado</th>
                      {pestaña === 'delta' && <th>Acciones</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {comprobantes.map((cbte: Comprobante) => (
                      <tr key={cbte.id}>
                        <td>{new Date(cbte.fecha_emision).toLocaleDateString()}</td>
                        <td className="font-medium">
                          {cbte.cliente?.razon_social || 'Sin cliente'}
                        </td>
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
                        <td className="font-semibold">
                          ${Number(cbte.total).toLocaleString('es-AR', { minimumFractionDigits: 2 })}
                        </td>
                        <td>
                          <EstadoBadge estado={cbte.estado_interno} />
                        </td>
                        {pestaña === 'delta' && (
                          <td>
                            <div className="flex gap-2">
                              <button
                                onClick={() => incorporarComprobante.mutate(cbte.id)}
                                className="btn-success btn-sm"
                                title="Incorporar"
                              >
                                <CheckCircle className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => descartarComprobante.mutate(cbte.id)}
                                className="btn-danger btn-sm"
                                title="Descartar"
                              >
                                <XCircle className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Paginación */}
              {data && data.total_paginas > 1 && (
                <div className="flex justify-center items-center gap-2 mt-6">
                  <button
                    className="btn-secondary"
                    onClick={() => setPagina(pagina - 1)}
                    disabled={pagina === 1}
                  >
                    Anterior
                  </button>
                  <span className="text-sm text-slate-600">
                    Página {pagina} de {data.total_paginas}
                  </span>
                  <button
                    className="btn-secondary"
                    onClick={() => setPagina(pagina + 1)}
                    disabled={pagina >= data.total_paginas}
                  >
                    Siguiente
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <FileText className="h-12 w-12 text-slate-300 mb-3" />
              <p className="text-slate-500">
                {pestaña === 'delta' 
                  ? 'No hay comprobantes que requieran revisión' 
                  : 'No hay comprobantes en ARCA'}
              </p>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
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
