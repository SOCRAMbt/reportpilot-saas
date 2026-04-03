import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

interface DashboardStats {
  comprobantes_hoy: number
  pendientes_revision: number
  veps_pendientes: number
  alertas_activas: number
  clientes_en_riesgo: number
  facturacion_mes_actual: number
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: async () => {
      const { data } = await api.get('/dashboard/stats')
      return data as DashboardStats
    },
  })
}
