import axios from 'axios'
import { ElMessage } from 'element-plus'

// Axios 实例
const request = axios.create({
  baseURL: '/api',
  timeout: 600000, // 10分钟，支持大规模清理/校验操作
})

// 请求拦截器
request.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const msg = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default request
