'use client'

import { useState, useRef, useCallback } from 'react'
import { DashboardLayout } from '@/components/DashboardLayout'
import { Camera, Upload, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import api from '@/lib/api'
import { useQuery } from '@tanstack/react-query'

export default function IngestaPage() {
  const [archivo, setArchivo] = useState<File | null>(null)
  const [clienteId, setClienteId] = useState('')
  const [procesando, setProcesando] = useState(false)
  const [resultado, setResultado] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const dropRef = useRef<HTMLDivElement>(null)

  const { data: clientes } = useQuery({
    queryKey: ['clientes'],
    queryFn: async () => {
      const { data } = await api.get('/clientes?activo=true')
      return Array.isArray(data) ? data : (data?.clientes || [])
    },
  })

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('image/')) {
      setArchivo(file)
    }
  }, [])

  const handleProcesar = async () => {
    if (!archivo || !clienteId) return
    setProcesando(true)
    setResultado(null)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('archivo', archivo)
      formData.append('cliente_id', clienteId)

      const { data } = await api.post('/ingesta/foto', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResultado(data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Error procesando la imagen')
    } finally {
      setProcesando(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Cargar Factura</h1>
            <p className="page-subtitle">Subí una foto de factura para procesar con IA</p>
          </div>
        </div>

        {/* Selección de cliente */}
        <div className="card">
          <label className="input-label">Cliente (obligatorio)</label>
          <select
            value={clienteId}
            onChange={(e) => setClienteId(e.target.value)}
            className="input-field"
          >
            <option value="">Seleccionar cliente...</option>
            {clientes?.map((c: any) => (
              <option key={c.id} value={c.id}>{c.razon_social}</option>
            ))}
          </select>
        </div>

        {/* Drop zone */}
        <div
          ref={dropRef}
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="card border-2 border-dashed border-slate-300 hover:border-blue-400 transition-colors cursor-pointer"
          onClick={() => document.getElementById('file-input')?.click()}
        >
          <input
            id="file-input"
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => setArchivo(e.target.files?.[0] || null)}
          />

          {archivo ? (
            <div className="text-center">
              <Camera className="h-12 w-12 text-blue-600 mx-auto mb-3" />
              <p className="font-medium text-slate-900">{archivo.name}</p>
              <p className="text-sm text-slate-500">{(archivo.size / 1024).toFixed(1)} KB</p>
              <button
                onClick={(e) => { e.stopPropagation(); setArchivo(null) }}
                className="btn-secondary btn-sm mt-3"
              >
                Cambiar imagen
              </button>
            </div>
          ) : (
            <div className="text-center py-8">
              <Upload className="h-12 w-12 text-slate-400 mx-auto mb-3" />
              <p className="font-medium text-slate-600">Arrastrá una foto acá</p>
              <p className="text-sm text-slate-500 mt-1">o hacé click para seleccionar</p>
              <p className="text-xs text-slate-400 mt-2">JPG, PNG — máximo 10MB</p>
            </div>
          )}
        </div>

        {/* Botón procesar */}
        <button
          onClick={handleProcesar}
          disabled={procesando || !archivo || !clienteId}
          className="btn-primary w-full"
        >
          {procesando ? (
            <><Loader2 className="h-5 w-5 mr-2 animate-spin" /> Procesando con IA...</>
          ) : (
            <><Camera className="h-5 w-5 mr-2" /> Procesar factura</>
          )}
        </button>

        {/* Error */}
        {error && (
          <div className="alert alert-red">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Resultado */}
        {resultado && (
          <div className={`card ${resultado.requiere_revision ? 'border-amber-300 bg-amber-50' : 'border-emerald-300 bg-emerald-50'}`}>
            <div className="flex items-center gap-3 mb-4">
              {resultado.requiere_revision ? (
                <AlertCircle className="h-6 w-6 text-amber-600" />
              ) : (
                <CheckCircle className="h-6 w-6 text-emerald-600" />
              )}
              <div>
                <p className="font-semibold text-slate-900">
                  {resultado.requiere_revision ? '⚠️ Requiere revisión' : '✅ Factura incorporada'}
                </p>
                <p className="text-sm text-slate-600">
                  ID: {resultado.comprobante_id} · Confianza: {resultado.confidence}%
                </p>
              </div>
            </div>

            {resultado.datos_ocr && Object.keys(resultado.datos_ocr).length > 0 && (
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-slate-500">Tipo:</span> <strong>{resultado.datos_ocr.tipo_comprobante || '—'}</strong></div>
                <div><span className="text-slate-500">Número:</span> <strong>{resultado.datos_ocr.punto_venta || '—'}-{resultado.datos_ocr.numero || '—'}</strong></div>
                <div><span className="text-slate-500">Total:</span> <strong>${resultado.datos_ocr.total || '—'}</strong></div>
                <div><span className="text-slate-500">CUIT:</span> <strong>{resultado.datos_ocr.cuit_emisor?.slice(0, 4) + '***' || '—'}</strong></div>
              </div>
            )}

            {resultado.requiere_revision && (
              <a href="/comprobantes" className="btn-secondary btn-sm mt-4 block text-center">
                Ir a Comprobantes para revisar
              </a>
            )}
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
