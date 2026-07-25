<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="collapsed ? '64px' : '200px'" class="sidebar">
      <div class="sidebar-header">
        <span v-show="!collapsed" class="logo-text">Legado Admin</span>
        <span v-show="collapsed" class="logo-icon">L</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        router
        class="sidebar-menu"
        background-color="var(--el-bg-color)"
        text-color="var(--el-text-color-primary)"
        active-text-color="var(--el-color-primary)"
      >
        <el-menu-item index="/admin/sources">
          <el-icon><Reading /></el-icon>
          <template #title>源列表</template>
        </el-menu-item>
        <el-menu-item index="/admin/collections">
          <el-icon><FolderOpened /></el-icon>
          <template #title>合集管理</template>
        </el-menu-item>
        <el-menu-item index="/admin/import">
          <el-icon><Upload /></el-icon>
          <template #title>源导入</template>
        </el-menu-item>
        <el-menu-item index="/admin/debug">
          <el-icon><Monitor /></el-icon>
          <template #title>测试面板</template>
        </el-menu-item>
        <el-menu-item index="/admin/batch-validate">
          <el-icon><CircleCheck /></el-icon>
          <template #title>批量校验</template>
        </el-menu-item>
        <el-menu-item index="/admin/devices">
          <el-icon><Iphone /></el-icon>
          <template #title>真机管理</template>
        </el-menu-item>
        <el-menu-item index="/admin/stats">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>统计面板</template>
        </el-menu-item>
        <el-menu-item index="/legado/">
          <el-icon><Link /></el-icon>
          <template #title>Legado原生前端</template>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-toggle" @click="collapsed = !collapsed">
        <el-icon :size="16">
          <Fold v-if="!collapsed" />
          <Expand v-else />
        </el-icon>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <!-- 顶栏 -->
      <el-header class="top-bar">
        <div class="top-bar-left">
          <span class="app-title">Legado 源管理面板</span>
        </div>
        <div class="top-bar-right">
          <!-- 数据库状态 -->
          <el-tooltip :content="`数据库: ${appStore.dbStatus}`">
            <el-tag
              :type="appStore.dbStatus === 'online' ? 'success' : appStore.dbStatus === 'offline' ? 'danger' : 'info'"
              size="small"
              effect="dark"
              class="status-tag"
            >
              DB: {{ appStore.dbStatus }}
            </el-tag>
          </el-tooltip>
          <!-- Legado 连接状态 -->
          <el-tooltip :content="`Legado: ${appStore.legadoConnected ? '已连接' : '未连接'}`">
            <el-tag
              :type="appStore.legadoConnected ? 'success' : 'warning'"
              size="small"
              effect="dark"
              class="status-tag"
            >
              Legado: {{ appStore.legadoConnected ? '已连接' : '未连接' }}
            </el-tag>
          </el-tooltip>
          <!-- 暗色切换 -->
          <el-switch
            v-model="appStore.darkMode"
            @change="appStore.toggleDarkMode()"
            active-text="暗"
            inactive-text="亮"
            size="small"
            class="dark-switch"
          />
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="content-area">
        <router-view />
      </el-main>

      <!-- 底栏 -->
      <el-footer class="bottom-bar" height="32px">
        <div class="bottom-bar-inner">
          <span>源总数: <strong>{{ sourceTotal }}</strong></span>
          <span>通过率: <strong>{{ passRate }}%</strong></span>
          <span>JVM: <strong>{{ appStore.jvmStatus }}</strong></span>
        </div>
      </el-footer>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import {
  Reading, FolderOpened, Upload, Monitor, Iphone,
  DataAnalysis, Link, Fold, Expand, CircleCheck,
} from '@element-plus/icons-vue'

const route = useRoute()
const appStore = useAppStore()

const collapsed = ref(false)
const sourceTotal = ref(0)
const passRate = ref(0)

const activeMenu = computed(() => {
  const path = route.path
  // 匹配 /legado/* 路径
  if (path.startsWith('/legado')) return '/legado/'
  return path
})

onMounted(async () => {
  await appStore.checkHealth()
  // 加载底栏统计
  try {
    const { fetchStats } = await import('@/api/stats')
    const stats = await fetchStats()
    sourceTotal.value = stats.total ?? 0
    passRate.value = stats.pass_rate ?? 0
  } catch {
    // 统计加载失败时保持默认值
  }
})
</script>

<style scoped>
.main-layout {
  height: 100vh;
}

.sidebar {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--el-border-color);
  transition: width 0.3s;
  overflow: hidden;
}

.sidebar-header {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--el-border-color);
  font-weight: 700;
  color: var(--el-color-primary);
}

.logo-text {
  font-size: 16px;
}

.logo-icon {
  font-size: 20px;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  overflow-y: auto;
}

.sidebar-toggle {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-top: 1px solid var(--el-border-color);
  color: var(--el-text-color-secondary);
}

.sidebar-toggle:hover {
  color: var(--el-color-primary);
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--el-border-color);
  padding: 0 16px;
}

.top-bar-left {
  display: flex;
  align-items: center;
}

.app-title {
  font-size: 16px;
  font-weight: 600;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-tag {
  font-size: 12px;
}

.dark-switch {
  margin-left: 8px;
}

.content-area {
  overflow-y: auto;
  padding: 16px;
}

.bottom-bar {
  display: flex;
  align-items: center;
  border-top: 1px solid var(--el-border-color);
  padding: 0 16px;
}

.bottom-bar-inner {
  display: flex;
  gap: 24px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
