import { AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react'

interface Alerta {
  id: number
  tipo: string
  severidad: string
  titulo: string
  mensaje: string
  leida: boolean
  creado_en: string
}

export function AlertaCard({ alerta }: { alerta: Alerta }) {
  const iconos = {
    critica: <AlertTriangle className="h-5 w-5 text-red-500" />,
    alta: <AlertCircle className="h-5 w-5 text-orange-500" />,
    media: <Info className="h-5 w-5 text-yellow-500" />,
    baja: <CheckCircle className="h-5 w-5 text-green-500" />,
  }

  const icono = iconos[alerta.severidad as keyof typeof iconos] || iconos.media

  return (
    <div
      className={`flex items-start space-x-3 p-3 rounded-lg border ${
        alerta.leida ? 'bg-gray-50 border-gray-200' : 'bg-white border-yellow-200'
      }`}
    >
      <div className="flex-shrink-0">{icono}</div>

      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${alerta.leida ? 'text-gray-500' : 'text-gray-900'}`}>
          {alerta.titulo}
        </p>
        <p className="text-sm text-gray-500 truncate">{alerta.mensaje}</p>
        <p className="text-xs text-gray-400 mt-1">
          {new Date(alerta.creado_en).toLocaleDateString('es-AR')}
        </p>
      </div>
    </div>
  )
}
