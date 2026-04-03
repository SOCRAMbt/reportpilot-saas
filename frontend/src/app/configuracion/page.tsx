'use client'

import { useState } from 'react'
import Link from 'next/link'
import { DashboardLayout } from '@/components/DashboardLayout'
import { Settings, Building2, Key, Shield, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import api from '@/lib/api'
import { useQuery } from '@tanstack/react-query'

export default function ConfiguracionPage() {
  const [verificando, setVerificando] = useState(false)
  const [conexionEstado, setConexionEstado] = useState<'ok' | 'error' | null>(null)

  const { data: healthData } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await api.get('/health')
      return data
    },
  })

  const handleVerificarConexion = async () => {
    setVerificando(true)
    setConexionEstado(null)
    
    try {
      const { data } = await api.get('/health')
      if (data.database === 'ok') {
        setConexionEstado('ok')
      } else {
        setConexionEstado('error')
      }
    } catch {
      setConexionEstado('error')
    } finally {
      setVerificando(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Configuración</h1>
            <p className="page-subtitle">Ajustes del sistema</p>
          </div>
        </div>

        {/* Mi Estudio */}
        <div className="card">
          <div className="flex items-center gap-3 mb-6">
            <div className="h-10 w-10 rounded-xl bg-blue-100 flex items-center justify-center">
              <Building2 className="h-5 w-5 text-blue-600" />
            </div>
            <h2 className="text-lg font-semibold">Mi Estudio</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="input-label">Razón Social</label>
              <input type="text" className="input-field" value="Mi Estudio Contable" readOnly />
            </div>
            <div>
              <label className="input-label">CUIT</label>
              <input type="text" className="input-field" value="20-12345678-9" readOnly />
            </div>
            <div>
              <label className="input-label">Email</label>
              <input type="email" className="input-field" value="admin@miestudio.com" readOnly />
            </div>
            <div>
              <label className="input-label">Teléfono</label>
              <input type="tel" className="input-field" value="+54 11 1234-5678" readOnly />
            </div>
          </div>

          <button className="btn-secondary mt-4">
            <Settings className="h-4 w-4 mr-2" />
            Editar datos
          </button>
        </div>

        {/* Conexión ARCA */}
        <div className="card">
          <div className="flex items-center gap-3 mb-6">
            <div className="h-10 w-10 rounded-xl bg-emerald-100 flex items-center justify-center">
              <Key className="h-5 w-5 text-emerald-600" />
            </div>
            <h2 className="text-lg font-semibold">Conexión ARCA/AFIP</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="input-label">CUIT del Estudio</label>
              <input type="text" className="input-field" value="20123456789" readOnly />
            </div>
            <div>
              <label className="input-label">Ambiente</label>
              <select className="input-field" defaultValue="hom">
                <option value="hom">Homologación</option>
                <option value="pro">Producción</option>
              </select>
            </div>
            <div>
              <label className="input-label">Ruta del Certificado</label>
              <input type="text" className="input-field" value="/app/certs/certificado.cer" readOnly />
            </div>
            <div>
              <label className="input-label">Ruta de la Clave</label>
              <input type="text" className="input-field" value="/app/certs/clave.key" readOnly />
            </div>
          </div>

          <div className="flex items-center gap-4 mt-6">
            <button
              onClick={handleVerificarConexion}
              disabled={verificando}
              className="btn-primary"
            >
              {verificando ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Verificando...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Verificar conexión
                </>
              )}
            </button>

            {conexionEstado === 'ok' && (
              <div className="flex items-center gap-2 text-emerald-600">
                <CheckCircle className="h-5 w-5" />
                <span className="font-medium">Conexión exitosa (Homologación)</span>
              </div>
            )}
            {conexionEstado === 'error' && (
              <div className="flex items-center gap-2 text-red-600">
                <XCircle className="h-5 w-5" />
                <span className="font-medium">Error de conexión</span>
              </div>
            )}
          </div>

          <div className="mt-6 p-4 bg-slate-50 rounded-xl">
            <h3 className="font-medium text-slate-900 mb-2">Estado de servicios</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-600">Base de datos:</span>
                <span className={healthData?.database === 'ok' ? 'text-emerald-600 font-medium' : 'text-red-600'}>
                  {healthData?.database === 'ok' ? '✓ Conectado' : healthData?.database || 'Verificando...'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600">Redis:</span>
                <span className={healthData?.redis === 'ok' ? 'text-emerald-600 font-medium' : 'text-amber-600'}>
                  {healthData?.redis === 'ok' ? '✓ Conectado' : healthData?.redis || 'No disponible'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Seguridad */}
        <div className="card">
          <div className="flex items-center gap-3 mb-6">
            <div className="h-10 w-10 rounded-xl bg-purple-100 flex items-center justify-center">
              <Shield className="h-5 w-5 text-purple-600" />
            </div>
            <h2 className="text-lg font-semibold">Seguridad</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="input-label">Contraseña actual</label>
              <input type="password" className="input-field" placeholder="••••••••" />
            </div>
            <div>
              <label className="input-label">Nueva contraseña</label>
              <input type="password" className="input-field" placeholder="••••••••" />
            </div>
            <div>
              <label className="input-label">Confirmar nueva contraseña</label>
              <input type="password" className="input-field" placeholder="••••••••" />
            </div>

            <button className="btn-secondary mt-2">
              <Shield className="h-4 w-4 mr-2" />
              Cambiar contraseña
            </button>
          </div>
        </div>

        {/* Información del sistema */}
        <div className="card bg-slate-50">
          <div className="text-center">
            <h3 className="font-semibold text-slate-900">AccountantOS v9.7</h3>
            <p className="text-sm text-slate-500 mt-1">
              Sistema de Automatización Contable para Argentina
            </p>
            <p className="text-xs text-slate-400 mt-4">
              © 2026 - Todos los derechos reservados
            </p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
