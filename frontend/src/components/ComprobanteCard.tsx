import { FileText, CheckCircle, AlertCircle, Clock } from 'lucide-react'

interface Comprobante {
  id: number
  tipo_comprobante: string
  punto_venta: number
  numero: number
  fecha_emision: string
  total: number
  estado_arca: string
  estado_interno: string
  cuit_emisor?: string
}

export function ComprobanteCard({ comprobante }: { comprobante: Comprobante }) {
  const estadoIcon = {
    PRESENTE_VALIDO: <CheckCircle className="h-4 w-4 text-green-500" />,
    PENDIENTE_VERIFICACION: <Clock className="h-4 w-4 text-yellow-500" />,
    REVISION_HUMANA: <AlertCircle className="h-4 w-4 text-red-500" />,
    ANULADO: <AlertCircle className="h-4 w-4 text-gray-400" />,
  }

  const estadoColors = {
    PRESENTE_VALIDO: 'badge-success',
    PENDIENTE_VERIFICACION: 'badge-warning',
    REVISION_HUMANA: 'badge-danger',
    ANULADO: 'bg-gray-100 text-gray-600',
  }

  const formatoNumero = comprobante.numero.toString().padStart(8, '0')

  return (
    <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
      <div className="flex items-center space-x-4">
        <div className="p-2 bg-blue-100 rounded-lg">
          <FileText className="h-5 w-5 text-blue-600" />
        </div>

        <div>
          <p className="font-medium text-gray-900">
            Factura {comprobante.tipo_comprobante} {formatoNumero}
          </p>
          <p className="text-sm text-gray-500">
            {new Date(comprobante.fecha_emision).toLocaleDateString('es-AR')}
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="text-right">
          <p className="font-medium text-gray-900">
            ${Number(comprobante.total).toLocaleString('es-AR', { minimumFractionDigits: 2 })}
          </p>
          <p className="text-xs text-gray-500">
            Pto {comprobante.punto_venta}
          </p>
        </div>

        <div className={`badge ${estadoColors[comprobante.estado_interno as keyof typeof estadoColors] || 'badge-info'}`}>
          {estadoIcon[comprobante.estado_interno as keyof typeof estadoIcon]}
          <span className="ml-1">{comprobante.estado_interno.replace(/_/g, ' ')}</span>
        </div>
      </div>
    </div>
  )
}
