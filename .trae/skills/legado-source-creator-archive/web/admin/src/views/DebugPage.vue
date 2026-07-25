<template>
  <div class="page-container">
    <h2>测试面板</h2>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- Tab1: 单源测试 -->
      <el-tab-pane label="单源测试" name="single">
        <el-form :model="singleForm" label-width="100px" class="debug-form">
          <el-form-item label="选择源">
            <SourceSelect v-model="singleForm.sourceId" placeholder="搜索并选择源" />
          </el-form-item>
          <el-form-item label="测试阶段">
            <el-checkbox-group v-model="singleForm.stages">
              <el-checkbox label="search">搜索</el-checkbox>
              <el-checkbox label="detail">详情</el-checkbox>
              <el-checkbox label="toc">目录</el-checkbox>
              <el-checkbox label="content">正文</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="测试模式">
            <el-radio-group v-model="singleForm.mode">
              <el-radio-button label="auto">自动</el-radio-button>
              <el-radio-button label="device">真机</el-radio-button>
              <el-radio-button label="jar">JVM仿真</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="singleForm.mode === 'device'" label="选择设备">
            <DeviceSelect v-model="singleForm.deviceId" />
          </el-form-item>
          <el-form-item v-if="singleForm.stages.includes('search')" label="搜索关键词">
            <el-input v-model="singleForm.keyword" placeholder="输入搜索关键词" clearable />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="debugStore.running"
              @click="handleStartSingle"
            >
              {{ debugStore.running ? '测试中...' : '开始测试' }}
            </el-button>
            <el-button
              v-if="debugStore.running"
              type="danger"
              @click="handleCancelDebug"
            >
              取消测试
            </el-button>
          </el-form-item>
        </el-form>

        <div v-if="debugStore.taskId" class="log-section">
          <h4>实时日志</h4>
          <DebugLogPanel :logs="debugStore.logs" @clear="debugStore.clearLogs()" />
        </div>
      </el-tab-pane>

      <!-- Tab2: 批量测试 -->
      <el-tab-pane label="批量测试" name="batch">
        <el-form :model="batchForm" label-width="100px" class="debug-form">
          <el-form-item label="测试范围">
            <el-radio-group v-model="batchForm.scope">
              <el-radio-button label="all">全部源</el-radio-button>
              <el-radio-button label="failed">失败源</el-radio-button>
              <el-radio-button label="group">指定分组</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="batchForm.scope === 'group'" label="选择分组">
            <el-select v-model="batchForm.group" placeholder="选择分组" filterable>
              <el-option
                v-for="g in groups"
                :key="g"
                :label="g"
                :value="g"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="测试模式">
            <el-radio-group v-model="batchForm.mode">
              <el-radio-button label="auto">自动</el-radio-button>
              <el-radio-button label="device">真机</el-radio-button>
              <el-radio-button label="jar">JVM仿真</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="batchRunning"
              @click="handleStartBatch"
            >
              {{ batchRunning ? '测试中...' : '开始测试' }}
            </el-button>
            <el-button
              v-if="batchRunning"
              type="danger"
              @click="handleCancelBatch"
            >
              取消测试
            </el-button>
          </el-form-item>
        </el-form>

        <!-- 批量测试结果表格 -->
        <el-table
          v-if="batchResults.length > 0"
          :data="batchResults"
          stripe
          style="margin-top: 16px"
        >
          <el-table-column prop="sourceName" label="源名称" min-width="160" />
          <el-table-column prop="sourceUrl" label="源地址" min-width="200" show-overflow-tooltip />
          <el-table-column prop="stage" label="阶段" width="80" />
          <el-table-column prop="result" label="结果" width="80">
            <template #default="{ row }">
              <el-tag :type="row.result === 'pass' ? 'success' : row.result === 'fail' ? 'danger' : 'warning'" size="small">
                {{ row.result === 'pass' ? '通过' : row.result === 'fail' ? '失败' : '超时' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="信息" min-width="200" show-overflow-tooltip />
        </el-table>
      </el-tab-pane>

      <!-- Tab3: 优化测试 -->
      <el-tab-pane label="优化测试" name="optimize">
        <el-form :model="optimizeForm" label-width="100px" class="debug-form">
          <el-form-item label="选择失败源">
            <SourceSelect v-model="optimizeForm.sourceId" placeholder="搜索失败源" />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="optimizeRunning"
              @click="handleStartOptimize"
            >
              {{ optimizeRunning ? '优化中...' : '开始优化' }}
            </el-button>
          </el-form-item>
        </el-form>

        <!-- 修复 diff 展示 -->
        <div v-if="optimizeDiff" class="diff-section">
          <h4>修复 Diff</h4>
          <el-card>
            <pre class="diff-content">{{ optimizeDiff }}</pre>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 测试历史 -->
    <div class="history-section">
      <h3>测试历史</h3>
      <el-table :data="historyList" stripe size="small" max-height="360">
        <el-table-column prop="task_id" label="任务ID" width="140" show-overflow-tooltip />
        <el-table-column prop="source_name" label="源名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="mode" label="模式" width="80" />
        <el-table-column prop="stages" label="阶段" width="160" show-overflow-tooltip />
        <el-table-column prop="result" label="结果" width="80">
          <template #default="{ row }">
            <el-tag
              :type="row.result === 'pass' ? 'success' : row.result === 'fail' ? 'danger' : 'info'"
              size="small"
            >
              {{ row.result === 'pass' ? '通过' : row.result === 'fail' ? '失败' : row.result || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170" />
      </el-table>
    </div>

    <!-- 批量测试进度弹窗 -->
    <ProgressDialog
      v-model="progressVisible"
      title="批量测试"
      :percentage="batchProgress"
      :message="batchMessage"
      :cancellable="batchRunning"
      @cancel="handleCancelBatch"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import SourceSelect from '@/components/SourceSelect.vue'
import DeviceSelect from '@/components/DeviceSelect.vue'
import DebugLogPanel from '@/components/DebugLogPanel.vue'
import ProgressDialog from '@/components/ProgressDialog.vue'
import { useDebugStore } from '@/stores/debug'
import { compareDebug, jarOptimize } from '@/api/debug'
import { validateSources } from '@/api/sources'

const debugStore = useDebugStore()
const activeTab = ref('single')

// 单源测试表单
const singleForm = ref({
  sourceId: 0,
  stages: ['search', 'detail', 'toc', 'content'] as string[],
  mode: 'auto',
  deviceId: '',
  keyword: '',
})

// 批量测试表单
const batchForm = ref({
  scope: 'all',
  group: '',
  mode: 'auto',
})
const groups = ref<string[]>([])
const batchRunning = ref(false)
const batchResults = ref<any[]>([])
const batchTaskId = ref('')
const batchProgress = ref(0)
const batchMessage = ref('')
const progressVisible = ref(false)
let batchPollTimer: ReturnType<typeof setInterval> | null = null

// 优化测试表单
const optimizeForm = ref({
  sourceId: 0,
})
const optimizeRunning = ref(false)
const optimizeDiff = ref('')

// 测试历史
const historyList = ref<any[]>([])

async function handleStartSingle() {
  if (!singleForm.value.sourceId) {
    ElMessage.warning('请选择一个源')
    return
  }
  try {
    if (singleForm.value.mode === 'jar') {
      const res = await jarOptimize({
        source_id: singleForm.value.sourceId,
        source_type: 'book',
      })
      const taskId = (res as any).task_id || (res as any).taskId
      if (taskId) {
        debugStore.startTask(taskId)
        ElMessage.success('JVM仿真测试已启动')
      }
    } else {
      const res = await validateSources({ source_ids: [singleForm.value.sourceId] })
      const taskId = (res as any).task_id || (res as any).taskId
      if (taskId) {
        debugStore.startTask(taskId)
        ElMessage.success('测试已启动')
      }
    }
  } catch (e: any) {
    ElMessage.error('启动测试失败: ' + (e.message || e))
  }
}

async function handleCancelDebug() {
  if (debugStore.taskId) {
    debugStore.stopTask()
    ElMessage.info('测试已取消')
  }
}

async function handleStartBatch() {
  batchRunning.value = true
  batchResults.value = []
  batchProgress.value = 0
  batchMessage.value = '正在启动批量测试...'
  progressVisible.value = true
  try {
    const res = await validateSources({ urls: [] })
    batchTaskId.value = (res as any).task_id || (res as any).taskId || ''
    if (batchTaskId.value) {
      startBatchPoll()
    }
  } catch (e: any) {
    ElMessage.error('启动批量测试失败: ' + (e.message || e))
    batchRunning.value = false
    progressVisible.value = false
  }
}

function startBatchPoll() {
  if (batchPollTimer) clearInterval(batchPollTimer)
  batchPollTimer = setInterval(async () => {
    if (!batchTaskId.value) return
    try {
      // 简化说明：后端 validate 为同步执行，无独立进度接口 | 已知上限：无法实时获取进度 | 升级路径：后端增加任务状态接口后替换轮询逻辑
      const res = await validateSources({ urls: [] })
      const data = res as any
      batchProgress.value = data.percentage ?? data.progress ?? 100
      batchMessage.value = data.message || `已完成 ${batchProgress.value}%`
      if (data.results) {
        batchResults.value = data.results
      }
      if (batchProgress.value >= 100 || data.done) {
        stopBatchPoll()
        batchRunning.value = false
        batchMessage.value = '批量测试完成'
        if (data.results) {
          batchResults.value = data.results
        }
      }
    } catch {
      stopBatchPoll()
      batchRunning.value = false
    }
  }, 2000)
}

function stopBatchPoll() {
  if (batchPollTimer) {
    clearInterval(batchPollTimer)
    batchPollTimer = null
  }
}

function handleCancelBatch() {
  stopBatchPoll()
  batchRunning.value = false
  progressVisible.value = false
  ElMessage.info('批量测试已取消')
}

async function handleStartOptimize() {
  if (!optimizeForm.value.sourceId) {
    ElMessage.warning('请先选择失败源')
    return
  }
  optimizeRunning.value = true
  optimizeDiff.value = ''
  try {
    const res = await jarOptimize({
      source_id: optimizeForm.value.sourceId,
      source_type: 'book',
    })
    const data = res as any
    if (data.diff) {
      optimizeDiff.value = data.diff
    }
    ElMessage.success('优化测试已启动')
  } catch (e: any) {
    ElMessage.error('启动优化测试失败: ' + (e.message || e))
  } finally {
    optimizeRunning.value = false
  }
}

onMounted(() => {
  // 加载测试历史
  try {
    const raw = localStorage.getItem('debug_history')
    if (raw) {
      historyList.value = JSON.parse(raw).slice(0, 20)
    }
  } catch { /* ignore */ }
})

onUnmounted(() => {
  stopBatchPoll()
  debugStore.stopTask()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.debug-form {
  max-width: 700px;
}

.log-section {
  margin-top: 20px;
}

.log-section h4 {
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
}

.history-section {
  margin-top: 24px;
}

.history-section h3 {
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
}

.diff-section {
  margin-top: 20px;
}

.diff-section h4 {
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
}

.diff-content {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  max-height: 400px;
  overflow-y: auto;
}
</style>
