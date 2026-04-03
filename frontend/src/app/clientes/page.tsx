'use client'

import { useState } from 'react'
import Link from 'next/link'
import { DashboardLayout } from '@/components/DashboardLayout'
import { Users, Search, Plus, ChevronRight, AlertTriangle, CheckCircle, AlertCircle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

interface Cliente {
  id: number
  cuit: string
  razon_social: string
  nombre_fantasia?: string
  categoria_monotributo?: string
  email?: string
  telefono?: string
  activo: boolean
  riesgo_fiscal?: {
    riesgo_exclusion: boolean
    urgencia_alerta: boolean
    categoria_calculada: string
    categoria_actual: string
    triggers_activados: string[]
  }
}

function getRiesgoLevel(cliente: Cliente): 'verde' | 'amarillo' | 'rojo' {
  const riesgo = cliente.riesgo_fiscal
  if (!riesgo) return 'verde'
  if (riesgo.riesgo_exclusion || riesgo.triggers_activados?.length > 0) return 'rojo'
  if (riesgo.urgencia_alerta || riesgo.categoria_calculada > riesgo.categoria_actual) return 'amarillo'
  return 'verde'
}

function RiesgoBadge({ nivel }: { nivel: 'verde' | 'amarillo' | 'rojo' }) {
  const config = {
    verde: { icon: CheckCircle, label: 'Sin riesgo', cls: 'text-emerald-600 bg-emerald-50' },
    amarillo: { icon: AlertCircle, label: 'Atencion', cls: 'text-amber-600 bg-amber-50' },
    rojo: { icon: AlertTriangle, label: 'Riesgo', cls: 'text-red-600 bg-red-50' },
  }
  const { icon: Icon, label, cls } = config[nivel]
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      <Icon className="h-3 w-3" />
      {label}
    </span>
  )
}

export default function ClientesPage() {
  const [busqueda, setBusqueda] = useState('')

  const { data: clientesData, isLoading } = useQuery({
    queryKey: ['clientes', busqueda],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (busqueda) params.set('busqueda', busqueda)
      const { data } = await api.get(`/clientes?${params}`)
      return data as Cliente[]
    },
  })

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Clientes</h1>
            <p className="page-subtitle">Gestion de clientes del estudio</p>
          </div>
          <button className="btn-primary">
            <Plus className="h-5 w-5 mr-2" />
            Nuevo cliente
          </button>
        </div>

        {/* Buscador */}
        <div className="card">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
            <input
              type="text"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Buscar por nombre o CUIT..."
              className="input-field pl-10"
            />
          </div>
        </div>

        {/* Grid de clientes */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="card skeleton h-48" />
            ))}
          </div>
        ) : clientesData && clientesData.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {clientesData.map((cliente: Cliente) => {
              const nivel = getRiesgoLevel(cliente)
              return (
                <div key={cliente.id} className="card card-hover">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-semibold text-slate-900">{cliente.razon_social}</h3>
                      {cliente.nombre_fantasia && (
                        <p className="text-sm text-slate-500">{cliente.nombre_fantasia}</p>
                      )}
                    </div>
                    <RiesgoBadge nivel={nivel} />
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">CUIT:</span>
                      <span className="font-mono">{cliente.cuit}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Categoria:</span>
                      <span className="badge badge-blue">
                        {cliente.categoria_monotributo || cliente.riesgo_fiscal?.categoria_actual || 'N/A'}
                      </span>
                    </div>
                    {cliente.email && (
                      <div className="flex justify-between">
                        <span className="text-slate-500">Email:</span>
                        <span className="text-slate-700 truncate max-w-[150px]">
                          {cliente.email}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="mt-4 pt-4 border-t border-slate-100">
                    <Link
                      href={`/clientes/${cliente.id}`}
                      className="btn-secondary btn-sm w-full flex items-center justify-center"
                    >
                      Ver detalle
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Link>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="card">
            <div className="empty-state">
              <Users className="h-12 w-12 text-slate-300 mb-3" />
              <p className="text-slate-500">
                {busqueda ? 'No se encontraron clientes' : 'No hay clientes cargados'}
              </p>
              {!busqueda && (
                <button className="btn-primary mt-4">
                  <Plus className="h-4 w-4 mr-2" />
                  Cargar primer cliente
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
