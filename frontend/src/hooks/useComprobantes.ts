import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

interface Comprobante {
  id: number
  tipo_comprobante: string
  punto_venta: number
  numero: number
  fecha_emision: string
  total: number
  estado_interno: string
  estado_arca: string
}

interface ComprobanteListResponse {
  comprobantes: Comprobante[]
  total: number
  pagina: number
  total_paginas: number
}

export function useComprobantes(filtros?: {
  cliente_id?: number
  estado?: string
  fecha_desde?: string
  fecha_hasta?: string
  pagina?: number
  limite?: number
}) {
  const params = new URLSearchParams()

  if (filtros?.cliente_id) params.set('cliente_id', String(filtros.cliente_id))
  if (filtros?.estado) params.set('estado', filtros.estado)
  if (filtros?.fecha_desde) params.set('fecha_desde', filtros.fecha_desde)
  if (filtros?.fecha_hasta) params.set('fecha_hasta', filtros.fecha_hasta)
  if (filtros?.pagina) params.set('pagina', String(filtros.pagina))
  if (filtros?.limite) params.set('limite', String(filtros.limite))

  return useQuery({
    queryKey: ['comprobantes', params.toString()],
    queryFn: async () => {
      const { data } = await api.get(`/comprobantes?${params}`)
      return data as ComprobanteListResponse
    },
  })
}

export function useCrearComprobante() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: Partial<Comprobante>) => {
      const { data: response } = await api.post('/comprobantes', data)
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comprobantes'] })
    },
  })
}

export function useEliminarComprobante() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/comprobantes/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comprobantes'] })
    },
  })
}
