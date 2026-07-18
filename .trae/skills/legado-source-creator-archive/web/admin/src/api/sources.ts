import request from './request'

// 健康检查
export async function fetchHealth(): Promise<{ db: boolean; jvm: boolean; legado?: boolean }> {
  return request.get('/health')
}

// 获取源列表
export async function fetchSources(params?: {
  keyword?: string
  group?: string
  type?: number
  enabled?: boolean
  page?: number
  page_size?: number
}) {
  return request.get('/sources', { params })
}

// 获取源详情
export async function fetchSource(id: string) {
  return request.get(`/sources/${encodeURIComponent(id)}`)
}

// 创建源
export async function createSource(data: any) {
  return request.post('/sources', data)
}

// 更新源
export async function updateSource(id: string, data: any) {
  return request.put(`/sources/${encodeURIComponent(id)}`, data)
}

// 删除源
export async function deleteSource(id: string) {
  return request.delete(`/sources/${encodeURIComponent(id)}`)
}

// 切换源启用/禁用
export async function toggleSource(id: string) {
  return request.patch(`/sources/${encodeURIComponent(id)}/toggle`)
}

// 批量操作（删除、启用、禁用等）
export async function batchAction(data: { action: string; source_ids?: string[]; urls?: string[] }) {
  return request.post('/sources/batch-action', data)
}

// 批量导出源
export async function batchExport(data: { urls?: string[]; source_ids?: string[]; format?: string }) {
  return request.post('/sources/batch-export', data, { responseType: 'blob' })
}

// 按域名查询源
export async function fetchSourcesByDomain(domain: string) {
  return request.get('/sources/by-domain', { params: { domain } })
}

// 验证源
export async function validateSources(data: { urls?: string[]; source_ids?: string[] }) {
  return request.post('/sources/validate', data)
}

// 导出单个源
export async function exportSource(id: string, format: string = 'json') {
  return request.post(`/sources/${encodeURIComponent(id)}/export`, { format }, { responseType: 'blob' })
}

// 获取源分组列表
export async function fetchGroups() {
  return request.get('/sources/groups')
}
