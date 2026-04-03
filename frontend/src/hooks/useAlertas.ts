import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

interface Alerta {
  id: number
  tipo: string
  severidad: string
  titulo: string
  mensaje: string
  leida: boolean
  creado_en: string
}

export function useAlertas() {
  return useQuery({
    queryKey: ['alertas'],
    queryFn: async () => {
      const { data } = await api.get('/alertas')
      return data as Alerta[]
    },
  })
}
