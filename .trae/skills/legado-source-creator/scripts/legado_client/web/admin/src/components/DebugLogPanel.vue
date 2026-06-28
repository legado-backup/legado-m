<template>
  <div class="debug-log-panel">
    <div class="log-toolbar">
      <el-button size="small" @click="clearLogs" :disabled="logs.length === 0">清空</el-button>
      <el-button size="small" @click="toggleAutoScroll">
        {{ autoScroll ? '停止自动滚动' : '开启自动滚动' }}
      </el-button>
      <span class="log-count">共 {{ logs.length }} 条</span>
    </div>
    <div ref="logContainerRef" class="log-container">
      <div
        v-for="(log, index) in logs"
        :key="index"
        :class="['log-line', `log-${log.level}`]"
      >
        <span class="log-time">{{ formatTime(log.timestamp) }}</span>
        <el-tag
          v-if="log.phase"
          size="small"
          type="info"
          class="log-phase"
        >
          {{ log.phase }}
        </el-tag>
        <span class="log-level">{{ log.level.toUpperCase() }}</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
      <div v-if="logs.length === 0" class="log-empty">暂无日志</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { DebugLogEntry } from '@/stores/debug'

const props = defineProps<{
  logs: DebugLogEntry[]
}>()

const emit = defineEmits<{
  'clear': []
}>()

const logContainerRef = ref<HTMLDivElement>()
const autoScroll = ref(true)

function clearLogs() {
  emit('clear')
}

function toggleAutoScroll() {
  autoScroll.value = !autoScroll.value
}

function formatTime(ts: string): string {
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString('zh-CN', { hour12: false })
  } catch {
    return ts
  }
}

// 自动滚动到底部
watch(() => props.logs.length, async () => {
  if (!autoScroll.value) return
  await nextTick()
  if (logContainerRef.value) {
    logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
  }
})
</script>

<style scoped>
.debug-log-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.log-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.log-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-left: auto;
}

.log-container {
  flex: 1;
  overflow-y: auto;
  background: var(--el-bg-color-page);
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  padding: 4px 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
}

.log-line {
  padding: 2px 8px;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-line:hover {
  background: var(--el-fill-color-light);
}

.log-info .log-level { color: var(--el-color-primary); }
.log-warn .log-level { color: var(--el-color-warning); }
.log-error .log-level { color: var(--el-color-danger); }
.log-error { background: var(--el-color-danger-light-9); }
.log-debug .log-level { color: var(--el-text-color-secondary); }

.log-time {
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}

.log-phase {
  flex-shrink: 0;
}

.log-level {
  flex-shrink: 0;
  font-weight: 600;
  width: 42px;
}

.log-message {
  flex: 1;
}

.log-empty {
  text-align: center;
  color: var(--el-text-color-placeholder);
  padding: 16px;
}
</style>
