'use client'

import { useState } from 'react'
import Link from 'next/link'
import { DashboardLayout } from '@/components/DashboardLayout'
import { Users, Search, Plus, ChevronRight } from 'lucide-react'
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
}

export default function ClientesPage() {
  const [busqueda, setBusqueda] = useState('')

  const { data: clientesData, isLoading } = useQuery({
    queryKey: ['clientes', busqueda],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (busqueda) params.set('busqueda', busqueda)
      const { data } = await api.get(`/clientes?${params}`)
      return data
    },
  })

  const clientes = clientesData?.clientes || []

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Clientes</h1>
            <p className="page-subtitle">Gestión de clientes del estudio</p>
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
        ) : clientes.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {clientes.map((cliente: Cliente) => (
              <div key={cliente.id} className="card card-hover">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-semibold text-slate-900">{cliente.razon_social}</h3>
                    {cliente.nombre_fantasia && (
                      <p className="text-sm text-slate-500">{cliente.nombre_fantasia}</p>
                    )}
                  </div>
                  <span className="semaforo-verde" title="Sin riesgo" />
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">CUIT:</span>
                    <span className="font-mono">{cliente.cuit}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Categoría:</span>
                    <span className="badge badge-blue">
                      {cliente.categoria_monotributo || 'N/A'}
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
            ))}
          </div>
        ) : (
          <div className="card">
            <div className="empty-state">
              <Users className="h-12 w-12 text-slate-300 mb-3" />
              <p className="text-slate-500">
                {busqueda ? 'No se encontraron clientes' : 'No hay clientes cargados'}
              </p>
              { !busqueda && (
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
