import request from './request'

// 获取概览统计
export async function fetchStats() {
  return request.get('/stats/overview')
}

// 获取测试结果统计
export async function fetchTestResultStats() {
  return request.get('/stats/test-result')
}

// 获取测试模式统计
export async function fetchTestModeStats() {
  return request.get('/stats/test-mode')
}

// 获取内容类型分布
export async function fetchContentTypeDistribution() {
  return request.get('/stats/content-type')
}

// 获取分组分布
export async function fetchGroupDistribution() {
  return request.get('/stats/group')
}
