import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface DebugLogEntry {
  timestamp: string
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
  phase?: string
}

export const useDebugStore = defineStore('debug', () => {
  // 当前任务 ID
  const taskId = ref<string | null>(null)
  // 日志
  const logs = ref<DebugLogEntry[]>([])
  // 进度 0-100
  const progress = ref(0)
  // 运行状态
  const running = ref(false)

  // 启动调试任务
  function startTask(id: string) {
    taskId.value = id
    logs.value = []
    progress.value = 0
    running.value = true
    // 简化说明：后端无 WebSocket 端点，暂不连接 | 已知上限：无法实时接收日志 | 升级路径：后端增加 /ws/debug/{task_id} 后恢复 WebSocket 连接
  }

  // 停止调试任务
  function stopTask() {
    running.value = false
  }

  // 清空日志
  function clearLogs() {
    logs.value = []
  }

  return { taskId, logs, progress, running, startTask, stopTask, clearLogs }
})
