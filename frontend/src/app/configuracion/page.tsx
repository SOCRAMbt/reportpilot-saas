'use client'

import { useState } from 'react'
import { DashboardLayout } from '@/components/DashboardLayout'
import { Key, CheckCircle, XCircle, Loader2, ArrowRight, ArrowLeft, Upload, Shield } from 'lucide-react'
import api from '@/lib/api'
import { useQuery } from '@tanstack/react-query'

export default function ConfiguracionPage() {
  const [paso, setPaso] = useState(1)

  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Configuración</h1>
            <p className="page-subtitle">Configurá tu conexión con ARCA en 3 pasos</p>
          </div>
        </div>

        {/* Steps indicator */}
        <div className="flex items-center gap-2">
          {[1, 2, 3].map((n) => (
            <div key={n} className="flex items-center gap-2 flex-1">
              <div className={`h-8 w-8 rounded-full flex items-center justify-center text-sm font-bold ${
                paso >= n ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'
              }`}>
                {paso > n ? '✓' : n}
              </div>
              <span className={`text-sm ${paso >= n ? 'text-slate-900 font-medium' : 'text-slate-400'}`}>
                {n === 1 ? 'Certificado' : n === 2 ? 'Datos' : 'Primeros pasos'}
              </span>
              {n < 3 && <div className={`flex-1 h-0.5 ${paso > n ? 'bg-blue-600' : 'bg-slate-200'}`} />}
            </div>
          ))}
        </div>

        {paso === 1 && <PasoCertificado onNext={() => setPaso(2)} />}
        {paso === 2 && <PasoDatos onNext={() => setPaso(3)} onBack={() => setPaso(1)} />}
        {paso === 3 && <PasoChecklist onBack={() => setPaso(2)} />}
      </div>
    </DashboardLayout>
  )
}

/* ─── PASO 1: Certificado ARCA ─── */

function PasoCertificado({ onNext }: { onNext: () => void }) {
  const [certFile, setCertFile] = useState<File | null>(null)
  const [keyFile, setKeyFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [certStatus, setCertStatus] = useState<'ok' | 'error' | null>(null)
  const [certInfo, setCertInfo] = useState<any>(null)

  const { data: arcaEstado } = useQuery({
    queryKey: ['arca', 'estado'],
    queryFn: async () => {
      const { data } = await api.get('/configuracion/arca/estado')
      return data
    },
  })

  const subirArchivo = async (file: File, endpoint: string) => {
    const formData = new FormData()
    formData.append('archivo', file)
    const { data } = await api.post(endpoint, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  }

  const handleSubir = async () => {
    if (!certFile && !keyFile) return
    setUploading(true)
    setCertStatus(null)
    try {
      if (certFile) {
        const res = await subirArchivo(certFile, '/configuracion/arca/certificado')
        setCertInfo(res)
      }
      if (keyFile) {
        await subirArchivo(keyFile, '/configuracion/arca/clave-privada')
      }
      setCertStatus('ok')
    } catch (e: any) {
      setCertStatus('error')
      console.error(e)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="card space-y-6">
      <div className="flex items-center gap-3">
        <Key className="h-6 w-6 text-blue-600" />
        <div>
          <h2 className="text-lg font-semibold">Tu certificado ARCA</h2>
          <p className="text-sm text-slate-500">Este certificado le dice a ARCA que sos vos</p>
        </div>
      </div>

      {/* Estado actual */}
      {arcaEstado && (
        <div className={`p-4 rounded-xl ${arcaEstado.listo_para_produccion ? 'bg-emerald-50' : 'bg-amber-50'}`}>
          <p className="text-sm font-medium">
            {arcaEstado.listo_para_produccion ? '✅ Certificado configurado' : '⚠️ Certificado pendiente de carga'}
          </p>
          {arcaEstado.certificado?.valido && (
            <p className="text-xs text-slate-500 mt-1">
              Vence: {arcaEstado.certificado.valid_until}
              {arcaEstado.certificado.alerta && ` — ${arcaEstado.certificado.alerta}`}
            </p>
          )}
        </div>
      )}

      {/* Upload certificado */}
      <div>
        <label className="input-label">Certificado (.cer, .pem, .crt)</label>
        <input
          type="file"
          accept=".cer,.pem,.crt"
          onChange={(e) => setCertFile(e.target.files?.[0] || null)}
          className="input-field"
        />
      </div>

      {/* Upload clave */}
      <div>
        <label className="input-label">Clave privada (.key, .pem)</label>
        <input
          type="file"
          accept=".key,.pem"
          onChange={(e) => setKeyFile(e.target.files?.[0] || null)}
          className="input-field"
        />
      </div>

      {certStatus === 'ok' && (
        <div className="flex items-center gap-2 text-emerald-600">
          <CheckCircle className="h-5 w-5" />
          <span className="font-medium">
            {certInfo?.dias_para_vencimiento
              ? `Cargado. Vence en ${certInfo.dias_para_vencimiento} días.`
              : 'Archivos cargados correctamente.'}
          </span>
        </div>
      )}
      {certStatus === 'error' && (
        <div className="flex items-center gap-2 text-red-600">
          <XCircle className="h-5 w-5" />
          <span className="font-medium">Error al subir. Verificá que los archivos sean válidos.</span>
        </div>
      )}

      <button
        onClick={handleSubir}
        disabled={uploading || (!certFile && !keyFile)}
        className="btn-primary w-full"
      >
        {uploading ? (
          <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Subiendo...</>
        ) : (
          <><Upload className="h-4 w-4 mr-2" /> Subir archivos</>
        )}
      </button>

      <button onClick={onNext} className="btn-secondary w-full">
        Siguiente <ArrowRight className="h-4 w-4 ml-1" />
      </button>
    </div>
  )
}

/* ─── PASO 2: Datos del estudio ─── */

function PasoDatos({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const [cuit, setCuit] = useState('')
  const [nombre, setNombre] = useState('')
  const [ambiente, setAmbiente] = useState('hom')
  const [guardando, setGuardando] = useState(false)
  const [resultado, setResultado] = useState<string | null>(null)

  const handleGuardar = async () => {
    if (!cuit || !nombre) return
    setGuardando(true)
    setResultado(null)
    try {
      const { data } = await api.post('/configuracion/arca/configurar-estudio', {
        cuit_estudio: cuit,
        nombre_estudio: nombre,
        ambiente,
      })
      setResultado(data.mensaje)
    } catch (e: any) {
      setResultado(`Error: ${e.response?.data?.detail || 'No se pudo configurar'}`)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="card space-y-6">
      <div className="flex items-center gap-3">
        <Shield className="h-6 w-6 text-blue-600" />
        <div>
          <h2 className="text-lg font-semibold">Tus datos</h2>
          <p className="text-sm text-slate-500">Configurá tu CUIT y el ambiente de trabajo</p>
        </div>
      </div>

      <div>
        <label className="input-label">CUIT del estudio (11 dígitos)</label>
        <input
          type="text"
          value={cuit}
          onChange={(e) => setCuit(e.target.value.replace(/\D/g, '').slice(0, 11))}
          className="input-field"
          placeholder="20123456789"
        />
      </div>

      <div>
        <label className="input-label">Nombre del estudio</label>
        <input
          type="text"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          className="input-field"
          placeholder="María García - Estudio Contable"
        />
      </div>

      <div>
        <label className="input-label">Ambiente</label>
        <select value={ambiente} onChange={(e) => setAmbiente(e.target.value)} className="input-field">
          <option value="hom">🧪 Prueba (homologación — sin efectos reales)</option>
          <option value="pro">⚠️ Producción (afecta datos reales de ARCA)</option>
        </select>
        <p className="text-xs text-slate-500 mt-1">
          Empezá siempre en Prueba para probar sin riesgo.
        </p>
      </div>

      {resultado && (
        <div className={`p-3 rounded-xl text-sm ${resultado.startsWith('Error') ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`}>
          {resultado}
        </div>
      )}

      <button onClick={handleGuardar} disabled={guardando || !cuit || !nombre} className="btn-primary w-full">
        {guardando ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Guardando...</> : 'Guardar y probar conexión'}
      </button>

      <div className="flex gap-2">
        <button onClick={onBack} className="btn-secondary flex-1">
          <ArrowLeft className="h-4 w-4 mr-1" /> Atrás
        </button>
        <button onClick={onNext} className="btn-primary flex-1">
          Siguiente <ArrowRight className="h-4 w-4 ml-1" />
        </button>
      </div>
    </div>
  )
}

/* ─── PASO 3: Checklist primeros pasos ─── */

function PasoChecklist({ onBack }: { onBack: () => void }) {
  return (
    <div className="card space-y-6">
      <div className="flex items-center gap-3">
        <CheckCircle className="h-6 w-6 text-emerald-600" />
        <div>
          <h2 className="text-lg font-semibold">Primeros pasos</h2>
          <p className="text-sm text-slate-500">Seguí este checklist para empezar</p>
        </div>
      </div>

      <div className="space-y-3">
        <ChecklistItem text="Certificado ARCA cargado" done />
        <ChecklistItem text="Datos del estudio configurados" done />
        <ChecklistItem text="Primer cliente agregado" link="/clientes" />
        <ChecklistItem text="Primera delegación verificada" link="/clientes" />
        <ChecklistItem text="Primera sincronización con ARCA" action="Dashboard → Sincronizar ARCA" />
      </div>

      <button onClick={onBack} className="btn-secondary w-full">
        <ArrowLeft className="h-4 w-4 mr-1" /> Volver
      </button>
    </div>
  )
}

function ChecklistItem({ text, done, link, action }: {
  text: string; done?: boolean; link?: string; action?: string
}) {
  return (
    <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
      {done ? (
        <CheckCircle className="h-5 w-5 text-emerald-600 flex-shrink-0" />
      ) : (
        <div className="h-5 w-5 rounded-full border-2 border-slate-300 flex-shrink-0" />
      )}
      <span className={done ? 'text-slate-500 line-through' : 'text-slate-900'}>{text}</span>
      {link && <a href={link} className="ml-auto text-blue-600 text-sm font-medium">Ir →</a>}
      {action && <span className="ml-auto text-slate-400 text-xs">{action}</span>}
    </div>
  )
}
