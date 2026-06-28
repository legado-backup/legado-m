import request from './request'

export interface DeviceItem {
  id: string
  name: string
  address: string
  online: boolean
  last_seen?: string
}

// 获取设备列表
export async function fetchDevices(): Promise<DeviceItem[]> {
  return request.get('/devices')
}

// 添加设备
export async function addDevice(data: { name: string; address: string }) {
  return request.post('/devices', data)
}

// 更新设备
export async function updateDevice(id: string, data: { name?: string; address?: string }) {
  return request.put(`/devices/${encodeURIComponent(id)}`, data)
}

// 删除设备
export async function deleteDevice(id: string) {
  return request.delete(`/devices/${encodeURIComponent(id)}`)
}

// 测试设备连接
export async function testDeviceConnection(id: string) {
  return request.post(`/devices/${encodeURIComponent(id)}/test-connection`)
}

// 推送源到设备
export async function pushSourcesToDevice(deviceId: string, urls: string[]) {
  return request.post(`/devices/${encodeURIComponent(deviceId)}/push`, { urls })
}

// 从设备拉取源
export async function pullSourcesFromDevice(deviceId: string) {
  return request.post(`/devices/${encodeURIComponent(deviceId)}/pull`)
}

// 清理真机上的死源
export async function cleanDeadSources(deviceId: number, data: {
  source_type?: string
  dry_run?: boolean
  mark_db?: boolean
}) {
  return request.post(`/devices/${encodeURIComponent(deviceId)}/clean-dead`, data)
}

// 真机批量校验源
export async function deviceBatchValidate(deviceId: number, data: {
  source_type?: string
  source_ids?: number[] | null
  checks?: string[]
  timeout?: number
}) {
  return request.post(`/devices/${encodeURIComponent(deviceId)}/batch-validate`, data)
}
