import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function useDevices() {
  return useQuery({ queryKey: ['devices'], queryFn: api.devices.list, refetchInterval: 3000 })
}
