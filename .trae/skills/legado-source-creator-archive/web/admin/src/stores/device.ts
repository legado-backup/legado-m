import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface DeviceInfo {
  id: string
  name: string
  address: string
  online: boolean
  lastSeen?: string
  [key: string]: any
}

export const useDeviceStore = defineStore('device', () => {
  const devices = ref<DeviceInfo[]>([])
  const loading = ref(false)
  const currentDeviceId = ref<string | null>(null)

  async function refresh() {
    loading.value = true
    try {
      const { fetchDevices } = await import('@/api/device')
      devices.value = await fetchDevices()
    } catch {
      devices.value = []
    } finally {
      loading.value = false
    }
  }

  function setCurrentDevice(id: string) {
    currentDeviceId.value = id
  }

  return { devices, loading, currentDeviceId, refresh, setCurrentDevice }
})
