'use client'

import { useState } from 'react'
import Link from 'next/link'
import { DashboardLayout } from '@/components/DashboardLayout'
import { Archive, Download, Calendar, FileText, Loader2 } from 'lucide-react'
import api from '@/lib/api'
import { useQuery } from '@tanstack/react-query'

interface Cliente {
  id: number
  cuit: string
  razon_social: string
}

export default function BankKitPage() {
  const [clienteId, setClienteId] = useState('')
  const [periodo, setPeriodo] = useState('')
  const [generando, setGenerando] = useState(false)

  const { data: clientesData } = useQuery({
    queryKey: ['clientes'],
    queryFn: async () => {
      const { data } = await api.get('/clientes')
      return data.clientes as Cliente[]
    },
  })

  const handleGenerar = async () => {
    if (!clienteId || !periodo) return

    setGenerando(true)
    try {
      const response = await api.get(`/bank-kit/${clienteId}/generar`, {
        params: { periodo },
        responseType: 'blob',
      })

      // Crear descarga automática
      const blob = new Blob([response.data], { type: 'application/zip' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `BankKit_${periodo}.zip`
      link.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Error generando Bank-Kit:', error)
    } finally {
      setGenerando(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Bank-Kit</h1>
            <p className="page-subtitle">Generador de paquetes para banco</p>
          </div>
        </div>

        {/* Descripción */}
        <div className="alert alert-blue">
          <FileText className="h-5 w-5 flex-shrink-0" />
          <div>
            <p className="font-semibold">¿Qué es Bank-Kit?</p>
            <p className="text-sm">
              Genera automáticamente el Libro IVA Ventas, Libro IVA Compras y Constancia de Inscripción 
              listos para presentar en el banco.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Formulario de generación */}
          <div className="card">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Archive className="h-5 w-5 text-blue-600" />
              Generar paquete
            </h2>

            <div className="space-y-4">
              {/* Cliente */}
              <div>
                <label className="input-label">Cliente</label>
                <select
                  value={clienteId}
                  onChange={(e) => setClienteId(e.target.value)}
                  className="input-field"
                >
                  <option value="">Seleccionar cliente...</option>
                  {clientesData?.map((cliente) => (
                    <option key={cliente.id} value={cliente.id}>
                      {cliente.razon_social} (CUIT: {cliente.cuit})
                    </option>
                  ))}
                </select>
              </div>

              {/* Período */}
              <div>
                <label className="input-label">Período</label>
                <input
                  type="month"
                  value={periodo}
                  onChange={(e) => setPeriodo(e.target.value)}
                  className="input-field"
                  max={new Date().toISOString().slice(0, 7)}
                />
              </div>

              {/* Botón generar */}
              <button
                onClick={handleGenerar}
                disabled={!clienteId || !periodo || generando}
                className="btn-primary w-full mt-6"
              >
                {generando ? (
                  <>
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                    Generando paquete...
                  </>
                ) : (
                  <>
                    <Download className="h-5 w-5 mr-2" />
                    Generar y descargar paquete
                  </>
                )}
              </button>

              <p className="text-xs text-slate-500 text-center mt-2">
                El archivo ZIP contendrá los libros IVA y la constancia de inscripción
              </p>
            </div>
          </div>

          {/* Historial */}
          <div className="card">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Calendar className="h-5 w-5 text-slate-600" />
              Últimas generaciones
            </h2>

            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 bg-slate-50 rounded-xl"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                      <Archive className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">Cliente Ejemplo S.A.</p>
                      <p className="text-xs text-slate-500">2026-0{i}</p>
                    </div>
                  </div>
                  <button className="btn-ghost btn-sm">
                    <Download className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>

            <div className="mt-4 pt-4 border-t border-slate-200">
              <Link href="/bank-kit/historial" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
                Ver historial completo →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
