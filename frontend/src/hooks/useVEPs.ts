import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

export function useVEPs(params?: { periodo?: string; estado?: string }) {
  return useQuery({
    queryKey: ['veps', params],
    queryFn: async () => {
      const p = new URLSearchParams()
      if (params?.periodo) p.set('periodo', params.periodo)
      if (params?.estado) p.set('estado', params.estado)
      const { data } = await api.get(`/veps?${p}`)
      return data
    },
  })
}

export function useAprobarVEP() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (vepId: number) => {
      const { data } = await api.post(`/veps/${vepId}/aprobar`)
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['veps'] }),
  })
}

export function useRegistrarPago() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (vepId: number) => {
      const { data } = await api.put(`/veps/${vepId}/registrar-pago`)
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['veps'] }),
  })
}
