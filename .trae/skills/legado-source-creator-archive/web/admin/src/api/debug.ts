import request from './request'

// 比较真机与 JAR 测试结果
export async function compareDebug(data: { source_id: number; source_type?: string; search_key?: string; device_id?: number }) {
  return request.post('/debug/compare', data)
}

// JAR 优化测试
export async function jarOptimize(data: { source_id: number; source_type?: string }) {
  return request.post('/debug/jar-optimize', data)
}

// 批量校验源
export async function batchValidate(data: {
  source_type?: string
  mode?: string
  source_ids?: number[] | null
  device_id?: number
  check_search?: boolean
  check_detail?: boolean
  check_toc?: boolean
  check_content?: boolean
  timeout?: number
  max_concurrent?: number
}) {
  return request.post('/debug/batch-validate', data)
}

// 查询批量校验进度
export async function batchValidateStatus(taskId: string) {
  return request.get(`/debug/batch-validate/${encodeURIComponent(taskId)}`)
}
