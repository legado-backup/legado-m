import request from './request'

// 获取合集列表
export async function fetchCollections(params?: { keyword?: string; page?: number; page_size?: number }) {
  return request.get('/collections', { params })
}

// 获取远程合集列表
export async function fetchRemoteCollections(params?: { type?: string }) {
  return request.get('/collections/remote', { params })
}

// 全量获取所有远程合集
export async function fetchAllCollections(data?: { type?: string }) {
  return request.post('/collections/fetch-all', data)
}

// 增量更新合集
export async function incrementalUpdateCollections(data?: { type?: string }) {
  return request.post('/collections/incremental', data)
}

// 下载指定合集
export async function downloadCollection(id: string) {
  return request.post(`/collections/${encodeURIComponent(id)}/download`)
}

// 删除合集
export async function deleteCollection(id: string) {
  return request.delete(`/collections/${encodeURIComponent(id)}`)
}
