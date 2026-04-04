import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

export function useClientes(busqueda?: string) {
  return useQuery({
    queryKey: ['clientes', busqueda],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (busqueda) params.set('busqueda', busqueda)
      const { data } = await api.get(`/clientes?${params}`)
      return data
    },
  })
}

export function useSemaforoDelegaciones() {
  return useQuery({
    queryKey: ['delegaciones', 'estado'],
    queryFn: async () => {
      const { data } = await api.get('/clientes/delegaciones/estado')
      return data
    },
  })
}

export function useVerificarDelegacion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (clienteId: number) => {
      const { data } = await api.post(`/clientes/${clienteId}/verificar-delegacion`)
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clientes'] })
      qc.invalidateQueries({ queryKey: ['delegaciones', 'estado'] })
    },
  })
}

export function useSemaforoClientes() {
  return useQuery({
    queryKey: ['dashboard', 'semaforo'],
    queryFn: async () => {
      const { data } = await api.get('/dashboard/semaforo-clientes')
      return data
    },
  })
}
