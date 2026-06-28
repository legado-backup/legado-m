import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchHealth } from '@/api/sources'

export const useAppStore = defineStore('app', () => {
  // 数据库状态
  const dbStatus = ref<'online' | 'offline' | 'unknown'>('unknown')
  // JVM 状态
  const jvmStatus = ref<'running' | 'stopped' | 'unknown'>('unknown')
  // 暗色模式
  const darkMode = ref(false)
  // Legado 连接状态
  const legadoConnected = ref(false)

  // 初始化暗色模式
  function initDarkMode() {
    const saved = localStorage.getItem('legado-dark-mode')
    if (saved !== null) {
      darkMode.value = saved === 'true'
    } else {
      darkMode.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    applyDarkMode()
  }

  // 切换暗色模式
  function toggleDarkMode() {
    darkMode.value = !darkMode.value
    localStorage.setItem('legado-dark-mode', String(darkMode.value))
    applyDarkMode()
  }

  function applyDarkMode() {
    document.documentElement.classList.toggle('dark', darkMode.value)
  }

  // 检查系统健康状态
  async function checkHealth() {
    try {
      const res = await fetchHealth()
      dbStatus.value = res.db ? 'online' : 'offline'
      jvmStatus.value = res.jvm ? 'running' : 'stopped'
      legadoConnected.value = res.legado ?? false
    } catch {
      dbStatus.value = 'offline'
      jvmStatus.value = 'stopped'
      legadoConnected.value = false
    }
  }

  return { dbStatus, jvmStatus, darkMode, legadoConnected, initDarkMode, toggleDarkMode, checkHealth }
})
