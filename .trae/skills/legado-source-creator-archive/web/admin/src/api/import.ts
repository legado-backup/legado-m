import request from './request'

// 从 URL 导入源
export async function importFromUrl(url: string) {
  return request.post('/import/url', { url })
}

// 从文件导入
export async function importFromFile(file: File) {
  const form = new FormData()
  form.append('file', file)
  return request.post('/import/file', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// 从 GitHub 导入
export async function importFromGithub(url: string) {
  return request.post('/import/github', { url })
}

// 从 Legado 真机拉取
export async function importFromLegadoPull(data: { device_id: string; source_type?: string }) {
  return request.post('/import/legado-pull', data)
}
